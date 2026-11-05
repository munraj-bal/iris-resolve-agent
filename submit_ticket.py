"""Interactive command-line interface for IRIS Resolve."""

from __future__ import annotations

import base64
import json
import subprocess
import sys
from typing import Any, Final


CONTAINER_NAME: Final[str] = "iris-ai-hub"

OPTIONAL_FIELDS: Final[tuple[tuple[str, str], ...]] = (
    ("ccr_id", "CCR ID, if applicable"),
    (
        "application",
        "Application or product, for example TrakCare",
    ),
    ("site", "Site or customer"),
    ("iris_namespace", "IRIS namespace"),
    (
        "affected_identifier",
        "Affected episode, appointment, order, or message ID",
    ),
    (
        "expected_interface",
        "Expected interface or message type",
    ),
    (
        "relevant_time",
        "Relevant timestamp or time range",
    ),
)

REVIEW_LABELS: Final[tuple[tuple[str, str], ...]] = (
    ("ticket_id", "Ticket ID"),
    ("title", "Title"),
    ("ccr_id", "CCR ID"),
    ("environment", "Environment"),
    ("application", "Application"),
    ("site", "Site"),
    ("iris_namespace", "Namespace"),
    ("affected_identifier", "Affected identifier"),
    ("expected_interface", "Expected interface"),
    ("relevant_time", "Relevant time"),
)


def configure_console_encoding() -> None:
    """Configure UTF-8 output when supported."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def prompt_required(label: str) -> str:
    """Prompt until a value is provided."""
    while not (
        value := input(f"{label}: ").strip()
    ):
        print(
            "This field is required. "
            "Please enter a value."
        )

    return value


def prompt_multiline(
    label: str,
    instructions: str,
    *,
    required: bool = False,
) -> str:
    """Collect multiline text until END."""
    while True:
        print(f"\n{label}")
        print(instructions)
        print("Enter END on a new line when finished.\n")

        lines: list[str] = []

        while True:
            try:
                line = input()
            except EOFError:
                line = "END"

            if line.strip().upper() == "END":
                break

            lines.append(line)

        value = "\n".join(lines).strip()

        if value or not required:
            return value

        print("This field is required.")


def create_payload() -> dict[str, str]:
    """Collect ticket details and evidence."""
    print("=" * 72)
    print("IRIS Resolve")
    print("Read-only AI-assisted ticket investigation")
    print("=" * 72)
    print(
        "\nEnter the support ticket information. "
        "No JSON files or live connections are required."
    )

    payload = {
        "ticket_id": prompt_required("Ticket ID"),
        "title": prompt_required("Ticket title"),
        "description": prompt_multiline(
            "Ticket description",
            (
                "Enter the issue, expected behaviour, "
                "actual behaviour, and context."
            ),
            required=True,
        ),
    }

    payload.update(
        {
            key: input(f"{label}: ").strip()
            for key, label in OPTIONAL_FIELDS
        }
    )

    payload["additional_evidence"] = prompt_multiline(
        "Additional evidence, if available",
        (
            "Paste traces, transport logs, Find GUID output, "
            "SQL results, errors, configuration details, "
            "comparison cases, or investigation notes. "
            "Enter END immediately to skip."
        ),
    )

    payload["environment"] = prompt_required(
        "Affected environment, for example BASE, TEST, UAT, or LIVE"
    ).upper()

    return payload


def confirm_submission(
    payload: dict[str, str],
) -> bool:
    """Review the ticket and request confirmation."""
    print("\n" + "=" * 72)
    print("Review ticket information")
    print("=" * 72)

    for key, label in REVIEW_LABELS:
        print(
            f"{label + ':':<22}"
            f"{payload.get(key) or 'Not supplied'}"
        )

    print("\nDescription:")
    print(payload["description"])

    print("\nAdditional evidence:")
    print(
        payload["additional_evidence"]
        or "No additional evidence supplied."
    )

    while True:
        answer = input(
            "\nSubmit this ticket to IRIS Resolve? [Y/n]: "
        ).strip().lower()

        if answer in {"", "y", "yes"}:
            return True

        if answer in {"n", "no"}:
            return False

        print("Enter Y or N.")


def run_solver(
    payload: dict[str, str],
) -> dict[str, Any]:
    """Run IRIS Resolve inside the Docker container."""
    encoded = base64.b64encode(
        json.dumps(payload).encode("utf-8")
    ).decode("ascii")

    code = (
        "import base64,os,iris;"
        f"payload=base64.b64decode('{encoded}').decode('utf-8');"
        "connection=iris.connect("
        "'localhost',1972,'USER','_SYSTEM',os.environ['IRIS_PASSWORD']);"
        "proxy=iris.createIRIS(connection);"
        "result=proxy.classMethodValue("
        "'SupportAgent.TicketService','Submit',payload);"
        "print(result);"
        "connection.close()"
    )

    result = subprocess.run(
        [
            "docker",
            "exec",
            CONTAINER_NAME,
            "python3",
            "-c",
            code,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode:
        raise RuntimeError(
            result.stderr.strip()
            or result.stdout.strip()
            or "IRIS Resolve failed without output."
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
            "IRIS Resolve returned invalid JSON.\n\n"
            f"{output}"
        ) from exc


def display_list(
    title: str,
    values: list[Any],
) -> None:
    """Display a numbered list."""
    print(f"\n{title}")
    print("-" * len(title))

    if not values:
        print("None")
        return

    for index, value in enumerate(values, 1):
        print(f"{index}. {value}")


def display_evidence(
    evidence: list[dict[str, Any]],
) -> None:
    """Display validated evidence."""
    print("\nEvidence")
    print("-" * 8)

    if not evidence:
        print(
            "No supporting evidence was supplied "
            "or validated."
        )
        return

    for index, item in enumerate(evidence, 1):
        print(
            f"\n{index}. "
            f"{item.get('source', 'Unknown source')}"
        )
        print(
            "   Evidence ID: "
            f"{item.get('evidence_id', 'No ID')}"
        )
        print(
            "   Finding: "
            f"{item.get('finding', 'No finding supplied')}"
        )


def yes_no(value: Any) -> str:
    """Return Yes or No."""
    return "Yes" if value else "No"


def display_result(
    result: dict[str, Any],
) -> None:
    """Display a solver response."""
    print("\n" + "=" * 72)
    print("IRIS Resolve result")
    print("=" * 72)

    summary = (
        ("Ticket", result.get("ticket_id", "Unknown")),
        ("Environment", result.get("environment", "Unknown")),
        (
            "CCR reference",
            result.get("ccr_id") or "Not supplied",
        ),
        ("Status", result.get("status", "Unknown")),
        ("Decision", result.get("decision", "Unknown")),
        (
            "Preliminary decision",
            result.get("preliminary_agent_decision")
            or "None",
        ),
        (
            "Confidence",
            f"{result.get('confidence_percent', 0)}%",
        ),
        (
            "Manual evidence",
            yes_no(result.get("user_evidence_supplied")),
        ),
        (
            "Human approval",
            yes_no(result.get("requires_human_approval")),
        ),
        (
            "Automatic changes",
            yes_no(result.get("automatic_changes_performed")),
        ),
    )

    for label, value in summary:
        print(f"{label + ':':<23}{value}")

    print("\nAI assessment")
    print("-" * 13)
    print(
        result.get("reasoning")
        or "No assessment was returned."
    )

    if root_cause := result.get("root_cause"):
        print("\nRoot cause")
        print("-" * 10)
        print(root_cause)
        print(
            "Supported by evidence: "
            f"{yes_no(result.get('root_cause_supported'))}"
        )

    display_evidence(result.get("evidence", []))
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
        "IRIS Resolve analysed user-supplied information "
        "and performed no automatic changes."
    )
    print("=" * 72)


def main() -> int:
    """Run the interactive CLI."""
    configure_console_encoding()

    try:
        payload = create_payload()

        if not confirm_submission(payload):
            print("\nSubmission cancelled.")
            return 0

        print(
            "\nInvestigating the ticket. "
            "This may take a few moments...\n"
        )

        display_result(run_solver(payload))
        return 0

    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return 130
    except FileNotFoundError:
        print(
            "\nDocker could not be found. "
            "Confirm Docker Desktop is running.",
            file=sys.stderr,
        )
        return 1
    except RuntimeError as exc:
        print(f"\nError:\n{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())