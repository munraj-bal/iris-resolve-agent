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


def infer_missing_information(
    ticket: dict[str, Any],
) -> list[str]:
    """Derive required investigation details from empty ticket fields."""

    missing: list[str] = []

    field_rules = (
        (
            "namespace",
            "Confirmed IRIS namespace.",
        ),
        (
            "affected_identifier",
            "Affected episode, appointment, order, event, or "
            "message identifier.",
        ),
        (
            "expected_interface",
            "Expected interface, route, or message type.",
        ),
        (
            "relevant_time",
            "Relevant timestamp or time range, including timezone.",
        ),
    )

    for field_name, description in field_rules:
        value = str(
            ticket.get(field_name) or ""
        ).strip()

        if not value:
            missing.append(description)

    title_and_description = " ".join(
        (
            str(ticket.get("title") or ""),
            str(ticket.get("description") or ""),
        )
    ).lower()

    if "visual trace" in title_and_description:
        missing.extend(
            [
                "Confirmed interoperability production name.",
                "Visual Trace search filters and session criteria used.",
                "Installed InterSystems IRIS product version.",
            ]
        )

    if "ccr" in title_and_description:
        missing.extend(
            [
                "Verified CCR contents and prerequisite relationships.",
                "Current transport and deployment state of each "
                "related CCR.",
            ]
        )

    return list(dict.fromkeys(missing))


def infer_diagnostic_actions(
    ticket: dict[str, Any],
    investigation_areas: list[str],
) -> list[str]:
    """Create safe read-only diagnostics for known investigation areas."""

    actions: list[str] = []

    areas = {
        str(area).strip().upper()
        for area in investigation_areas
    }

    ticket_text = " ".join(
        (
            str(ticket.get("title") or ""),
            str(ticket.get("description") or ""),
            str(ticket.get("additional_evidence") or ""),
        )
    ).lower()

    if (
        "queue" in ticket_text
        or "queued" in ticket_text
    ):
        actions.extend(
            [
                "Open the Production Monitor and record the affected "
                "business operation's queue depth and job status.",
                "Check whether a job is available in the business "
                "operation's private or actor pool.",
                "Review the Event Log for errors from the affected "
                "business operation during the supplied time range.",
                "Compare the queue depth at two points in time to determine "
                "whether the queue is static, increasing, or draining slowly.",
                "Inspect the oldest queued message read-only to identify its "
                "status, target, creation time, and any recorded error.",
            ]
        )

    if "OUTBOUND_TRACE" in areas and not (
        "queue" in ticket_text
        or "queued" in ticket_text
    ):
        actions.extend(
            [
                "Confirm the IRIS namespace and interoperability "
                "production before searching messages.",
                "Confirm the source event or message identifier and "
                "the relevant timestamp range, including timezone.",
                "Review Message Viewer and Visual Trace using the "
                "confirmed identifiers, session, filters, and time range.",
                "Review the Event Log for errors at the earliest point "
                "where the expected message flow diverges.",
            ]
        )

    if "FIND_GUID" in areas:
        actions.append(
            "Run Find GUID for each missing reference in the relevant "
            "source and target environments and record the owning item."
        )

    if "CCR_TRANSPORT" in areas:
        actions.extend(
            [
                "Review the read-only transport history and current "
                "state of each related CCR.",
                "Compare the recorded CCR prerequisites with the "
                "contents and expected deployment sequence.",
            ]
        )

    if "ENVIRONMENT" in areas:
        actions.append(
            "Verify the affected environment, namespace, product "
            "version, and configuration scope."
        )

    return list(dict.fromkeys(actions))


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

    user_evidence_available = bool(
        ticket.get("additional_evidence")
    )

    evidence = validate_evidence(
        agent_result.get("evidence"),
        user_evidence_available,
    )

    root_cause = normalise_text(
        agent_result.get("root_cause"),
        5000,
    )

    root_cause_supported = bool(
        preliminary == "PROPOSE_RESOLUTION"
        and root_cause
        and agent_result.get("root_cause_supported") is True
        and evidence
    )

    conflicting_evidence = (
        agent_result.get("conflicting_evidence") is True
    )

    investigation_areas = validate_investigation_areas(
        agent_result.get("investigation_areas")
    )

    recommended_actions = normalise_string_list(
        agent_result.get("recommended_actions")
    )

    missing_information = normalise_string_list(
        agent_result.get("missing_information")
    )

    risks = normalise_string_list(
        agent_result.get("risks")
    )

    decision = preliminary

    # A resolution cannot be proposed unless the root cause is directly
    # supported by supplied evidence.
    if (
        decision == "PROPOSE_RESOLUTION"
        and not root_cause_supported
    ):
        decision = "NEEDS_INVESTIGATION"

        if not missing_information:
            missing_information.append(
                "Evidence directly supporting the proposed root cause "
                "and resolution."
            )

    # A request for information must specify the required information.
    if decision == "REQUEST_INFORMATION":
        if not missing_information:
            missing_information = (
                infer_missing_information(ticket)
            )

        if not missing_information:
            missing_information = [
                "The identifiers, timestamps, search scope, and "
                "supporting evidence required to continue the "
                "investigation."
            ]

        root_cause = ""
        root_cause_supported = False

    # A diagnostic proposal must contain at least one read-only action.
    if decision == "PROPOSE_DIAGNOSTICS":
        if not recommended_actions:
            recommended_actions = (
                infer_diagnostic_actions(
                    ticket,
                    investigation_areas,
                )
            )

        if not recommended_actions:
            recommended_actions = [
                "Review the relevant read-only logs, identifiers, "
                "timestamps, configuration, and comparison evidence "
                "before proposing a resolution."
            ]

        if not root_cause_supported:
            root_cause = ""

    # An unresolved investigation must state what remains unresolved.
    if decision == "NEEDS_INVESTIGATION":
        if not missing_information:
            missing_information = (
                infer_missing_information(ticket)
            )

        if not missing_information:
            missing_information = [
                "Additional verified evidence is required to "
                "determine the earliest point of divergence and "
                "support a root cause."
            ]

        root_cause = ""
        root_cause_supported = False

    # Rejected requests must not contain operational instructions.
    if decision == "REJECT":
        root_cause = ""
        root_cause_supported = False
        recommended_actions = []
        investigation_areas = []

    return {
        **ticket,
        "decision": decision,
        "preliminary_agent_decision": preliminary,
        "root_cause": root_cause,
        "root_cause_supported": root_cause_supported,
        "reasoning": normalise_text(
            agent_result.get("reasoning"),
            5000,
        ),
        "evidence": evidence,
        "recommended_actions": recommended_actions,
        "missing_information": missing_information,
        "risks": risks,
        "investigation_areas": investigation_areas,
        "conflicting_evidence": conflicting_evidence,
        "user_evidence_supplied": user_evidence_available,
        "requires_human_approval": True,
        "automatic_changes_performed": False,
        "status": "COMPLETED",
    }