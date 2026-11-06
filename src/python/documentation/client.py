"""Read-only search client for official InterSystems documentation."""

from __future__ import annotations

import argparse
import ipaddress
import json
import re
import socket
import sys
import xml.etree.ElementTree as ET

from dataclasses import asdict, dataclass
from html import unescape
from typing import Final, Iterable
from urllib.parse import urljoin, urlparse, urlunparse

import httpx
from bs4 import BeautifulSoup


ALLOWED_HOSTS: Final[frozenset[str]] = frozenset(
    {
        "docs.intersystems.com",
    }
)

START_URLS: Final[tuple[str, ...]] = (
    "https://docs.intersystems.com/",
)

ALLOWED_METHODS: Final[frozenset[str]] = frozenset({"GET", "HEAD"})

USER_AGENT: Final[str] = "IRIS-Resolve-Documentation-Prototype/0.1"

CONNECT_TIMEOUT_SECONDS: Final[float] = 5.0
READ_TIMEOUT_SECONDS: Final[float] = 15.0
MAX_REDIRECTS: Final[int] = 2

MAX_RESPONSE_BYTES: Final[int] = 2_000_000
MAX_RETURNED_CHARACTERS: Final[int] = 12_000

DEFAULT_MAX_RESULTS: Final[int] = 5
DEFAULT_MAX_PAGES: Final[int] = 40
MAX_ALLOWED_RESULTS: Final[int] = 10
MAX_ALLOWED_PAGES: Final[int] = 100

MIN_QUERY_LENGTH: Final[int] = 3
MAX_QUERY_LENGTH: Final[int] = 200

SENSITIVE_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"\b\d{9,12}[A-Za-z]?\b"),
    re.compile(r"\bI\d{5,10}\b", re.IGNORECASE),
    re.compile(r"\bCCR[-\s]?\d+\b", re.IGNORECASE),
    re.compile(r"\bNHS[-\s]?\d+\b", re.IGNORECASE),
    re.compile(
        r"\b(?:patient|episode|nhs number|date of birth|dob)\s*[:=]",
        re.IGNORECASE,
    ),
)

WORD_PATTERN: Final[re.Pattern[str]] = re.compile(r"[a-z0-9]+")

IGNORED_EXTENSIONS: Final[tuple[str, ...]] = (
    ".7z",
    ".css",
    ".csv",
    ".doc",
    ".docx",
    ".exe",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".js",
    ".json",
    ".mp3",
    ".mp4",
    ".pdf",
    ".png",
    ".ppt",
    ".pptx",
    ".rar",
    ".svg",
    ".tar",
    ".tgz",
    ".txt",
    ".webp",
    ".xls",
    ".xlsx",
    ".zip",
)


class DocumentationError(RuntimeError):
    """Raised when documentation retrieval cannot be completed safely."""


@dataclass(frozen=True)
class SearchResult:
    """A single documentation search result."""

    evidence_id: str
    source: str
    title: str
    url: str
    excerpt: str
    score: int


@dataclass(frozen=True)
class Document:
    """Cleaned content from one documentation page."""

    evidence_id: str
    source: str
    title: str
    url: str
    text: str
    truncated: bool


def normalise_hostname(hostname: str | None) -> str:
    """Return a lower-case hostname without a trailing dot."""

    return (hostname or "").lower().rstrip(".")


def is_public_ip(address: str) -> bool:
    """Return True only when an IP address is publicly routable."""

    ip = ipaddress.ip_address(address)

    return not any(
        (
            ip.is_private,
            ip.is_loopback,
            ip.is_link_local,
            ip.is_multicast,
            ip.is_reserved,
            ip.is_unspecified,
        )
    )


def validate_host_resolution(hostname: str) -> None:
    """Confirm that the approved documentation hostname resolves.

    Corporate networks may resolve public websites through an internal
    security gateway with a private IP address. This is permitted only
    because the hostname has already been checked against ALLOWED_HOSTS.
    """

    if hostname not in ALLOWED_HOSTS:
        raise DocumentationError(
            f"Host is not allow-listed: {hostname}"
        )

    try:
        addresses = socket.getaddrinfo(
            hostname,
            443,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise DocumentationError(
            f"Unable to resolve approved documentation host: {hostname}"
        ) from exc

    if not addresses:
        raise DocumentationError(
            f"No network addresses were returned for: {hostname}"
        )


def validate_url(url: str, *, resolve_host: bool = True) -> str:
    """Validate and normalise an allow-listed documentation URL."""

    if not isinstance(url, str) or not url.strip():
        raise DocumentationError("A non-empty URL is required.")

    parsed = urlparse(url.strip())
    hostname = normalise_hostname(parsed.hostname)

    if parsed.scheme.lower() != "https":
        raise DocumentationError("Only HTTPS URLs are allowed.")

    if hostname not in ALLOWED_HOSTS:
        raise DocumentationError(
            f"Host is not allow-listed: {hostname or '[missing host]'}"
        )

    if parsed.username or parsed.password:
        raise DocumentationError("Credentials in URLs are not allowed.")

    if parsed.port not in (None, 443):
        raise DocumentationError("Only the standard HTTPS port is allowed.")

    path = parsed.path or "/"

    if path.lower().endswith(IGNORED_EXTENSIONS):
        raise DocumentationError(
            "Downloads and unsupported file types are not allowed."
        )

    if resolve_host:
        validate_host_resolution(hostname)

    normalised = parsed._replace(
        scheme="https",
        netloc=hostname,
        fragment="",
    )

    return urlunparse(normalised)


def validate_query(query: str) -> str:
    """Validate that a documentation search query is generic and safe."""

    cleaned = " ".join(query.split())

    if len(cleaned) < MIN_QUERY_LENGTH:
        raise DocumentationError(
            f"Query must contain at least {MIN_QUERY_LENGTH} characters."
        )

    if len(cleaned) > MAX_QUERY_LENGTH:
        raise DocumentationError(
            f"Query must not exceed {MAX_QUERY_LENGTH} characters."
        )

    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(cleaned):
            raise DocumentationError(
                "The query may contain a ticket, CCR, patient, episode, or "
                "other customer-specific identifier. Use generic product "
                "terminology instead."
            )

    return cleaned


def create_client() -> httpx.Client:
    """Create the restricted HTTP client."""

    timeout = httpx.Timeout(
        connect=CONNECT_TIMEOUT_SECONDS,
        read=READ_TIMEOUT_SECONDS,
        write=READ_TIMEOUT_SECONDS,
        pool=CONNECT_TIMEOUT_SECONDS,
    )

    return httpx.Client(
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=timeout,
        follow_redirects=False,
        trust_env=False,
    )


def perform_get(
    client: httpx.Client,
    url: str,
) -> tuple[str, bytes, str]:
    """Perform a bounded GET request with validated redirects."""

    current_url = validate_url(url)

    for redirect_number in range(MAX_REDIRECTS + 1):
        request = client.build_request("GET", current_url)

        if request.method not in ALLOWED_METHODS:
            raise DocumentationError(
                f"Blocked HTTP method: {request.method}"
            )

        try:
            response = client.send(request, stream=True)
        except httpx.HTTPError as exc:
            raise DocumentationError(
                f"Documentation request failed: {exc}"
            ) from exc

        try:
            if response.is_redirect:
                if redirect_number >= MAX_REDIRECTS:
                    raise DocumentationError(
                        "Maximum redirect count exceeded."
                    )

                location = response.headers.get("location")

                if not location:
                    raise DocumentationError(
                        "Redirect did not provide a destination."
                    )

                redirected_url = urljoin(current_url, location)
                current_url = validate_url(redirected_url)
                continue

            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise DocumentationError(
                    f"Documentation request returned HTTP "
                    f"{response.status_code}: {current_url}"
                ) from exc

            content_type = (
                response.headers.get("content-type", "")
                .split(";", maxsplit=1)[0]
                .strip()
                .lower()
            )

            if content_type not in {
                "text/html",
                "application/xhtml+xml",
                "application/xml",
                "text/xml",
            }:
                raise DocumentationError(
                    f"Unsupported content type: "
                    f"{content_type or '[missing]'}"
                )

            content = bytearray()

            for chunk in response.iter_bytes():
                content.extend(chunk)

                if len(content) > MAX_RESPONSE_BYTES:
                    raise DocumentationError(
                        "Documentation response exceeded the size limit."
                    )

            final_url = validate_url(str(response.url))
            return final_url, bytes(content), content_type
        finally:
            response.close()

    raise DocumentationError("Unable to complete documentation request.")


def clean_text(value: str) -> str:
    """Normalise extracted page text."""

    value = unescape(value)
    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n[ \t]+", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)

    return value.strip()


def extract_html_page(
    content: bytes,
    base_url: str,
) -> tuple[str, str, list[str]]:
    """Extract the page title, readable text, and safe documentation links."""

    soup = BeautifulSoup(content, "html.parser")

    for element in soup(
        [
            "script",
            "style",
            "form",
            "input",
            "button",
            "iframe",
            "object",
            "embed",
            "svg",
            "canvas",
            "noscript",
        ]
    ):
        element.decompose()

    title = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""

    content_root = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.body
        or soup
    )

    text = clean_text(content_root.get_text("\n", strip=True))
    links: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        raw_link = anchor.get("href", "").strip()

        if not raw_link:
            continue

        candidate = urljoin(base_url, raw_link)

        try:
            safe_url = validate_url(candidate, resolve_host=False)
        except DocumentationError:
            continue

        links.add(safe_url)

    return title or base_url, text, sorted(links)


def extract_sitemap_urls(content: bytes) -> list:
    """Extract allow-listed URLs from an XML sitemap."""

    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []

    urls: set[str] = set()

    for element in root.iter():
        if not element.tag.lower().endswith("loc"):
            continue

        if not element.text:
            continue

        try:
            safe_url = validate_url(
                element.text.strip(),
                resolve_host=False,
            )
        except DocumentationError:
            continue

        urls.add(safe_url)

    return sorted(urls)


def tokenise(value: str) -> set:
    """Return normalised search tokens."""

    return set(WORD_PATTERN.findall(value.lower()))


def score_page(query_tokens: set[str], title: str, text: str) -> int:
    """Score a page against a set of query tokens."""

    if not query_tokens:
        return 0

    title_tokens = tokenise(title)
    body_tokens = tokenise(text[:50_000])

    title_matches = len(query_tokens.intersection(title_tokens))
    body_matches = len(query_tokens.intersection(body_tokens))

    phrase = " ".join(sorted(query_tokens))
    normalised_title = " ".join(title.lower().split())
    normalised_body = " ".join(text[:20_000].lower().split())

    phrase_bonus = 0

    if phrase and phrase in normalised_title:
        phrase_bonus += 20

    if phrase and phrase in normalised_body:
        phrase_bonus += 10

    return (title_matches * 10) + (body_matches * 2) + phrase_bonus


def make_excerpt(
    text: str,
    query_tokens: set[str],
    length: int = 500,
) -> str:
    """Return a short excerpt close to the first matching term."""

    if not text:
        return ""

    lower_text = text.lower()
    positions = [
        lower_text.find(token)
        for token in query_tokens
        if lower_text.find(token) >= 0
    ]

    position = min(positions) if positions else 0
    start = max(0, position - (length // 3))
    end = min(len(text), start + length)

    excerpt = text[start:end].strip()

    if start > 0:
        excerpt = f"...{excerpt}"

    if end < len(text):
        excerpt = f"{excerpt}..."

    return clean_text(excerpt)


def candidate_urls_from_sitemaps(
    client: httpx.Client,
) -> list:
    """Try to discover documentation URLs through conventional sitemaps."""

    sitemap_candidates = (
        "https://docs.intersystems.com/sitemap.xml",
        "https://docs.intersystems.com/sitemap_index.xml",
    )

    discovered: set[str] = set()

    for sitemap_url in sitemap_candidates:
        try:
            _, content, content_type = perform_get(client, sitemap_url)
        except DocumentationError:
            continue

        if content_type not in {"application/xml", "text/xml"}:
            continue

        for url in extract_sitemap_urls(content):
            if url.lower().endswith(".xml"):
                try:
                    _, nested_content, nested_type = perform_get(client, url)
                except DocumentationError:
                    continue

                if nested_type in {"application/xml", "text/xml"}:
                    discovered.update(extract_sitemap_urls(nested_content))
            else:
                discovered.add(url)

    return sorted(discovered)


def prioritise_urls(
    urls: Iterable[str],
    query_tokens: set[str],
) -> list:
    """Prioritise URLs containing search terms without excluding others."""

    unique_urls = set(urls)

    return sorted(
        unique_urls,
        key=lambda url: (
            -len(query_tokens.intersection(tokenise(url))),
            len(url),
            url,
        ),
    )


def search_intersystems_docs(
    query: str,
    *,
    max_results: int = DEFAULT_MAX_RESULTS,
    max_pages: int = DEFAULT_MAX_PAGES,
) -> dict:
    """Search a bounded number of official InterSystems documentation pages."""

    safe_query = validate_query(query)

    if not 1 <= max_results <= MAX_ALLOWED_RESULTS:
        raise DocumentationError(
            f"max_results must be between 1 and {MAX_ALLOWED_RESULTS}."
        )

    if not 1 <= max_pages <= MAX_ALLOWED_PAGES:
        raise DocumentationError(
            f"max_pages must be between 1 and {MAX_ALLOWED_PAGES}."
        )

    query_tokens = tokenise(safe_query)
    visited: set[str] = set()
    queued: set[str] = set(START_URLS)
    results: list[SearchResult] = []

    with create_client() as client:
        sitemap_urls = candidate_urls_from_sitemaps(client)
        queue = prioritise_urls(
            (*START_URLS, *sitemap_urls),
            query_tokens,
        )

        while queue and len(visited) < max_pages:
            url = queue.pop(0)

            if url in visited:
                continue

            visited.add(url)

            try:
                final_url, content, content_type = perform_get(client, url)
            except DocumentationError:
                continue

            if content_type not in {
                "text/html",
                "application/xhtml+xml",
            }:
                continue

            title, text, page_links = extract_html_page(
                content,
                final_url,
            )

            page_score = score_page(query_tokens, title, text)

            if page_score > 0:
                results.append(
                    SearchResult(
                        evidence_id="",
                        source="INTERSYSTEMS_DOCUMENTATION",
                        title=title,
                        url=final_url,
                        excerpt=make_excerpt(text, query_tokens),
                        score=page_score,
                    )
                )

            if not sitemap_urls:
                for link in prioritise_urls(page_links, query_tokens):
                    if link not in visited and link not in queued:
                        queue.append(link)
                        queued.add(link)

        results.sort(
            key=lambda result: (
                -result.score,
                result.title.lower(),
                result.url,
            )
        )

        deduplicated: list[SearchResult] = []
        seen_urls: set[str] = set()

        for result in results:
            if result.url in seen_urls:
                continue

            seen_urls.add(result.url)
            deduplicated.append(result)

            if len(deduplicated) >= max_results:
                break

    numbered_results = [
        SearchResult(
            evidence_id=f"ISC-DOC-{index:03d}",
            source=result.source,
            title=result.title,
            url=result.url,
            excerpt=result.excerpt,
            score=result.score,
        )
        for index, result in enumerate(deduplicated, start=1)
    ]

    return {
        "query": safe_query,
        "source": "INTERSYSTEMS_DOCUMENTATION",
        "read_only": True,
        "allowed_hosts": sorted(ALLOWED_HOSTS),
        "http_methods": ["GET"],
        "pages_checked": len(visited),
        "results": [asdict(result) for result in numbered_results],
    }


def get_intersystems_doc(url: str) -> dict:
    """Retrieve and clean one allow-listed documentation page."""

    safe_url = validate_url(url)

    with create_client() as client:
        final_url, content, content_type = perform_get(client, safe_url)

    if content_type not in {
        "text/html",
        "application/xhtml+xml",
    }:
        raise DocumentationError(
            "The requested resource is not an HTML documentation page."
        )

    title, text, _ = extract_html_page(content, final_url)
    truncated = len(text) > MAX_RETURNED_CHARACTERS

    document = Document(
        evidence_id="ISC-DOC-001",
        source="INTERSYSTEMS_DOCUMENTATION",
        title=title,
        url=final_url,
        text=text[:MAX_RETURNED_CHARACTERS],
        truncated=truncated,
    )

    return {
        **asdict(document),
        "read_only": True,
        "http_method": "GET",
    }


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Search and retrieve official InterSystems documentation "
            "using read-only HTTP GET requests."
        )
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    search_parser = subparsers.add_parser(
        "search",
        help="Search official InterSystems documentation.",
    )
    search_parser.add_argument("query")
    search_parser.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_MAX_RESULTS,
    )
    search_parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
    )

    get_parser = subparsers.add_parser(
        "get",
        help="Retrieve one official documentation page.",
    )
    get_parser.add_argument("url")

    return parser


def main() -> int:
    """Run the standalone documentation client."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "search":
            output = search_intersystems_docs(
                args.query,
                max_results=args.max_results,
                max_pages=args.max_pages,
            )
        else:
            output = get_intersystems_doc(args.url)
    except DocumentationError as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                    "read_only": True,
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())