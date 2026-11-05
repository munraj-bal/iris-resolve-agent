"""IRIS AI Hub and MCP agent execution."""

from __future__ import annotations

import json
import os
from typing import Any

import iris
from langchain.agents import create_agent
from langchain_intersystems.chat_models import init_chat_model
from langchain_mcp_adapters.tools import load_mcp_tools
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config import (
    IRIS_PYTHON_PATH,
    MCP_ERROR_LOG_PATH,
    MCP_SERVER_PATH,
)
from prompts import build_agent_prompt


def extract_text(content: Any) -> str:
    """Extract text from a model response."""
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []

        for block in content:
            if isinstance(block, dict):
                text = block.get("text")

                if isinstance(text, str):
                    parts.append(text)
            elif isinstance(block, str):
                parts.append(block)

        return "".join(parts).strip()

    raise ValueError(
        "Unexpected agent response content type."
    )


def parse_json_object(
    text: str,
) -> dict[str, Any]:
    """Extract and parse a JSON object."""
    cleaned = text.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()

        if lines:
            lines = lines[1:]

        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]

        cleaned = "\n".join(lines).strip()

        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start < 0 or end < start:
        raise ValueError(
            "The agent response did not contain a JSON object."
        )

    result = json.loads(cleaned[start : end + 1])

    if not isinstance(result, dict):
        raise ValueError(
            "The agent response must be a JSON object."
        )

    return result


def parse_tool_result(
    content: Any,
) -> dict[str, Any]:
    """Parse a JSON MCP response."""
    if isinstance(content, list):
        content = "".join(
            str(block.get("text") or "")
            for block in content
            if isinstance(block, dict)
        )

    if not isinstance(content, str):
        raise TypeError(
            "Unexpected MCP tool response type."
        )

    result = json.loads(content)

    if not isinstance(result, dict):
        raise ValueError(
            "MCP tool response must be a JSON object."
        )

    return result


def extract_diagnostic_ids(
    messages: list[Any],
) -> set[str]:
    """Return successful diagnostic IDs retrieved through MCP."""
    check_ids: set[str] = set()

    for message in messages:
        message_type = getattr(message, "type", "")
        message_name = getattr(message, "name", "")

        if message_type != "tool" and not message_name:
            continue

        try:
            result = parse_tool_result(
                getattr(message, "content", "")
            )
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            continue

        if not result.get("ok"):
            continue

        data = result.get("data")

        if (
            result.get("tool") == "get_diagnostic_check"
            and isinstance(data, dict)
            and data.get("check_id")
        ):
            check_ids.add(str(data["check_id"]))

    return check_ids


def mcp_environment() -> dict[str, str]:
    """Return the MCP subprocess environment."""
    environment = os.environ.copy()
    existing_path = environment.get("PYTHONPATH", "")

    environment["PYTHONPATH"] = os.pathsep.join(
        value
        for value in (IRIS_PYTHON_PATH, existing_path)
        if value
    )

    return environment


async def run_agent(
    ticket: dict[str, Any],
    llm_config_name: str,
) -> tuple[dict[str, Any], set[str]]:
    """Run the configured AI Hub model and MCP tools."""
    connection = iris.connect(
        "localhost",
        1972,
        "USER",
        "_SYSTEM",
        os.environ["IRIS_PASSWORD"],
    )

    try:
        model = init_chat_model(
            llm_config_name,
            connection,
        )

        parameters = StdioServerParameters(
            command="python3",
            args=[MCP_SERVER_PATH],
            env=mcp_environment(),
        )

        with open(
            MCP_ERROR_LOG_PATH,
            "a",
            encoding="utf-8",
        ) as error_log:
            async with stdio_client(
                parameters,
                errlog=error_log,
            ) as (read_stream, write_stream):
                async with ClientSession(
                    read_stream,
                    write_stream,
                ) as session:
                    await session.initialize()

                    tools = await load_mcp_tools(session)
                    agent = create_agent(model, tools)

                    result = await agent.ainvoke(
                        {
                            "messages": [
                                {
                                    "role": "user",
                                    "content": build_agent_prompt(
                                        ticket
                                    ),
                                }
                            ]
                        }
                    )

        messages = result.get("messages", [])

        if not messages:
            raise ValueError(
                "The agent returned no messages."
            )

        agent_output = parse_json_object(
            extract_text(messages[-1].content)
        )

        return (
            agent_output,
            extract_diagnostic_ids(messages),
        )
    finally:
        connection.close()