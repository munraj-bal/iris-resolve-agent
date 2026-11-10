"""Public entry point for IRIS Resolve ticket processing."""

from __future__ import annotations

import asyncio
import json
import re
import traceback

from typing import Any
from documentation.internal_search import search_internal

from agent import DEFAULT_LLM_CONFIG, run_agent
from documentation.reranker import rerank_documentation
from policy import (
    missing_information_result,
    rejected_result,
    technical_failure_result,
    validate_agent_result,
)
from validation import (
    detect_instruction_injection,
    find_missing_fields,
    parse_ticket,
)


MAX_DOCUMENTATION_QUESTION_LENGTH = 180


def encode(
    result: dict[str, Any],
) -> str:
    """Serialise a solver result."""

    return json.dumps(
        result,
        ensure_ascii=False,
    )


def documentation_product(ticket: dict[str, Any]) -> str:
    """Map the supplied application to an indexed product."""

    application = str(
        ticket.get("application")
        or ticket.get("product")
        or ticket.get("application_or_product")
        or ""
    ).lower()

    if "health connect" in application:
        return "InterSystems Health Connect"

    if "iris for health" in application:
        return "InterSystems IRIS for Health"

    if "trakcare" in application:
        return "InterSystems IRIS for Health"

    return "InterSystems IRIS"


def generic_documentation_question(
    ticket: dict[str, Any],
) -> str:
    """Build a generic technical query without customer identifiers."""

    title = str(
        ticket.get("title")
        or ticket.get("summary")
        or ""
    ).strip()

    description = str(
        ticket.get("description")
        or ""
    ).strip()

    technical_text = " ".join(
        part
        for part in (
            title,
            description[:500],
        )
        if part
    )

    # Remove likely ticket, CCR, patient, episode, NHS and long numeric IDs.
    technical_text = re.sub(
        r"\bI\d{5,10}\b",
        " ",
        technical_text,
        flags=re.IGNORECASE,
    )
    technical_text = re.sub(
        r"\bCCR[-\s]?\d+\b",
        " ",
        technical_text,
        flags=re.IGNORECASE,
    )
    technical_text = re.sub(
        r"\bNHS[-\s]?\d+\b",
        " ",
        technical_text,
        flags=re.IGNORECASE,
    )
    technical_text = re.sub(
        r"\b\d{8,}[A-Za-z]?\b",
        " ",
        technical_text,
    )

    # Remove fields that are likely to contain identifying information.
    technical_text = re.sub(
        r"\b(?:patient|episode|nhs number|date of birth|dob)"
        r"\s*[:=]\s*\S+",
        " ",
        technical_text,
        flags=re.IGNORECASE,
    )

    technical_text = " ".join(
        technical_text.split()
    )

    if not technical_text:
        return "InterSystems support investigation diagnostics"

    return technical_text[
        :MAX_DOCUMENTATION_QUESTION_LENGTH
    ]


def internal_sections(question: str) -> list[dict[str, Any]]:
    """Return matching sections from the local internal documentation index."""

    try:
        matches = search_internal(question, limit=8)
    except Exception as exc:
        print(f"Internal documentation search failed: {exc}", flush=True)
        return []

    return [
        {
            "evidence_id": match["evidence_id"],
            "source": "INTERNAL_DOCUMENTATION",
            "title": match["title"],
            "heading": match["section"],
            "url": "",
            "finding": match["text"],
            "relevance": "",
            "product": "TrakCare",
            "version": "",
        }
        for match in matches
    ]


def documentation_context(
    ticket: dict[str, Any],
    llm_config_name: str,
) -> dict[str, Any]:
    """Retrieve relevant official and internal documentation safely."""

    question = generic_documentation_question(ticket)
    product = documentation_product(ticket)
    internal = internal_sections(question)

    try:
        result = rerank_documentation(
            question,
            product=product,
            version="",
            document_type="",
            max_candidates=15,
            max_selected=3,
            llm_config_name=llm_config_name,
        )
    except Exception as exc:
        error_text = (
            f"Documentation retrieval failed: "
            f"{type(exc).__name__}: {exc}"
        )

        print(error_text, flush=True)
        print(traceback.format_exc(), flush=True)

        return {
            "question": question,
            "product": product,
            "status": "AVAILABLE" if internal else "UNAVAILABLE",
            "selected_sections": internal,
            "error": error_text,
        }

    selected_sections = []

    for section in result.get(
        "selected_sections",
        [],
    ):
        selected_sections.append(
            {
                "evidence_id": section["section_id"],
                "source": "INTERSYSTEMS_DOCUMENTATION",
                "title": section["document_title"],
                "heading": section["heading"],
                "url": section["url"],
                "finding": section["excerpt"],
                "relevance": section.get(
                    "reason",
                    "",
                ),
                "product": section["product"],
                "version": section["version"],
            }
        )

    selected_sections.extend(internal)

    return {
        "question": question,
        "product": product,
        "status": (
            "AVAILABLE"
            if selected_sections
            else "NO_RELEVANT_DOCUMENTATION"
        ),
        "reranking_method": result.get(
            "reranking_method",
            "",
        ),
        "insufficient_documentation": result.get(
            "insufficient_documentation",
            False,
        ),
        "selected_sections": selected_sections,
    }


def add_documentation_evidence(
    result: dict[str, Any],
    agent_result: dict[str, Any],
    docs_context: dict[str, Any],
) -> dict[str, Any]:
    """Add only documentation explicitly cited by the final agent."""

    selected_sections = docs_context.get(
        "selected_sections",
        [],
    )

    if not selected_sections:
        return result

    reasoning = str(
        agent_result.get("reasoning") or ""
    )

    model_evidence = agent_result.get(
        "evidence",
        [],
    )

    cited_ids = {
        str(item.get("evidence_id") or "")
        for item in model_evidence
        if isinstance(item, dict)
    }

    for section in selected_sections:
        evidence_id = str(
            section.get("evidence_id") or ""
        )

        if evidence_id and evidence_id in reasoning:
            cited_ids.add(evidence_id)

    if not cited_ids:
        return result

    evidence = result.setdefault(
        "evidence",
        [],
    )

    existing_ids = {
        item.get("evidence_id")
        for item in evidence
        if isinstance(item, dict)
    }

    for section in selected_sections:
        evidence_id = section.get(
            "evidence_id",
            "",
        )

        if (
            not evidence_id
            or evidence_id not in cited_ids
            or evidence_id in existing_ids
        ):
            continue

        evidence.append(
            {
                "evidence_id": evidence_id,
                "source": section.get("source", "INTERSYSTEMS_DOCUMENTATION"),
                "finding": (
                    section.get("relevance")
                    or (
                        f"See '{section.get('heading', '')}' in "
                        f"'{section.get('title', '')}'."
                    )
                ).strip(),
            }
        )

        existing_ids.add(evidence_id)

    result["evidence"] = evidence
    return result


def process_ticket(
    raw_ticket_json: str,
    llm_config_name: str = DEFAULT_LLM_CONFIG,
) -> str:
    """Process one ticket and return validated JSON."""

    try:
        ticket = parse_ticket(raw_ticket_json)
    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        return encode(
            rejected_result(
                f"Invalid ticket input: {exc}"
            )
        )

    missing_fields = find_missing_fields(ticket)

    if missing_fields:
        return encode(
            missing_information_result(
                ticket,
                missing_fields,
            )
        )

    injection_reason = detect_instruction_injection(
        ticket
    )

    if injection_reason:
        return encode(
            rejected_result(
                injection_reason,
                ticket,
            )
        )

    try:
        agent_ticket = dict(ticket)

        docs_context = documentation_context(
            ticket,
            llm_config_name,
        )

        agent_ticket["documentation_context"] = (
            docs_context
        )

        agent_result = asyncio.run(
            run_agent(
                agent_ticket,
                llm_config_name,
            )
        )

        result = validate_agent_result(
            ticket,
            agent_result,
        )

        result = add_documentation_evidence(
            result,
            agent_result,
            docs_context,
        )
    except Exception as exc:
        print(traceback.format_exc())

        result = technical_failure_result(
            ticket,
            str(exc),
        )

    return encode(result)