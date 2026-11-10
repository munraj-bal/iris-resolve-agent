"""Read-only search over the local internal documentation index."""

import os
import re
import sqlite3
from pathlib import Path
from typing import Final

DB_PATH: Final = Path(
    os.environ.get("IRIS_RESOLVE_INTERNAL_DOCS", "/opt/irisapp/data/internal_docs")
) / "index" / "internal.db"

_STOPWORDS: Final = frozenset(
    "the and for with that this from what are can not does into have when "
    "there their which would should could about other".split()
)


def _enabled() -> bool:
    return os.environ.get("IRIS_RESOLVE_INTERNAL", "1") != "0"


def _fts_query(text: str) -> str:
    terms = {
        t.lower() for t in re.findall(r"[A-Za-z]{4,}", text)
        if t.lower() not in _STOPWORDS
    }
    return " OR ".join(f'"{t}"' for t in sorted(terms))


def search_internal(
    query: str,
    limit: int = 5,
) -> list[dict[str, str]]:
    """Find matching chunks and return their complete document sections."""
    if not _enabled() or not DB_PATH.exists():
        return []

    match = _fts_query(query)
    if not match:
        return []

    connection = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:
        matches = connection.execute(
            "SELECT title, section FROM chunks "
            "WHERE chunks MATCH ? "
            "ORDER BY bm25(chunks), rowid LIMIT ?",
            (match, limit),
        ).fetchall()

        results: list[dict[str, str]] = []
        seen: set[tuple[str, str]] = set()

        for title, section in matches:
            key = (title, section)
            if key in seen:
                continue
            seen.add(key)

            rows = connection.execute(
                "SELECT body FROM chunks "
                "WHERE title = ? AND section = ? "
                "ORDER BY rowid",
                (title, section),
            ).fetchall()

            # Preserve the complete section, removing the 200-character
            # overlap used by internal_ingest.py where it matches exactly.
            parts: list[str] = []

            for (body,) in rows:
                if parts and parts[-1][-200:] == body[:200]:
                    parts.append(body[200:])
                else:
                    parts.append(body)

            results.append(
                {
                    "evidence_id": f"INTERNAL-{len(results) + 1}",
                    "source": "INTERNAL_DOCUMENTATION",
                    "title": title,
                    "section": section,
                    "text": "".join(parts),
                }
            )

        return results
    finally:
        connection.close()