"""Shared configuration for IRIS Resolve."""

from __future__ import annotations

from typing import Final


DEFAULT_LLM_CONFIG: Final[str] = "claude_single"

MCP_SERVER_PATH: Final[str] = (
    "/opt/irisapp/src/python/ticket_mcp_server.py"
)

MCP_ERROR_LOG_PATH: Final[str] = (
    "/tmp/iris-resolve-mcp-stderr.log"
)

IRIS_PYTHON_PATH: Final[str] = (
    "/usr/irissys/mgr/python"
)

ALLOWED_DECISIONS: Final[frozenset[str]] = frozenset(
    {
        "PROPOSE_RESOLUTION",
        "PROPOSE_DIAGNOSTICS",
        "REQUEST_INFORMATION",
        "NEEDS_INVESTIGATION",
        "REJECT",
    }
)

REQUIRED_TICKET_FIELDS: Final[tuple[str, ...]] = (
    "title",
    "description",
)

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

INJECTION_PHRASES: Final[tuple[str, ...]] = (
    r"\bignore\s+(all\s+)?previous\s+instructions\b",
    r"\breveal\s+(the\s+)?system\s+prompt\b",
    r"\bdeveloper\s+message\b",
    r"\bdisable\s+(the\s+)?safety\b",
    r"\bbypass\s+(the\s+)?policy\b",
)