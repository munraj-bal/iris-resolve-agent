"""Public entry point for IRIS Resolve ticket processing."""

from __future__ import annotations

import asyncio
import json
import traceback
from typing import Any

from agent import DEFAULT_LLM_CONFIG, run_agent
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


def encode(
    result: dict[str, Any],
) -> str:
    """Serialise a solver result."""
    return json.dumps(
        result,
        ensure_ascii=False,
    )


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
        agent_result = asyncio.run(
            run_agent(
                ticket,
                llm_config_name,
            )
        )

        result = validate_agent_result(
            ticket,
            agent_result,
        )
    except Exception as exc:
        print(traceback.format_exc())

        result = technical_failure_result(
            ticket,
            str(exc),
        )

    return encode(result)