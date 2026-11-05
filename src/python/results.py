"""Deterministic non-agent result builders."""

from __future__ import annotations

from typing import Any

from config import MCP_ERROR_LOG_PATH


def base_result(
    ticket: dict[str, Any],
    *,
    decision: str,
    status: str,
    reasoning: str,
) -> dict[str, Any]:
    """Create a standard safe result."""
    return {
        **ticket,
        "decision": decision,
        "preliminary_agent_decision": None,
        "confidence": 0.0,
        "confidence_percent": 0,
        "confidence_factors": {},
        "root_cause": "",
        "root_cause_supported": False,
        "reasoning": reasoning,
        "evidence": [],
        "recommended_actions": [],
        "missing_information": [],
        "risks": [],
        "diagnostic_check_ids": [],
        "conflicting_evidence": False,
        "user_evidence_supplied": bool(
            ticket.get("additional_evidence")
        ),
        "requires_human_approval": True,
        "automatic_changes_performed": False,
        "status": status,
    }


def rejected_result(
    reason: str,
    ticket: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a rejected result."""
    return base_result(
        ticket or {},
        decision="REJECT",
        status="REJECTED",
        reasoning=reason,
    )


def missing_information_result(
    ticket: dict[str, Any],
    fields: list[str],
) -> dict[str, Any]:
    """Create a result for missing required input."""
    result = base_result(
        ticket,
        decision="REQUEST_INFORMATION",
        status="COMPLETED",
        reasoning="Required ticket information is missing.",
    )

    result["missing_information"] = [
        f"Provide the ticket {field.replace('_', ' ')}."
        for field in fields
    ]

    result["risks"] = [
        "A resolution cannot be proposed without "
        "the required ticket information."
    ]

    return result


def technical_failure_result(
    ticket: dict[str, Any],
    error: str,
) -> dict[str, Any]:
    """Create a controlled technical-error result."""
    result = base_result(
        ticket,
        decision="NEEDS_INVESTIGATION",
        status="TECHNICAL_ERROR",
        reasoning=(
            f"IRIS Resolve technical error: {error}"
        ),
    )

    result["recommended_actions"] = [
        "Review the IRIS Resolve application logs.",
        f"Review the MCP stderr log at {MCP_ERROR_LOG_PATH}.",
    ]

    result["risks"] = [
        "No support resolution was produced because "
        "the agent workflow failed."
    ]

    return result