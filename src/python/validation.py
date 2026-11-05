"""Ticket parsing, normalisation, and input safety checks."""

from __future__ import annotations

import json
import re
from typing import Any, Final


FIELD_LIMITS: Final[dict[str, int]] = {
    "ticket_id": 100,
    "title": 1000,
    "description": 20_000,
    "ccr_id": 100,
    "application": 200,
    "site": 200,
    "iris_namespace": 100,
    "affected_identifier": 500,
    "expected_interface": 500,
    "relevant_time": 500,
    "additional_evidence": 50_000,
    "environment": 100,
}

REQUIRED_FIELDS: Final[tuple[str, ...]] = (
    "title",
    "description",
)

INJECTION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bignore\s+(all\s+)?previous\s+instructions\b",
        r"\breveal\s+(the\s+)?system\s+prompt\b",
        r"\bdeveloper\s+message\b",
        r"\bdisable\s+(the\s+)?safety\b",
        r"\bbypass\s+(the\s+)?policy\b",
    )
)


def normalise_text(
    value: Any,
    maximum_length: int,
) -> str:
    """Convert a scalar value into bounded text."""
    if value is None:
        return ""

    if isinstance(value, (dict, list, tuple, set)):
        raise ValueError(
            "Ticket text fields must contain scalar values."
        )

    return str(value).strip()[:maximum_length]


def normalise_string_list(
    value: Any,
    *,
    maximum_items: int = 20,
    maximum_length: int = 2000,
    uppercase: bool = False,
) -> list[str]:
    """Normalise and de-duplicate a list of strings."""
    if not isinstance(value, list):
        return []

    results: list[str] = []

    for item in value[:maximum_items]:
        if not isinstance(item, str):
            continue

        text = item.strip()[:maximum_length]

        if uppercase:
            text = text.upper()

        if text and text not in results:
            results.append(text)

    return results


def parse_ticket(
    raw_ticket_json: str,
) -> dict[str, str]:
    """Parse and normalise one ticket JSON object."""
    if not isinstance(raw_ticket_json, str):
        raise TypeError(
            "Ticket input must be a JSON string."
        )

    payload = json.loads(raw_ticket_json)

    if not isinstance(payload, dict):
        raise ValueError(
            "Ticket input must contain a JSON object."
        )

    return {
        field: normalise_text(
            payload.get(field),
            maximum_length,
        )
        for field, maximum_length in FIELD_LIMITS.items()
    }


def find_missing_fields(
    ticket: dict[str, str],
) -> list[str]:
    """Return required fields containing no value."""
    return [
        field
        for field in REQUIRED_FIELDS
        if not ticket.get(field)
    ]


def detect_instruction_injection(
    ticket: dict[str, str],
) -> str | None:
    """Detect explicit instruction-injection phrases."""
    combined_text = "\n".join(ticket.values())

    if any(
        pattern.search(combined_text)
        for pattern in INJECTION_PATTERNS
    ):
        return (
            "Ticket input contains an instruction-injection "
            "pattern and was rejected."
        )

    return None