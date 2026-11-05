"""Agent-output validation and deterministic decision policy."""

from __future__ import annotations

from typing import Any

from config import ALLOWED_DECISIONS
from ticket_validation import (
    normalise_string_list,
    normalise_text,
)


USER_EVIDENCE_ID = "USER-PROVIDED-EVIDENCE"


def validate_evidence(
    value: Any,
    evidence_available: bool,
) -> list[dict[str, str]]:
    """Keep valid references to user-provided evidence."""
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


def calculate_confidence(
    ticket: dict[str, Any],
    evidence_available: bool,
    root_cause_supported: bool,
    diagnostics_available: bool,
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
            0.05 if ticket.get("environment") else 0.0
        ),
        "ccr_reference_present": (
            0.05 if ticket.get("ccr_id") else 0.0
        ),
        "user_evidence_supplied": (
            0.25 if evidence_available else 0.0
        ),
        "root_cause_supported": (
            0.20 if root_cause_supported else 0.0
        ),
        "diagnostics_available": (
            0.10 if diagnostics_available else 0.0
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
        "NEEDS_INVESTIGATION",
        "REQUEST_INFORMATION",
    }:
        return preliminary

    if confidence >= 0.85 and evidence_count:
        return "PROPOSE_RESOLUTION"

    if confidence >= 0.65 and evidence_count:
        return "PROPOSE_DIAGNOSTICS"

    if confidence >= 0.40:
        return "REQUEST_INFORMATION"

    return "NEEDS_INVESTIGATION"


def validate_agent_result(
    ticket: dict[str, Any],
    agent: dict[str, Any],
    retrieved_diagnostics: set[str],
) -> dict[str, Any]:
    """Validate model output and select the final decision."""
    preliminary = str(
        agent.get("decision")
        or "NEEDS_INVESTIGATION"
    ).strip().upper()

    if preliminary not in ALLOWED_DECISIONS:
        preliminary = "NEEDS_INVESTIGATION"

    evidence_available = bool(
        ticket.get("additional_evidence")
    )

    evidence = validate_evidence(
        agent.get("evidence"),
        evidence_available,
    )

    root_cause = normalise_text(
        agent.get("root_cause"),
        5000,
    )

    root_cause_supported = bool(
        root_cause
        and agent.get("root_cause_supported") is True
        and evidence
    )

    conflicting = (
        agent.get("conflicting_evidence") is True
    )

    requested_diagnostics = normalise_string_list(
        agent.get("diagnostic_check_ids"),
        maximum_length=100,
        uppercase=True,
    )

    diagnostics = [
        check_id
        for check_id in requested_diagnostics
        if check_id in retrieved_diagnostics
    ]

    confidence, factors = calculate_confidence(
        ticket,
        evidence_available,
        root_cause_supported,
        bool(diagnostics),
        conflicting,
    )

    decision = select_decision(
        preliminary,
        confidence,
        len(evidence),
    )

    actions = normalise_string_list(
        agent.get("recommended_actions")
    )

    if decision == "REJECT":
        actions = []
        diagnostics = []

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
            agent.get("reasoning"),
            5000,
        ),
        "evidence": evidence,
        "recommended_actions": actions,
        "missing_information": normalise_string_list(
            agent.get("missing_information")
        ),
        "risks": normalise_string_list(
            agent.get("risks")
        ),
        "diagnostic_check_ids": diagnostics,
        "conflicting_evidence": conflicting,
        "user_evidence_supplied": evidence_available,
        "requires_human_approval": True,
        "automatic_changes_performed": False,
        "status": "COMPLETED",
    }