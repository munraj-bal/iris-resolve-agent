"""Deterministic decision and result policy for IRIS Resolve."""

from __future__ import annotations

from typing import Any, Final

from validation import (
    normalise_string_list,
    normalise_text,
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

ALLOWED_INVESTIGATION_AREAS: Final[frozenset[str]] = (
    frozenset(
        {
            "MANUAL_EVIDENCE",
            "ENVIRONMENT",
            "OUTBOUND_TRACE",
            "FIND_GUID",
            "CCR_TRANSPORT",
        }
    )
)

USER_EVIDENCE_ID: Final[str] = (
    "USER-PROVIDED-EVIDENCE"
)


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
        "investigation_areas": [],
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
        "Review the IRIS Resolve application and production logs."
    ]

    result["risks"] = [
        "No support recommendation was produced because "
        "the AI workflow failed."
    ]

    return result


def validate_evidence(
    value: Any,
    evidence_available: bool,
) -> list[dict[str, str]]:
    """Keep valid user-evidence references."""
    if not evidence_available or not isinstance(value, list):
        return []

    results: list[dict[str, str]] = []

    for item in value[:50]:
        if not isinstance(item, dict):
            continue

        if item.get("evidence_id") != USER_EVIDENCE_ID:
            continue

        finding = normalise_text(
            item.get("finding"),
            2000,
        )

        if not finding:
            continue

        results.append(
            {
                "evidence_id": USER_EVIDENCE_ID,
                "source": normalise_text(
                    item.get("source"),
                    100,
                ),
                "finding": finding,
            }
        )

    return results


def validate_investigation_areas(
    value: Any,
) -> list[str]:
    """Keep approved investigation-area values."""
    requested = normalise_string_list(
        value,
        maximum_length=100,
        uppercase=True,
    )

    return [
        area
        for area in requested
        if area in ALLOWED_INVESTIGATION_AREAS
    ]


def calculate_confidence(
    ticket: dict[str, Any],
    evidence_available: bool,
    root_cause_supported: bool,
    conflicting_evidence: bool,
) -> tuple[float, dict[str, float]]:
    """Calculate confidence from deterministic factors."""
    factors = {
        "ticket_title_present": (
            0.10 if ticket.get("title") else 0.0
        ),
        "ticket_description_present": (
            0.15 if ticket.get("description") else 0.0
        ),
        "environment_present": (
            0.10 if ticket.get("environment") else 0.0
        ),
        "user_evidence_supplied": (
            0.30 if evidence_available else 0.0
        ),
        "root_cause_supported": (
            0.25 if root_cause_supported else 0.0
        ),
        "conflicting_evidence_absent": (
            0.0 if conflicting_evidence else 0.10
        ),
    }

    confidence = round(
        min(sum(factors.values()), 1.0),
        2,
    )

    return confidence, factors


def select_decision(
    preliminary: str,
    confidence: float,
    evidence_count: int,
) -> str:
    """Apply deterministic decision thresholds."""
    if preliminary in {
        "REJECT",
        "REQUEST_INFORMATION",
        "NEEDS_INVESTIGATION",
    }:
        return preliminary

    if confidence >= 0.85 and evidence_count > 0:
        return "PROPOSE_RESOLUTION"

    if confidence >= 0.65 and evidence_count > 0:
        return "PROPOSE_DIAGNOSTICS"

    if confidence >= 0.40:
        return "REQUEST_INFORMATION"

    return "NEEDS_INVESTIGATION"


def validate_agent_result(
    ticket: dict[str, Any],
    agent_result: dict[str, Any],
) -> dict[str, Any]:
    """Validate model output and select the final decision."""
    preliminary = str(
        agent_result.get("decision")
        or "NEEDS_INVESTIGATION"
    ).strip().upper()

    if preliminary not in ALLOWED_DECISIONS:
        preliminary = "NEEDS_INVESTIGATION"

    evidence_available = bool(
        ticket.get("additional_evidence")
    )

    evidence = validate_evidence(
        agent_result.get("evidence"),
        evidence_available,
    )

    root_cause = normalise_text(
        agent_result.get("root_cause"),
        5000,
    )

    root_cause_supported = bool(
        root_cause
        and agent_result.get("root_cause_supported") is True
        and evidence
    )

    conflicting_evidence = (
        agent_result.get("conflicting_evidence") is True
    )

    investigation_areas = validate_investigation_areas(
        agent_result.get("investigation_areas")
    )

    confidence, factors = calculate_confidence(
        ticket,
        evidence_available,
        root_cause_supported,
        conflicting_evidence,
    )

    decision = select_decision(
        preliminary,
        confidence,
        len(evidence),
    )

    recommended_actions = normalise_string_list(
        agent_result.get("recommended_actions")
    )

    if decision == "REJECT":
        recommended_actions = []
        investigation_areas = []

    if decision in {
        "REQUEST_INFORMATION",
        "NEEDS_INVESTIGATION",
        "REJECT",
    } and not root_cause_supported:
        root_cause = ""

    return {
        **ticket,
        "decision": decision,
        "preliminary_agent_decision": preliminary,
        "confidence": confidence,
        "confidence_percent": round(
            confidence * 100
        ),
        "confidence_factors": factors,
        "root_cause": root_cause,
        "root_cause_supported": root_cause_supported,
        "reasoning": normalise_text(
            agent_result.get("reasoning"),
            5000,
        ),
        "evidence": evidence,
        "recommended_actions": recommended_actions,
        "missing_information": normalise_string_list(
            agent_result.get("missing_information")
        ),
        "risks": normalise_string_list(
            agent_result.get("risks")
        ),
        "investigation_areas": investigation_areas,
        "conflicting_evidence": conflicting_evidence,
        "user_evidence_supplied": evidence_available,
        "requires_human_approval": True,
        "automatic_changes_performed": False,
        "status": "COMPLETED",
    }