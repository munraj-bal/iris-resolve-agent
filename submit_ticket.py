"""Interactive command-line interface for IRIS Resolve."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from typing import Any


CONTAINER_NAME = "iris-ai-hub"


def configure_console_encoding() -> None:
    """Configure UTF-8 output when supported."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

def prompt_required(label: str) -> str:
    """Prompt until the user provides a non-empty value."""
    while True:
        value = input(f"{label}: ").strip()

        if value:
            return value

        print("This field is required. Please enter a value.")


def prompt_optional(label: str) -> str:
    """Prompt for an optional value."""
    return input(f"{label}: ").strip()


def prompt_multiline(
    label: str,
    *,
    required: bool,
    instructions: str,
) -> str:
    """Collect multiline text until the user enters END."""
    print(f"\n{label}")
    print(instructions)
    print("Enter END on a new line when finished.\n")

    lines: list[str] = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        if line.strip().upper() == "END":
            break

        lines.append(line)

    value = "\n".join(lines).strip()

    if required and not value:
        print("This field is required.")
        return prompt_multiline(
            label,
            required=True,
            instructions=instructions,
        )

    return value


def create_payload() -> dict[str, str]:
    """Collect ticket details and optional evidence from the user."""
    print("=" * 72)
    print("IRIS Resolve")
    print("Read-only AI-assisted ticket investigation")
    print("=" * 72)

    print(
        "\nEnter the support ticket information. "
        "No JSON files or live system connections are required."
    )

    ticket_id = prompt_required("Ticket ID")
    title = prompt_required("Ticket title")

    description = prompt_multiline(
        "Ticket description",
        required=True,
        instructions=(
            "Paste or type the reported issue, expected behaviour, "
            "actual behaviour, and relevant context."
        ),
    )

    ccr_id = prompt_optional(
        "CCR ID, if applicable"
    )

    application = prompt_optional(
        "Application or product, for example TrakCare"
    )

    site = prompt_optional(
        "Site or customer"
    )

    iris_namespace = prompt_optional(
        "IRIS namespace"
    )

    affected_identifier = prompt_optional(
        "Affected episode, appointment, order, or message ID"
    )

    expected_interface = prompt_optional(
        "Expected interface or message type"
    )

    relevant_time = prompt_optional(
        "Relevant timestamp or time range"
    )

    additional_evidence = prompt_multiline(
        "Additional evidence, if available",
        required=False,
        instructions=(
            "Paste outbound traces, transport logs, Find GUID output, "
            "SQL results, error messages, configuration details, "
            "queue status, successful comparison cases, or previous "
            "investigation notes. Enter END immediately to skip."
        ),
    )

    environment = prompt_required(
        "Affected environment, for example BASE, TEST, UAT, or LIVE"
    ).upper()

    return {
        "ticket_id": ticket_id,
        "title": title,
        "description": description,
        "ccr_id": ccr_id,
        "application": application,
        "site": site,
        "iris_namespace": iris_namespace,
        "affected_identifier": affected_identifier,
        "expected_interface": expected_interface,
        "relevant_time": relevant_time,
        "additional_evidence": additional_evidence,
        "environment": environment,
    }


def confirm_submission(payload: dict[str, str]) -> bool:
    """Display the supplied information and request confirmation."""
    print("\n" + "=" * 72)
    print("Review ticket information")
    print("=" * 72)

    print(f"Ticket ID:   {payload['ticket_id']}")
    print(f"Title:       {payload['title']}")
    print(f"CCR ID:      {payload['ccr_id'] or 'Not supplied'}")
    print(f"Environment: {payload['environment']}")
    print(
        f"Application: {payload['application'] or 'Not supplied'}"
    )
    print(
        f"Site:        {payload['site'] or 'Not supplied'}"
    )
    print(
        f"Namespace:   {payload['iris_namespace'] or 'Not supplied'}"
    )
    print(
        "Affected identifier:  "
        f"{payload['affected_identifier'] or 'Not supplied'}"
    )
    print(
        "Expected interface:   "
        f"{payload['expected_interface'] or 'Not supplied'}"
    )
    print(
        "Relevant time:        "
        f"{payload['relevant_time'] or 'Not supplied'}"
    )


    print("\nDescription:")
    print(payload["description"])

    print("\nAdditional evidence:")
    print(
        payload["additional_evidence"]
        or "No additional evidence supplied."
    )

    while True:
        response = input(
            "\nSubmit this ticket to IRIS Resolve? [Y/n]: "
        ).strip().lower()

        if response in {"", "y", "yes"}:
            return True

        if response in {"n", "no"}:
            return False

        print("Enter Y or N.")


def run_solver(payload: dict[str, str]) -> dict[str, Any]:
    """Run solver.py inside the IRIS Docker container."""
    encoded_payload = base64.b64encode(
        json.dumps(payload).encode("utf-8")
    ).decode("ascii")

    python_code = (
        "import base64,json,solver;"
        f"payload=base64.b64decode('{encoded_payload}').decode('utf-8');"
        "result=solver.process_ticket(payload);"
        "print(result)"
    )

    command = [
        "docker",
        "exec",
        CONTAINER_NAME,
        "python3",
        "-c",
        python_code,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        error_output = (
            result.stderr.strip()
            or result.stdout.strip()
        )

        raise RuntimeError(
            "IRIS Resolve could not run successfully.\n\n"
            f"{error_output}"
        )

    output = result.stdout.strip()

    if not output:
        raise RuntimeError(
            "IRIS Resolve returned no output."
        )

    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "IRIS Resolve returned an invalid response.\n\n"
            f"Raw output:\n{output}"
        ) from exc


def display_list(
    title: str,
    values: list[Any],
) -> None:
    """Display a titled list."""
    print(f"\n{title}")
    print("-" * len(title))

    if not values:
        print("None")
        return

    for index, value in enumerate(values, start=1):
        print(f"{index}. {value}")


def display_evidence(
    evidence: list[dict[str, Any]],
) -> None:
    """Display evidence used by the solver."""
    print("\nEvidence")
    print("-" * 8)

    if not evidence:
        print("No supporting evidence was supplied or validated.")
        return

    for index, item in enumerate(evidence, start=1):
        source = item.get(
            "source",
            "Unknown source",
        )
        evidence_id = item.get(
            "evidence_id",
            "No ID",
        )
        finding = item.get(
            "finding",
            "No finding supplied",
        )

        print(f"\n{index}. {source}")
        print(f"   Evidence ID: {evidence_id}")
        print(f"   Finding: {finding}")


def yes_no(value: Any) -> str:
    """Convert a Boolean-like value into Yes or No."""
    return "Yes" if value else "No"


def display_result(result: dict[str, Any]) -> None:
    """Display the solver response in a user-friendly format."""
    print("\n" + "=" * 72)
    print("IRIS Resolve result")
    print("=" * 72)

    print(
        f"Ticket:              "
        f"{result.get('ticket_id', 'Unknown')}"
    )
    print(
        f"Environment:         "
        f"{result.get('environment', 'Unknown')}"
    )
    print(
        f"CCR reference:       "
        f"{result.get('ccr_id') or 'Not supplied'}"
    )
    print(
        f"Status:              "
        f"{result.get('status', 'Unknown')}"
    )
    print(
        f"Decision:            "
        f"{result.get('decision', 'Unknown')}"
    )
    print(
        "Preliminary decision: "
        f"{result.get('preliminary_agent_decision') or 'None'}"
    )
    print(
        f"Confidence:          "
        f"{result.get('confidence_percent', 0)}%"
    )
    print(
        "Manual evidence:     "
        f"{yes_no(result.get('user_evidence_supplied'))}"
    )
    print(
        "Human approval:      "
        f"{yes_no(result.get('requires_human_approval'))}"
    )
    print(
        "Automatic changes:   "
        f"{yes_no(result.get('automatic_changes_performed'))}"
    )

    print("\nAI assessment")
    print("-" * 13)
    print(
        result.get("reasoning")
        or "No assessment was returned."
    )

    root_cause = result.get("root_cause")

    if root_cause:
        print("\nRoot cause")
        print("-" * 10)
        print(root_cause)
        print(
            "Supported by evidence: "
            f"{yes_no(result.get('root_cause_supported'))}"
        )

    display_evidence(
        result.get("evidence", [])
    )
    display_list(
        "Recommended actions",
        result.get("recommended_actions", []),
    )
    display_list(
        "Missing information",
        result.get("missing_information", []),
    )
    display_list(
        "Risks and limitations",
        result.get("risks", []),
    )
    display_list(
        "Proposed diagnostic checks",
        result.get("diagnostic_check_ids", []),
    )

    print("\n" + "=" * 72)
    print(
        "IRIS Resolve analysed user-supplied information only "
        "and performed no automatic changes."
    )
    print("=" * 72)


def main() -> int:
    """Run the interactive CLI."""
    configure_console_encoding()

    try:
        payload = create_payload()

        if not confirm_submission(payload):
            print(
                "\nSubmission cancelled. "
                "No information was sent."
            )
            return 0

        print(
            "\nInvestigating the ticket. "
            "This may take a few moments...\n"
        )

        result = run_solver(payload)
        display_result(result)
        return 0

    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return 130

    except FileNotFoundError:
        print(
            "\nError: Docker could not be found. "
            "Confirm Docker Desktop is installed and running.",
            file=sys.stderr,
        )
        return 1

    except RuntimeError as exc:
        print(
            f"\nError:\n{exc}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())