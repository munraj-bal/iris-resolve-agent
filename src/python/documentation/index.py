"""Build and search a local index of InterSystems documentation."""

from __future__ import annotations

import os
import argparse
import hashlib
import json
import re
import sqlite3
import sys
import time

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Final, Iterable
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup, Tag

from documentation.client import (
    DocumentationError,
    create_client,
    perform_get,
    validate_query,
    validate_url,
)


PROJECT_ROOT: Final[Path] = (
    Path(__file__).resolve().parents[3]
)

DEFAULT_DATABASE_PATH: Final[Path] = (
    PROJECT_ROOT / "data" / "documentation" / "docs.db"
)

DATABASE_PATH: Final[Path] = Path(
    os.environ.get(
        "DOCS_DATABASE_PATH",
        str(DEFAULT_DATABASE_PATH),
    )
)

START_URLS: Final[tuple[str, ...]] = (
    "https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls",
    "https://docs.intersystems.com/irisforhealthlatest/csp/docbook/DocBook.UI.Page.cls",
    "https://docs.intersystems.com/healthconnectlatest/csp/docbook/DocBook.UI.Page.cls",
)

DEFAULT_MAX_PAGES: Final[int] = 100
MAX_ALLOWED_PAGES: Final[int] = 500

DEFAULT_MAX_DEPTH: Final[int] = 3
MAX_ALLOWED_DEPTH: Final[int] = 6

DEFAULT_REQUEST_DELAY_SECONDS: Final[float] = 0.25

MIN_SECTION_CHARACTERS: Final[int] = 80
MAX_SECTION_CHARACTERS: Final[int] = 8_000

DEFAULT_SEARCH_RESULTS: Final[int] = 10
MAX_SEARCH_RESULTS: Final[int] = 50

SKIPPED_PATH_PARTS: Final[tuple[str, ...]] = (
    "/changes/",
    "/relnotes/",
    "doc.feedback.cls",
    "doc.search",
    "docbook.ui.search",
)

SKIPPED_QUERY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "page",
        "search",
        "query",
        "sort",
        "highlight",
        "session",
        "token",
    }
)

ALLOWED_DOCUMENTATION_PREFIXES: Final[tuple[str, ...]] = (
    "/irislatest/",
    "/irisforhealthlatest/",
    "/healthconnectlatest/",
)

@dataclass(frozen=True)
class Section:
    """One searchable documentation section."""

    section_id: str
    url: str
    product: str
    version: str
    document_type: str
    document_title: str
    heading: str
    content: str


@dataclass(frozen=True)
class SearchHit:
    """One result returned from the local documentation index."""

    section_id: str
    url: str
    product: str
    version: str
    document_type: str
    document_title: str
    heading: str
    excerpt: str
    score: float


def connect_database(
    database_path: Path = DATABASE_PATH,
) -> sqlite3.Connection:
    """Open the local SQLite documentation database."""

    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row

    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


def initialise_database(connection: sqlite3.Connection) -> None:
    """Create the local documentation tables."""

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS sections (
            section_id TEXT PRIMARY KEY,
            url TEXT NOT NULL,
            product TEXT NOT NULL,
            version TEXT NOT NULL,
            document_type TEXT NOT NULL,
            document_title TEXT NOT NULL,
            heading TEXT NOT NULL,
            content TEXT NOT NULL,
            indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS sections_fts USING fts5(
            section_id UNINDEXED,
            product,
            version,
            document_type,
            document_title,
            heading,
            content,
            tokenize = 'porter unicode61'
        );

        CREATE INDEX IF NOT EXISTS idx_sections_url
        ON sections(url);

        CREATE INDEX IF NOT EXISTS idx_sections_product
        ON sections(product);

        CREATE INDEX IF NOT EXISTS idx_sections_version
        ON sections(version);

        CREATE INDEX IF NOT EXISTS idx_sections_document_type
        ON sections(document_type);
        """
    )

    connection.commit()


def clear_database(connection: sqlite3.Connection) -> None:
    """Remove the existing locally indexed documentation."""

    connection.execute("DELETE FROM sections")
    connection.execute("DELETE FROM sections_fts")
    connection.commit()


def canonicalise_url(url: str) -> str:
    """Remove fragments and unnecessary query parameters."""

    safe_url = validate_url(url, resolve_host=False)
    parsed = urlparse(safe_url)

    if parsed.query:
        query_parts = []

        for item in parsed.query.split("&"):
            key = item.split("=", maxsplit=1)[0].lower()

            if key not in SKIPPED_QUERY_KEYS:
                query_parts.append(item)

        query = "&".join(query_parts)
    else:
        query = ""

    normalised = parsed._replace(
        query=query,
        fragment="",
    )

    return urlunparse(normalised)


def should_index_url(url: str) -> bool:
    """Return whether an approved URL is useful for indexing."""

    try:
        safe_url = canonicalise_url(url)
    except DocumentationError:
        return False

    parsed = urlparse(safe_url)
    path = parsed.path.lower()

    if not path.startswith(ALLOWED_DOCUMENTATION_PREFIXES):
        return False

    if path.endswith(
        (
            ".css",
            ".csv",
            ".gif",
            ".ico",
            ".jpeg",
            ".jpg",
            ".js",
            ".json",
            ".pdf",
            ".png",
            ".svg",
            ".txt",
            ".webp",
            ".xml",
            ".zip",
        )
    ):
        return False

    if any(part in path for part in SKIPPED_PATH_PARTS):
        return False

    return True


def infer_product_and_version(url: str) -> tuple[str, str]:
    """Infer the InterSystems product and version from the URL."""

    path = urlparse(url).path.lower()

    patterns = (
        (
            r"/irisforhealth(\d{4,5})/",
            "InterSystems IRIS for Health",
        ),
        (
            r"/healthconnect(\d{4,5})/",
            "InterSystems Health Connect",
        ),
        (
            r"/iris(\d{4,5})/",
            "InterSystems IRIS",
        ),
        (
            r"/cache(\d{4,5})/",
            "InterSystems Caché",
        ),
        (
            r"/ensemble(\d{4,5})/",
            "InterSystems Ensemble",
        ),
    )

    for pattern, product in patterns:
        match = re.search(pattern, path)

        if match:
            raw_version = match.group(1)

            if len(raw_version) >= 5:
                version = (
                    f"{raw_version[:4]}."
                    f"{raw_version[4:]}"
                )
            else:
                version = raw_version

            return product, version

    if "irisforhealth" in path:
        return "InterSystems IRIS for Health", ""

    if "healthconnect" in path:
        return "InterSystems Health Connect", ""

    if "cacheensemble" in path:
        return "InterSystems Caché and Ensemble", ""

    if "iris" in path:
        return "InterSystems IRIS", ""

    return "InterSystems Documentation", ""


def infer_document_type(
    url: str,
    title: str,
    heading: str,
) -> str:
    """Classify a documentation page or section."""

    combined = " ".join(
        (
            url.lower(),
            title.lower(),
            heading.lower(),
        )
    )

    if any(
        term in combined
        for term in (
            "release note",
            "change note",
            "upgrade checklist",
            "/changes/",
            "/relnotes/",
        )
    ):
        return "RELEASE_NOTES"

    if any(
        term in combined
        for term in (
            "reference",
            "class reference",
            "api reference",
            "sql reference",
        )
    ):
        return "REFERENCE"

    if any(
        term in combined
        for term in (
            "administration",
            "management portal",
            "monitoring",
            "security",
        )
    ):
        return "ADMINISTRATION"

    if any(
        term in combined
        for term in (
            "interoperability",
            "production",
            "visual trace",
            "message viewer",
            "business service",
            "business process",
            "business operation",
        )
    ):
        return "INTEROPERABILITY"

    if any(
        term in combined
        for term in (
            "tutorial",
            "using ",
            "configuring ",
            "creating ",
            "managing ",
            "viewing ",
        )
    ):
        return "USER_GUIDE"

    return "GENERAL"


def clean_section_text(value: str) -> str:
    """Normalise text extracted from a documentation section."""

    value = value.replace("\u00a0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n[ \t]+", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)

    return value.strip()


def split_text(
    value: str,
    maximum_length: int = MAX_SECTION_CHARACTERS,
) -> list:
    """Split an oversized section into bounded text chunks."""

    value = clean_section_text(value)

    if len(value) <= maximum_length:
        return [value]

    paragraphs = value.split("\n")
    chunks: list[str] = []
    current: list[str] = []
    current_length = 0

    for paragraph in paragraphs:
        paragraph = paragraph.strip()

        if not paragraph:
            continue

        paragraph_length = len(paragraph) + 1

        if current and current_length + paragraph_length > maximum_length:
            chunks.append("\n".join(current))
            current = []
            current_length = 0

        if len(paragraph) > maximum_length:
            for start in range(0, len(paragraph), maximum_length):
                chunks.append(
                    paragraph[start : start + maximum_length]
                )
            continue

        current.append(paragraph)
        current_length += paragraph_length

    if current:
        chunks.append("\n".join(current))

    return chunks


def make_section_id(
    url: str,
    heading: str,
    chunk_number: int,
) -> str:
    """Create a stable identifier for one indexed section."""

    value = f"{url}\n{heading}\n{chunk_number}"
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()

    return f"ISC-SECTION-{digest[:16].upper()}"


def extract_sections(
    content: bytes,
    url: str,
) -> tuple[str, list[Section], list[str]]:
    """Extract structured sections and approved links from one page."""

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
            "nav",
            "footer",
        ]
    ):
        element.decompose()

    title = (
        clean_section_text(
            soup.title.get_text(" ", strip=True)
        )
        if soup.title
        else url
    )

    root = (
        soup.find("main")
        or soup.find("article")
        or soup.find(attrs={"role": "main"})
        or soup.body
        or soup
    )

    product, version = infer_product_and_version(url)
    extracted_sections: list[Section] = []

    headings = root.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6"]
    )

    if headings:
        for heading_element in headings:
            heading = clean_section_text(
                heading_element.get_text(" ", strip=True)
            )

            if not heading:
                continue

            parts: list[str] = []

            for sibling in heading_element.next_siblings:
                if (
                    isinstance(sibling, Tag)
                    and sibling.name
                    in {"h1", "h2", "h3", "h4", "h5", "h6"}
                ):
                    break

                if isinstance(sibling, Tag):
                    sibling_text = sibling.get_text(
                        "\n",
                        strip=True,
                    )
                else:
                    sibling_text = str(sibling).strip()

                if sibling_text:
                    parts.append(sibling_text)

            section_text = clean_section_text(
                "\n".join(parts)
            )

            if len(section_text) < MIN_SECTION_CHARACTERS:
                continue

            for chunk_number, chunk in enumerate(
                split_text(section_text),
                start=1,
            ):
                displayed_heading = heading

                if chunk_number > 1:
                    displayed_heading = (
                        f"{heading} (part {chunk_number})"
                    )

                document_type = infer_document_type(
                    url,
                    title,
                    displayed_heading,
                )

                extracted_sections.append(
                    Section(
                        section_id=make_section_id(
                            url,
                            displayed_heading,
                            chunk_number,
                        ),
                        url=url,
                        product=product,
                        version=version,
                        document_type=document_type,
                        document_title=title,
                        heading=displayed_heading,
                        content=chunk,
                    )
                )

    if not extracted_sections:
        page_text = clean_section_text(
            root.get_text("\n", strip=True)
        )

        for chunk_number, chunk in enumerate(
            split_text(page_text),
            start=1,
        ):
            if len(chunk) < MIN_SECTION_CHARACTERS:
                continue

            heading = title

            if chunk_number > 1:
                heading = f"{title} (part {chunk_number})"

            extracted_sections.append(
                Section(
                    section_id=make_section_id(
                        url,
                        heading,
                        chunk_number,
                    ),
                    url=url,
                    product=product,
                    version=version,
                    document_type=infer_document_type(
                        url,
                        title,
                        heading,
                    ),
                    document_title=title,
                    heading=heading,
                    content=chunk,
                )
            )

    links: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "").strip()

        if not href:
            continue

        from urllib.parse import urljoin

        candidate = urljoin(url, href)

        if not should_index_url(candidate):
            continue

        try:
            links.add(canonicalise_url(candidate))
        except DocumentationError:
            continue

    return title, extracted_sections, sorted(links)


def store_sections(
    connection: sqlite3.Connection,
    url: str,
    sections: Iterable[Section],
) -> int:
    """Replace locally indexed sections for a page."""

    existing_rows = connection.execute(
        "SELECT section_id FROM sections WHERE url = ?",
        (url,),
    ).fetchall()

    for row in existing_rows:
        connection.execute(
            "DELETE FROM sections_fts WHERE section_id = ?",
            (row["section_id"],),
        )

    connection.execute(
        "DELETE FROM sections WHERE url = ?",
        (url,),
    )

    count = 0

    for section in sections:
        connection.execute(
            """
            INSERT OR REPLACE INTO sections (
                section_id,
                url,
                product,
                version,
                document_type,
                document_title,
                heading,
                content
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                section.section_id,
                section.url,
                section.product,
                section.version,
                section.document_type,
                section.document_title,
                section.heading,
                section.content,
            ),
        )

        connection.execute(
            """
            INSERT INTO sections_fts (
                section_id,
                product,
                version,
                document_type,
                document_title,
                heading,
                content
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                section.section_id,
                section.product,
                section.version,
                section.document_type,
                section.document_title,
                section.heading,
                section.content,
            ),
        )

        count += 1

    connection.commit()
    return count


def prioritise_links(
    links: Iterable[str],
) -> list:
    """Prefer detailed technical documentation pages."""

    preferred_terms = (
        "interop",
        "production",
        "message",
        "trace",
        "viewer",
        "enslib",
        "monitor",
        "manage",
        "admin",
        "hl7",
        "objectscript",
        "sql",
        "security",
    )

    def link_score(url: str) -> tuple[int, int, int, str]:
        lower_url = url.lower()
        parsed = urlparse(url)

        has_key = "key=" in parsed.query.lower()
        preferred_matches = sum(
            term in lower_url
            for term in preferred_terms
        )

        return (
            -int(has_key),
            -preferred_matches,
            len(url),
            url,
        )

    return sorted(set(links), key=link_score)


def build_index(
    *,
    max_pages: int,
    max_depth: int,
    reset: bool,
    delay_seconds: float,
) -> dict:
    """Build a bounded local documentation index."""

    if not 1 <= max_pages <= MAX_ALLOWED_PAGES:
        raise DocumentationError(
            f"max_pages must be between 1 and "
            f"{MAX_ALLOWED_PAGES}."
        )

    if not 0 <= max_depth <= MAX_ALLOWED_DEPTH:
        raise DocumentationError(
            f"max_depth must be between 0 and "
            f"{MAX_ALLOWED_DEPTH}."
        )

    connection = connect_database()
    initialise_database(connection)

    if reset:
        clear_database(connection)

    queue: list[tuple[str, int]] = [
        (canonicalise_url(url), 0)
        for url in START_URLS
    ]

    queued = {url for url, _ in queue}
    visited: set[str] = set()
    failures: list[dict] = []
    indexed_sections = 0

    with create_client() as client:
        while queue and len(visited) < max_pages:
            url, depth = queue.pop(0)

            if url in visited:
                continue

            visited.add(url)

            try:
                final_url, content, content_type = perform_get(
                    client,
                    url,
                )
            except DocumentationError as exc:
                failures.append(
                    {
                        "url": url,
                        "error": str(exc),
                    }
                )
                continue

            if content_type not in {
                "text/html",
                "application/xhtml+xml",
            }:
                continue

            _, sections, links = extract_sections(
                content,
                final_url,
            )

            indexed_sections += store_sections(
                connection,
                final_url,
                sections,
            )

            print(
                f"[{len(visited)}/{max_pages}] "
                f"{len(sections)} sections: {final_url}",
                file=sys.stderr,
            )

            if depth < max_depth:
                for link in prioritise_links(links):
                    if link in visited or link in queued:
                        continue

                    parsed_link = urlparse(link)
                    lower_path = parsed_link.path.lower()
                    lower_query = parsed_link.query.lower()

                    is_document_page = (
                        "key=" in lower_query
                        or lower_path.endswith("/docbook.ui.page.cls")
                    )

                    if not is_document_page:
                        continue

                    queue.append((link, depth + 1))
                    queued.add(link)

            if delay_seconds > 0:
                time.sleep(delay_seconds)

    page_count = connection.execute(
        "SELECT COUNT(DISTINCT url) AS count FROM sections"
    ).fetchone()["count"]

    total_sections = connection.execute(
        "SELECT COUNT(*) AS count FROM sections"
    ).fetchone()["count"]

    connection.close()

    return {
        "database": str(DATABASE_PATH),
        "read_only_external_access": True,
        "external_http_methods": ["GET"],
        "pages_requested": len(visited),
        "pages_in_index": page_count,
        "sections_in_index": total_sections,
        "sections_added_or_replaced": indexed_sections,
        "failures": failures,
    }


def build_fts_query(query: str) -> str:
    """Create a safe, phrase-aware FTS5 query."""

    safe_query = validate_query(query)

    terms = re.findall(
        r"[A-Za-z0-9_]+",
        safe_query,
    )

    if not terms:
        raise DocumentationError(
            "The search query did not contain searchable terms."
        )

    escaped_terms = [
        term.replace('"', '""')
        for term in terms
    ]

    phrase = " ".join(escaped_terms)

    parts = [
        f'"{phrase}"',
        *(
            f'"{term}"'
            for term in escaped_terms
        ),
    ]

    return " OR ".join(parts)


def make_excerpt(
    content: str,
    query: str,
    length: int = 600,
) -> str:
    """Create a readable excerpt around a matching phrase or term."""

    lower_content = content.lower()
    lower_query = query.lower()

    position = lower_content.find(lower_query)

    if position < 0:
        for term in re.findall(r"[a-z0-9]+", lower_query):
            position = lower_content.find(term)

            if position >= 0:
                break

    if position < 0:
        position = 0

    start = max(0, position - 180)
    end = min(len(content), start + length)

    if start > 0:
        next_space = content.find(" ", start)

        if 0 <= next_space < end:
            start = next_space + 1

    truncated_at_end = end < len(content)

    if truncated_at_end:
        sentence_end = max(
            content.rfind(".", start, end),
            content.rfind("!", start, end),
            content.rfind("?", start, end),
        )

        if sentence_end > start + 200:
            end = sentence_end + 1
        else:
            last_space = content.rfind(" ", start, end)

            if last_space > start:
                end = last_space

    excerpt = content[start:end].strip()

    if start > 0:
        excerpt = f"...{excerpt}"

    if truncated_at_end:
        excerpt = f"{excerpt}..."

    return clean_section_text(excerpt)



QUERY_EXPANSIONS: Final[dict[str, tuple[str, ...]]] = {
    "visual trace": (
        "tracing related messages",
        "production session messages",
        "message path",
    ),
    "message viewer": (
        "viewing messages",
        "filtering messages",
        "message header fields",
        "message body fields",
    ),
    "business operation queue": (
        "monitoring production queues",
        "queued messages",
        "business operation status",
        "production queue status",
        "jobs and message queues",
    ),
    "event log": (
        "viewing event log entries",
        "event log search criteria",
        "production errors",
    ),
    "outbound message": (
        "business operation",
        "message transmission",
        "message status",
        "production message path",
    ),
    "message not generated": (
        "viewing messages",
        "visual trace",
        "event log",
        "message routing",
    ),
}


def expand_support_query(query: str) -> list[str]:
    """Expand support terminology into related documentation phrases."""

    safe_query = validate_query(query)
    lower_query = safe_query.lower()
    expanded = [safe_query]

    for phrase, alternatives in QUERY_EXPANSIONS.items():
        if phrase in lower_query:
            expanded.extend(alternatives)

    seen: set[str] = set()
    unique_queries: list[str] = []

    for item in expanded:
        normalised = " ".join(item.split())
        key = normalised.lower()

        if key in seen:
            continue

        seen.add(key)
        unique_queries.append(normalised)

    return unique_queries


def search_index(
    query: str,
    *,
    product: str = "",
    version: str = "",
    document_type: str = "",
    max_results: int = DEFAULT_SEARCH_RESULTS,
) -> dict:
    """Search the local documentation index."""

    if not DATABASE_PATH.exists():
        raise DocumentationError(
            "The local documentation index does not exist. "
            "Run docs_index.py build first."
        )

    if not 1 <= max_results <= MAX_SEARCH_RESULTS:
        raise DocumentationError(
            f"max_results must be between 1 and "
            f"{MAX_SEARCH_RESULTS}."
        )

    safe_query = validate_query(query)
    fts_query = build_fts_query(safe_query)

    connection = connect_database()
    initialise_database(connection)

    conditions = ["sections_fts MATCH ?"]
    parameters: list[object] = [fts_query]

    if product:
        conditions.append("LOWER(s.product) = LOWER(?)")
        parameters.append(product)

    if version:
        conditions.append("s.version = ?")
        parameters.append(version)

    if document_type:
        conditions.append("s.document_type = ?")
        parameters.append(document_type.upper())

    parameters.append(max_results * 4)

    sql = f"""
        SELECT
            s.section_id,
            s.url,
            s.product,
            s.version,
            s.document_type,
            s.document_title,
            s.heading,
            s.content,
            bm25(
                sections_fts,
                0.0,
                1.5,
                1.0,
                1.0,
                3.0,
                5.0,
                1.0
            ) AS raw_score
        FROM sections_fts
        JOIN sections AS s
          ON s.section_id = sections_fts.section_id
        WHERE {" AND ".join(conditions)}
        ORDER BY raw_score ASC
        LIMIT ?
    """

    rows = connection.execute(
        sql,
        parameters,
    ).fetchall()

    hits: list[SearchHit] = []
    normalised_query = safe_query.lower()

    for row in rows:
        title = row["document_title"]
        heading = row["heading"]
        content = row["content"]

        searchable = " ".join(
            (
                title,
                heading,
                content,
            )
        ).lower()

        phrase_bonus = 0.0

        if normalised_query in heading.lower():
            phrase_bonus += 100.0

        if normalised_query in title.lower():
            phrase_bonus += 60.0

        if normalised_query in content.lower():
            phrase_bonus += 30.0

        type_bonus = {
            "INTEROPERABILITY": 20.0,
            "ADMINISTRATION": 15.0,
            "USER_GUIDE": 10.0,
            "REFERENCE": 5.0,
            "GENERAL": 0.0,
            "RELEASE_NOTES": -20.0,
        }.get(row["document_type"], 0.0)

        title_penalty = 0.0
        lower_title = title.lower()

        if "planning" in lower_title:
            title_penalty -= 20.0

        if "all documentation" in lower_title:
            title_penalty -= 30.0

        if "documentation home page" in lower_title:
            title_penalty -= 30.0

        if "release notes" in lower_title:
            title_penalty -= 20.0

        if "contents" in lower_title:
            title_penalty -= 5.0

        all_terms = all(
            term in searchable
            for term in re.findall(
                r"[a-z0-9]+",
                normalised_query,
            )
        )

        heading_bonus = 0.0
        lower_heading = heading.lower()

        operational_heading_terms = (
            "jobs and message queues",
            "monitoring production queues",
            "message viewer",
            "visual trace",
            "event log",
            "message status",
            "sessions",
        )

        if any(
            term in lower_heading
            for term in operational_heading_terms
        ):
            heading_bonus += 25.0

        completeness_bonus = 15.0 if all_terms else 0.0

        final_score = (
            -float(row["raw_score"])
            + phrase_bonus
            + type_bonus
            + completeness_bonus
            + title_penalty
            + heading_bonus
        )

        hits.append(
            SearchHit(
                section_id=row["section_id"],
                url=row["url"],
                product=row["product"],
                version=row["version"],
                document_type=row["document_type"],
                document_title=title,
                heading=heading,
                excerpt=make_excerpt(
                    content,
                    safe_query,
                ),
                score=round(final_score, 4),
            )
        )

    hits.sort(
        key=lambda hit: (
            -hit.score,
            hit.document_title.lower(),
            hit.heading.lower(),
        )
    )

    connection.close()

    return {
        "query": safe_query,
        "source": "LOCAL_INTERSYSTEMS_DOCUMENTATION_INDEX",
        "external_request_made": False,
        "filters": {
            "product": product,
            "version": version,
            "document_type": document_type.upper(),
        },
        "results": [
            asdict(hit)
            for hit in hits[:max_results]
        ],
    }


def search_expanded_index(
    query: str,
    *,
    product: str = "",
    version: str = "",
    document_type: str = "",
    max_results: int = DEFAULT_SEARCH_RESULTS,
) -> dict:
    """Search using the original query and related support phrases."""

    safe_query = validate_query(query)
    expanded_queries = expand_support_query(safe_query)

    merged: dict[str, dict] = {}

    candidate_limit = min(
        MAX_SEARCH_RESULTS,
        max(max_results * 3, 15),
    )

    original_terms = set(
        re.findall(
            r"[a-z0-9]+",
            safe_query.lower(),
        )
    )

    total_original_terms = max(
        1,
        len(original_terms),
    )

    for expanded_query in expanded_queries:
        search_output = search_index(
            expanded_query,
            product=product,
            version=version,
            document_type=document_type,
            max_results=candidate_limit,
        )

        for result in search_output["results"]:
            section_id = result["section_id"]
            candidate = dict(result)

            is_original_query = (
                expanded_query.lower() == safe_query.lower()
            )

            candidate_text = " ".join(
                (
                    candidate["document_title"],
                    candidate["heading"],
                    candidate["excerpt"],
                )
            ).lower()

            matched_original_terms = sum(
                term in candidate_text
                for term in original_terms
            )

            original_term_coverage = (
                matched_original_terms
                / total_original_terms
            )

            exact_original_phrase = (
                safe_query.lower() in candidate_text
            )

            candidate["matched_original_terms"] = (
                matched_original_terms
            )
            candidate["original_term_coverage"] = round(
                original_term_coverage,
                3,
            )
            candidate["exact_original_phrase"] = (
                exact_original_phrase
            )

            if is_original_query:
                candidate["matched_query"] = safe_query
                candidate["match_source"] = "ORIGINAL_QUERY"

                candidate["score"] += (
                    40.0 * original_term_coverage
                )

                if exact_original_phrase:
                    candidate["score"] += 25.0
            else:
                candidate["matched_query"] = expanded_query
                candidate["match_source"] = "EXPANDED_QUERY"

                candidate["score"] *= 0.45
                candidate["score"] += (
                    10.0 * original_term_coverage
                )

            if matched_original_terms == 0:
                candidate["score"] -= 30.0

            candidate["score"] = round(
                float(candidate["score"]),
                4,
            )

            existing = merged.get(section_id)

            if (
                existing is None
                or float(candidate["score"])
                > float(existing["score"])
            ):
                merged[section_id] = candidate

    ranked_results = sorted(
        merged.values(),
        key=lambda result: (
            -float(result["score"]),
            -float(result["original_term_coverage"]),
            result["document_title"].lower(),
            result["heading"].lower(),
        ),
    )

    return {
        "query": safe_query,
        "expanded_queries": expanded_queries,
        "source": "LOCAL_INTERSYSTEMS_DOCUMENTATION_INDEX",
        "external_request_made": False,
        "filters": {
            "product": product,
            "version": version,
            "document_type": document_type.upper(),
        },
        "results": ranked_results[:max_results],
    }


def index_status() -> dict:
    """Return information about the local index."""

    if not DATABASE_PATH.exists():
        return {
            "database": str(DATABASE_PATH),
            "exists": False,
            "pages": 0,
            "sections": 0,
        }

    connection = connect_database()
    initialise_database(connection)

    pages = connection.execute(
        "SELECT COUNT(DISTINCT url) AS count FROM sections"
    ).fetchone()["count"]

    sections = connection.execute(
        "SELECT COUNT(*) AS count FROM sections"
    ).fetchone()["count"]

    products = connection.execute(
        """
        SELECT product, COUNT(*) AS sections
        FROM sections
        GROUP BY product
        ORDER BY sections DESC
        """
    ).fetchall()

    connection.close()

    return {
        "database": str(DATABASE_PATH),
        "exists": True,
        "pages": pages,
        "sections": sections,
        "products": [dict(row) for row in products],
    }


def build_parser() -> argparse.ArgumentParser:
    """Create the command-line parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Build and search a local section-level index of "
            "official InterSystems documentation."
        )
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    build_parser_command = subparsers.add_parser(
        "build",
        help="Build or update the local documentation index.",
    )
    build_parser_command.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
    )
    build_parser_command.add_argument(
        "--max-depth",
        type=int,
        default=DEFAULT_MAX_DEPTH,
    )
    build_parser_command.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY_SECONDS,
    )
    build_parser_command.add_argument(
        "--reset",
        action="store_true",
    )

    search_parser = subparsers.add_parser(
        "search",
        help="Search the local documentation index.",
    )
    search_parser.add_argument("query")
    search_parser.add_argument(
        "--product",
        default="",
    )
    search_parser.add_argument(
        "--version",
        default="",
    )
    search_parser.add_argument(
        "--document-type",
        default="",
        choices=(
            "",
            "GENERAL",
            "USER_GUIDE",
            "ADMINISTRATION",
            "INTEROPERABILITY",
            "REFERENCE",
            "RELEASE_NOTES",
        ),
    )
    search_parser.add_argument(
        "--max-results",
        type=int,
        default=DEFAULT_SEARCH_RESULTS,
    )

    subparsers.add_parser(
        "status",
        help="Show the local documentation index status.",
    )

    return parser


def main() -> int:
    """Run the documentation index command."""

    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "build":
            output = build_index(
                max_pages=args.max_pages,
                max_depth=args.max_depth,
                reset=args.reset,
                delay_seconds=args.delay,
            )
        elif args.command == "search":
            output = search_expanded_index(
                args.query,
                product=args.product,
                version=args.version,
                document_type=args.document_type,
                max_results=args.max_results,
            )
        else:
            output = index_status()
    except (
        DocumentationError,
        sqlite3.Error,
    ) as exc:
        print(
            json.dumps(
                {
                    "error": str(exc),
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())