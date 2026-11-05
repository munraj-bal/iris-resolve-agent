"""Read-only MCP policy and diagnostic tools for IRIS Resolve."""

from __future__ import annotations

import json
from typing import Any, Final

from mcp.server.fastmcp import FastMCP


mcp = FastMCP("IRISResolveTools")


RESOLUTION_POLICY: Final[dict[str, Any]] = {
    "allowed_decisions": [
        "PROPOSE_RESOLUTION",
        "PROPOSE_DIAGNOSTICS",
        "REQUEST_INFORMATION",
        "NEEDS_INVESTIGATION",
        "REJECT",
    ],
    "thresholds": {
        "PROPOSE_RESOLUTION": 0.85,
        "PROPOSE_DIAGNOSTICS": 0.65,
        "REQUEST_INFORMATION": 0.40,
    },
    "safety": {
        "access": "read_only",
        "human_approval_required": True,
        "automatic_changes_allowed": False,
        "prohibited_actions": [
            "Create or update a support ticket.",
            "Resolve a support ticket automatically.",
            "Create or update a CCR.",
            "Transport or retry a CCR.",
            "Change an item-set status.",
            "Modify an environment.",
            "Change production source code.",
            "Execute a corrective database update.",
            "Send an outbound interface message.",
        ],
    },
}


DIAGNOSTIC_CHECKS: Final[dict[str, dict[str, Any]]] = {
    "MANUAL_EVIDENCE_REVIEW": {
        "check_id": "MANUAL_EVIDENCE_REVIEW",
        "title": "Review manually supplied evidence",
        "read_only": True,
        "steps": [
            "Identify each evidence source.",
            "Separate facts from assumptions.",
            "Check timestamps, identifiers, and environments.",
            "Identify contradictions and missing context.",
        ],
    },
    "ENVIRONMENT_CONFIRMATION": {
        "check_id": "ENVIRONMENT_CONFIRMATION",
        "title": "Confirm the affected environment",
        "read_only": True,
        "steps": [
            "Read the ticket environment.",
            "Compare it with the supplied evidence.",
            "Report any mismatch.",
        ],
    },
    "OUTBOUND_TRACE_REVIEW": {
        "check_id": "OUTBOUND_TRACE_REVIEW",
        "title": "Review outbound trace evidence",
        "read_only": True,
        "steps": [
            "Identify the expected event and message type.",
            "Compare event and trace timestamps.",
            "Check generation, routing, suppression, and transmission.",
            "Request missing trace sections.",
        ],
    },
    "FIND_GUID_REVIEW": {
        "check_id": "FIND_GUID_REVIEW",
        "title": "Review Find GUID evidence",
        "read_only": True,
        "steps": [
            "Identify each GUID and referenced record.",
            "Compare BASE and target environments.",
            "Identify the introducing CCR or item set.",
            "Check prerequisite progression.",
            "Do not modify GUIDs automatically.",
        ],
    },
    "CCR_TRANSPORT_EVIDENCE_REVIEW": {
        "check_id": "CCR_TRANSPORT_EVIDENCE_REVIEW",
        "title": "Review CCR transport evidence",
        "read_only": True,
        "steps": [
            "Confirm the CCR and target environment.",
            "Identify failed or incomplete item sets.",
            "Review dependencies and referenced identifiers.",
            "Identify the latest available status.",
            "Do not retry or update the CCR.",
        ],
    },
}


def response(
    tool: str,
    data: Any,
) -> str:
    """Create a successful MCP response."""
    return json.dumps(
        {
            "ok": True,
            "tool": tool,
            "read_only": True,
            "data": data,
        },
        ensure_ascii=False,
    )


def error(
    tool: str,
    message: str,
) -> str:
    """Create a controlled MCP error response."""
    return json.dumps(
        {
            "ok": False,
            "tool": tool,
            "read_only": True,
            "error": message,
            "available_check_ids": sorted(
                DIAGNOSTIC_CHECKS
            ),
        },
        ensure_ascii=False,
    )


@mcp.tool()
def get_resolution_policy() -> str:
    """Return decision and safety policy."""
    return response(
        "get_resolution_policy",
        RESOLUTION_POLICY,
    )


@mcp.tool()
def get_diagnostic_check(
    check_id: str,
) -> str:
    """Return one approved diagnostic procedure."""
    normalised = str(
        check_id or ""
    ).strip().upper()

    check = DIAGNOSTIC_CHECKS.get(normalised)

    if not check:
        return error(
            "get_diagnostic_check",
            (
                "Unknown diagnostic check: "
                f"{normalised or '<empty>'}"
            ),
        )

    return response(
        "get_diagnostic_check",
        check,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")