# IRIS Resolve

IRIS Resolve is a read-only support ticket investigation agent built with InterSystems IRIS, IRIS Interoperability, IRIS AI Hub, Model Context Protocol, LangChain, and Amazon Bedrock.

Users enter ticket details and optionally paste technical evidence. The request passes through an IRIS Interoperability production, where an IRIS AI Hub agent evaluates the evidence, calls approved read-only MCP diagnostic tools, and returns a structured recommendation for human review.

IRIS Resolve never applies automatic corrective actions.

## Overview

Support investigations often require information from several technical areas, including:

- TrakCare audit history
- IRIS namespaces and productions
- HL7 message traces
- Routing and suppression rules
- CCR transport output
- Find GUID results
- SQL query output
- Configuration records
- Queue status
- Previous investigation notes

IRIS Resolve provides a structured workflow for supplying this evidence to an AI agent.

The agent separates established facts from hypotheses, selects an appropriate investigation outcome, calls approved diagnostic tools, and returns practical next steps.

## Key features

- InterSystems IRIS Interoperability production
- Business Service and Business Process message flow
- Interactive command-line interface
- General and CCR-related ticket support
- Multiline ticket descriptions and technical evidence
- TrakCare and InterSystems IRIS investigation context
- IRIS AI Hub model configuration
- Amazon Bedrock model integration
- Read-only MCP diagnostic tools
- Deterministic evidence validation
- Deterministic confidence calculation
- Instruction-injection detection
- Five structured decision outcomes
- Message Viewer and Visual Trace support
- Mandatory human approval
- No automatic ticket, CCR, data, code, or configuration changes

## Interoperability workflow

IRIS Resolve runs through an InterSystems IRIS Interoperability production:

```text
submit_ticket.py
        |
        | IRIS Native API
        v
SupportAgent.TicketService
        |
        | SupportAgent.TicketRequest
        v
SupportAgent.ResolutionProcess
        |
        | Embedded Python
        v
solver.process_ticket()
        |
        v
IRIS AI Hub
        |
        v
Amazon Bedrock
        |
        v
Read-only MCP tools
        |
        v
Deterministic validation and confidence calculation
        |
        | SupportAgent.ResolutionResponse
        v
SupportAgent.TicketService
        |
        v
submit_ticket.py displays the result
```

Each submission creates two Interoperability messages in one session:

1. `IRIS Resolve Ticket Service` sends a `SupportAgent.TicketRequest` to `IRIS Resolve Process`.
2. `IRIS Resolve Process` returns a `SupportAgent.ResolutionResponse` to the service.

The complete request and response can be inspected in the IRIS Management Portal using Message Viewer and Visual Trace.

## Decision outcomes

IRIS Resolve returns one of five decisions:

| Decision | Meaning |
|---|---|
| `PROPOSE_RESOLUTION` | The supplied evidence directly supports a likely root cause and a human-reviewed resolution. |
| `PROPOSE_DIAGNOSTICS` | A focused investigation path exists, but further read-only diagnostics are required. |
| `REQUEST_INFORMATION` | Essential ticket or technical information is missing. |
| `NEEDS_INVESTIGATION` | The available evidence is insufficient, inconclusive, or materially conflicting. |
| `REJECT` | The input is invalid or contains a detected instruction-injection attempt. |

The AI model selects a preliminary decision. Python then validates the evidence, validates the selected diagnostics, calculates confidence, and selects the final decision.

## Confidence calculation

Confidence is calculated deterministically from factors including:

- Ticket title present
- Ticket description present
- Environment present
- CCR reference present
- User evidence supplied
- Root cause supported by evidence
- Approved diagnostic procedure retrieved
- Absence of conflicting evidence

Current thresholds are:

| Decision | Minimum confidence |
|---|---:|
| `PROPOSE_RESOLUTION` | 85% |
| `PROPOSE_DIAGNOSTICS` | 65% |
| `REQUEST_INFORMATION` | 40% |

`REJECT`, `REQUEST_INFORMATION`, and `NEEDS_INVESTIGATION` are preserved when selected for their corresponding safety or evidence conditions.

## Read-only MCP tools

The MCP server exposes approved diagnostic procedures:

- `MANUAL_EVIDENCE_REVIEW`
- `ENVIRONMENT_CONFIRMATION`
- `OUTBOUND_TRACE_REVIEW`
- `FIND_GUID_REVIEW`
- `CCR_TRANSPORT_EVIDENCE_REVIEW`

These tools return controlled investigation procedures. They do not connect to or modify external systems.

Examples:

- `OUTBOUND_TRACE_REVIEW` separates message generation, routing, filtering, suppression, queueing, transmission, and receipt.
- `FIND_GUID_REVIEW` guides comparison of GUID references across environments without changing a GUID.
- `CCR_TRANSPORT_EVIDENCE_REVIEW` reviews manually supplied CCR transport evidence without retrying or updating a CCR.

## Safety model

IRIS Resolve treats all ticket content and pasted evidence as untrusted input.

The application can:

- Analyse ticket descriptions
- Analyse manually pasted technical evidence
- Identify facts, assumptions, and contradictions
- Identify missing information
- Propose approved read-only diagnostics
- Recommend human-reviewed next steps

The application does not:

- Retrieve live iService tickets
- Retrieve live CCR records
- Access customer databases
- Access customer environments
- Retry CCR transports
- Change CCR dependencies or item sets
- Resolve tickets automatically
- Execute database updates
- Modify source code
- Apply configuration changes
- Resend interface messages
- Perform automatic corrective actions

Every result includes:

```json
{
  "requires_human_approval": true,
  "automatic_changes_performed": false
}
```

## Supported evidence

IRIS Resolve analyses information entered or pasted by the user.

Supported evidence includes:

- Error messages
- Application and production logs
- CCR transport evidence
- Outbound interface traces
- Find GUID output
- SQL results
- Configuration details
- Queue status
- Relevant timestamps
- Successful comparison cases
- Previous investigation notes

A supplied CCR ID is treated as contextual information only.

The agent does not claim that a live system was queried. Manually pasted evidence is identified as user-supplied and not independently verified.

## Example use cases

IRIS Resolve can assist with investigations such as:

- An expected HL7 message was not generated
- A message was generated but not routed or transmitted
- A CCR item set failed during `Load()`
- A CCR contains missing GUID references
- A CCR appears to have an incorrect prerequisite
- A rescheduled appointment lost an association required by an outbound interface
- Ticket communications contain incomplete or contradictory evidence

## Architecture

```text
CLI and Native API
        |
        v
IRIS Interoperability Production
        |
        +-- IRIS Resolve Ticket Service
        |
        +-- IRIS Resolve Process
                    |
                    v
              solver.py
                    |
        +-----------+-----------+
        |                       |
        v                       v
ticket_validation.py       agent_runner.py
                                    |
                                    v
                              IRIS AI Hub
                                    |
                                    v
                             Amazon Bedrock
                                    |
                                    v
                           Read-only MCP tools
                                    |
                                    v
                              decisions.py
                                    |
                                    v
                               results.py
                                    |
                                    v
                     SupportAgent.ResolutionResponse
```

## Project structure

```text
iris-resolve-agent/
|-- src/
|   |-- python/
|   |   |-- agent_runner.py
|   |   |-- config.py
|   |   |-- decisions.py
|   |   |-- prompts.py
|   |   |-- results.py
|   |   |-- solver.py
|   |   |-- ticket_mcp_server.py
|   |   `-- ticket_validation.py
|   `-- SupportAgent/
|       |-- Production.cls
|       |-- ResolutionProcess.cls
|       |-- ResolutionRecord.cls
|       |-- ResolutionResponse.cls
|       |-- Setup.cls
|       |-- TicketRequest.cls
|       `-- TicketService.cls
|-- .env.example
|-- .gitignore
|-- docker-compose.yml
|-- Dockerfile
|-- LICENSE
|-- README.md
|-- requirements.txt
`-- submit_ticket.py
```

## Main components

### Interactive CLI

`submit_ticket.py` collects:

- Ticket ID
- Ticket title
- Ticket description
- Optional CCR reference
- Application or product
- Site or customer
- IRIS namespace
- Affected identifier
- Expected interface or message type
- Relevant timestamp or time range
- Optional technical evidence
- Affected environment

The user can review all information before submission.

The CLI uses the IRIS Native API to invoke `SupportAgent.TicketService.Submit()`. It does not call the Python solver directly.

### Business Service

`SupportAgent.TicketService` is the entry point into the Interoperability production.

The service:

1. Receives the JSON ticket payload.
2. Creates a `SupportAgent.TicketRequest`.
3. Sends the request synchronously to `IRIS Resolve Process`.
4. Receives the structured response.
5. Returns the resolution JSON to the CLI.

### Business Process

`SupportAgent.ResolutionProcess` receives the ticket request and invokes `solver.process_ticket()` through Embedded Python.

The Business Process returns a `SupportAgent.ResolutionResponse` containing the validated AI result.

### Solver

`solver.py` is the stable Python entry point:

```python
solver.process_ticket(raw_ticket_json)
```

The solver coordinates ticket validation, agent execution, deterministic result validation, confidence calculation, and controlled error handling.

### Agent runner

`agent_runner.py` handles:

- IRIS connection
- IRIS AI Hub model initialisation
- MCP server execution
- LangChain agent execution
- Model-response parsing
- Diagnostic-result extraction

### Validation and decisions

`ticket_validation.py` handles input parsing, normalisation, required-field checks, and instruction-injection detection.

`decisions.py` validates evidence, validates diagnostic procedures, calculates confidence, and selects the final decision.

`results.py` creates standard results for missing information, rejected input, and technical failures.

### MCP server

`ticket_mcp_server.py` provides the resolution policy, safety policy, and approved read-only diagnostic procedures.

### Setup

`SupportAgent.Setup` configures:

- IRIS Wallet credentials
- Amazon Bedrock model configuration
- MCP server configuration

## Prerequisites

- Docker Desktop
- Python 3
- Access to the required InterSystems Docker registry
- InterSystems IRIS Community AI image
- InterSystems `langchain_intersystems` wheel
- Amazon Bedrock API key
- Private local IRIS password

Place the InterSystems Early Access Program wheel in:

```text
src/python/langchain_intersystems-0.0.1-py3-none-any.whl
```

The wheel is excluded from Git.

## Installation

### 1. Create the private environment file

```cmd
copy .env.example .env
```

Edit the file:

```cmd
notepad .env
```

Set a private local IRIS password:

```env
IRIS_PASSWORD=replace_with_your_private_local_IRIS_password
```

Do not commit `.env`.

### 2. Build the Docker image

```cmd
docker compose build
```

Use a clean build after changing dependencies:

```cmd
docker compose build --no-cache
```

### 3. Start the container

```cmd
docker compose up -d
```

Check its status:

```cmd
docker compose ps
```

Wait for `iris-ai-hub` to report `healthy`.

## Persistent IRIS data

Docker Compose uses the named volume:

```text
iris-mgr
```

The volume preserves:

- IRIS databases
- Password state
- Compiled classes
- IRIS Wallet entries
- AI Hub configuration
- MCP configuration

Do not run:

```cmd
docker compose down -v
```

The `-v` option deletes the persistent volume.

## Verify the installation

### Verify Python dependencies

```cmd
docker exec iris-ai-hub python3 -c "import iris,langchain,langchain_aws,langchain_intersystems; print('All Python dependencies available')"
```

Expected:

```text
All Python dependencies available
```

### Verify the application modules

```cmd
docker exec iris-ai-hub python3 -c "import solver,agent_runner,config,decisions,prompts,results,ticket_validation; print('IRIS Resolve modules available')"
```

Expected:

```text
IRIS Resolve modules available
```

### Verify the IRIS connection

```cmd
docker exec iris-ai-hub python3 -c "import os,iris; c=iris.connect('localhost',1972,'USER','_SYSTEM',os.environ['IRIS_PASSWORD']); print('IRIS connection successful'); c.close()"
```

Expected:

```text
IRIS connection successful
```

## Configure IRIS AI Hub and Interoperability

Open an IRIS terminal:

```cmd
docker exec -it iris-ai-hub iris session IRIS -U USER
```

Compile the application classes:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/TicketRequest.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionResponse.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionRecord.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionProcess.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/TicketService.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/Production.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/Setup.cls","ck")
```

Register the AI Hub configuration descriptors:

```objectscript
Do ##class(%ConfigStore.DescriptorManager).RebuildRegistry()
```

Initialise Amazon Bedrock and MCP using a private Bedrock API key:

```objectscript
Set sc = ##class(SupportAgent.Setup).Init("YOUR_PRIVATE_BEDROCK_API_KEY")
Do $SYSTEM.Status.DisplayError(sc)
```

Do not commit, log, paste, or share the real API key.

Start the Interoperability production:

```objectscript
Set sc = ##class(Ens.Director).StartProduction("SupportAgent.Production")
Do $SYSTEM.Status.DisplayError(sc)
```

Exit the terminal:

```objectscript
Halt
```

## Verify the production

Open the System Management Portal:

```text
http://localhost:9092/csp/sys/UtilHome.csp
```

Select the `USER` namespace and open:

```text
Interoperability
→ Configure
→ Production
→ SupportAgent.Production
```

The production should show two green components:

```text
Services
└── IRIS Resolve Ticket Service

Processes
└── IRIS Resolve Process
```

## Run IRIS Resolve

Start the interactive CLI:

```cmd
python submit_ticket.py
```

The CLI guides the user through the ticket information and allows multiline evidence to be pasted by entering `END` on a new line.

## Demonstration

The following synthetic example exercises the complete Interoperability, AI Hub, Bedrock, and MCP workflow.

```text
Ticket ID: INTEROP-DEMO-001
Ticket title: TrakCare cancellation did not generate an SIU_S15 message

Ticket description:
An appointment cancellation completed successfully in TrakCare TEST, but the
expected HL7 SIU_S15 cancellation message did not appear in the reviewed
outbound trace.

Please identify the appropriate read-only investigation steps and the evidence
required before a root cause or fix is proposed.
END

CCR ID:

Application or product: TrakCare T2024
Site or customer: Synthetic demonstration
IRIS namespace: DEMO-TEST
Affected identifier: Appointment DEMO-123456
Expected interface or message type: HL7 SIU_S15
Relevant timestamp or time range:
Cancellation at 10:59:40; trace reviewed from 10:50 to 11:10

Additional evidence:
The cancellation completed without an application error.
The cancellation is visible against appointment DEMO-123456.
No SIU_S15 appeared in the reviewed outbound trace.
SIU_S12 and SIU_S14 were previously generated for the same appointment.
The trace component, filters, routing result, suppression decision and queue
status have not yet been confirmed.
END

Affected environment: TEST
```

A representative result is:

```text
Decision:              PROPOSE_DIAGNOSTICS
Confidence:            75%
Manual evidence:       Yes
Human approval:        Yes
Automatic changes:     No
```

The agent selects `OUTBOUND_TRACE_REVIEW` and recommends checking message generation, routing, filtering, suppression, queueing, transmission, and successful comparison evidence before a resolution is considered.

## Inspect the Interoperability messages

After running the CLI, open:

```text
Interoperability
→ View
→ Message Viewer
```

A successful session contains two messages:

```text
IRIS Resolve Ticket Service
        → IRIS Resolve Process

IRIS Resolve Process
        → IRIS Resolve Ticket Service
```

The first message contains the `SupportAgent.TicketRequest`.

The second message contains the `SupportAgent.ResolutionResponse`, including the complete structured AI result.

Open the session using Visual Trace to view the request and response path through the production.

## Example structured result

```json
{
  "decision": "PROPOSE_DIAGNOSTICS",
  "confidence": 0.75,
  "confidence_percent": 75,
  "root_cause": "",
  "root_cause_supported": false,
  "diagnostic_check_ids": [
    "OUTBOUND_TRACE_REVIEW"
  ],
  "user_evidence_supplied": true,
  "requires_human_approval": true,
  "automatic_changes_performed": false,
  "status": "COMPLETED"
}
```

## Security

- Never commit `.env`.
- Never commit or share an Amazon Bedrock API key.
- Store model credentials in the IRIS Wallet.
- Rotate exposed credentials.
- Treat ticket content as untrusted input.
- Use synthetic or anonymised demonstrations.
- Do not include patient-identifiable information.
- Review every recommendation before applying a change.

## Licence

See `LICENSE` for licence information.