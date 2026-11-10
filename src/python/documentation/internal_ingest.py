"""Build a local, read-only full-text index of approved internal documents."""

import os
import re
import sqlite3
import sys
from pathlib import Path
from typing import Final, Iterator

from docx import Document

ROOT: Final = Path(
    os.environ.get("IRIS_RESOLVE_INTERNAL_DOCS", "/opt/irisapp/data/internal_docs")
)
SOURCE_DIR: Final = ROOT / "source"
DB_PATH: Final = ROOT / "index" / "internal.db"
CHUNK_CHARS: Final = 1500
OVERLAP_CHARS: Final = 200

_SCRUB_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("phone", re.compile(r"\+?\d[\d\s().-]{8,}\d")),
    ("nhs_chi", re.compile(r"\b\d{3}\s?\d{3}\s?\d{4}\b|\b\d{10}\b")),
    ("episode", re.compile(r"\b[A-Z]\d{8,}\b")),
    ("clinician", re.compile(r"\bDr\.?\s+[A-Z][A-Za-z'-]+(?:\s+[A-Z][A-Za-z'-]+)?")),
)


def _scrub(text: str) -> tuple[str, list[str]]:
    """Remove likely personal identifiers and report what was removed."""
    removed = []
    for label, pattern in _SCRUB_PATTERNS:
        for match in pattern.findall(text):
            removed.append(f"{label}: {match}")
        text = pattern.sub(f"[{label.upper()} REMOVED]", text)
    return text, removed


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _docx_sections(path: Path) -> Iterator[tuple[str, str]]:
    """Yield (heading, text) pairs, splitting the document at each heading."""
    heading, buffer = "Introduction", []
    for paragraph in Document(str(path)).paragraphs:
        style = (paragraph.style.name or "").lower()
        if style.startswith("heading"):
            if buffer:
                yield heading, _clean(" ".join(buffer))
                buffer = []
            heading = _clean(paragraph.text) or heading
            continue
        buffer.append(paragraph.text)
    if buffer:
        yield heading, _clean(" ".join(buffer))


def _chunks(text: str) -> Iterator[str]:
    start = 0
    while start < len(text):
        yield text[start:start + CHUNK_CHARS]
        start += CHUNK_CHARS - OVERLAP_CHARS


def build() -> None:
    """Rebuild the internal documentation index from the source folder."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute("DROP TABLE IF EXISTS chunks")
    connection.execute(
        "CREATE VIRTUAL TABLE chunks USING fts5("
        "title, section, body, tokenize='porter unicode61')"
    )
    total = 0
    for path in sorted(SOURCE_DIR.glob("*.docx")):
        count = 0
        for section, text in _docx_sections(path):
            text, removed = _scrub(text)
            for item in removed:
                print(f"  scrubbed in '{section}': {item}")
            for chunk in _chunks(text):
                if len(chunk) > 80:
                    connection.execute(
                        "INSERT INTO chunks VALUES (?, ?, ?)",
                        (path.stem, section, chunk),
                    )
                    count += 1
        print(f"{path.name}: {count} chunks")
        total += count
    connection.commit()
    connection.close()
    print(f"Indexed {total} chunks into {DB_PATH}")


if __name__ == "__main__":
    if not SOURCE_DIR.exists():
        sys.exit(f"Source folder not found: {SOURCE_DIR}")
    build()