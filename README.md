# IRIS Resolve

IRIS Resolve is a read-only support ticket investigation agent built with InterSystems IRIS, IRIS Interoperability, IRIS AI Hub, LangChain, and Amazon Bedrock.

Users submit ticket details and technical evidence through an interactive command-line interface. The request passes through an IRIS Interoperability production, where an IRIS AI Hub agent analyses the evidence and returns a structured recommendation for human review.

IRIS Resolve never applies automatic corrective actions.

## Key features

- InterSystems IRIS Interoperability production
- Business Service and Business Process message flow
- IRIS AI Hub agent using Amazon Bedrock
- Interactive command-line interface
- General and CCR-related ticket support
- TrakCare and IRIS technical context
- Evidence-based investigation recommendations
- Deterministic confidence calculation
- Instruction-injection detection
- Five controlled decision outcomes
- Message Viewer and Visual Trace support
- Mandatory human approval
- No automatic ticket, CCR, data, code, or configuration changes

## Interoperability workflow

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
Deterministic validation
        |
        | SupportAgent.ResolutionResponse
        v
SupportAgent.TicketService
        |
        v
submit_ticket.py displays the result
```

Each ticket submission creates two Interoperability messages in one session:

1. `IRIS Resolve Ticket Service` sends a `SupportAgent.TicketRequest` to `IRIS Resolve Process`.
2. `IRIS Resolve Process` returns a `SupportAgent.ResolutionResponse` to the service.

The complete request and response can be inspected in the IRIS Management Portal using Message Viewer and Visual Trace.

## Decision outcomes

IRIS Resolve returns one of five decisions:

| Decision | Meaning |
|---|---|
| `PROPOSE_RESOLUTION` | The supplied evidence supports a likely root cause and a human-reviewed resolution. |
| `PROPOSE_DIAGNOSTICS` | A focused investigation can be proposed, but more read-only evidence is required. |
| `REQUEST_INFORMATION` | Essential ticket or technical information is missing. |
| `NEEDS_INVESTIGATION` | The evidence is insufficient, inconclusive, or materially conflicting. |
| `REJECT` | The input is invalid or contains a detected instruction-injection attempt. |

The AI model selects a preliminary decision. Python validates the evidence, calculates confidence, validates the investigation areas, and selects the final decision.

## Investigation areas

IRIS Resolve classifies recommendations into controlled investigation areas:

- `MANUAL_EVIDENCE`
- `ENVIRONMENT`
- `OUTBOUND_TRACE`
- `FIND_GUID`
- `CCR_TRANSPORT`

These values categorise the recommended investigation. They do not represent connections to live customer systems.

## Confidence calculation

Confidence is calculated deterministically from:

- Ticket title present
- Ticket description present
- Environment present
- User evidence supplied
- Root cause supported by evidence
- Absence of conflicting evidence

Current thresholds are:

| Decision | Minimum confidence |
|---|---:|
| `PROPOSE_RESOLUTION` | 85% |
| `PROPOSE_DIAGNOSTICS` | 65% |
| `REQUEST_INFORMATION` | 40% |

Confidence is capped for outcomes where the evidence remains incomplete or conflicting.

## Safety model

IRIS Resolve treats ticket content and pasted evidence as untrusted input.

The application can:

- Analyse ticket descriptions
- Analyse manually pasted technical evidence
- Separate facts from hypotheses
- Identify missing or contradictory information
- Classify relevant investigation areas
- Recommend read-only investigation steps
- Propose human-reviewed resolutions

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

Users can paste evidence such as:

- Error messages
- Application and production logs
- CCR transport output
- Outbound interface traces
- Find GUID results
- SQL query output
- Configuration details
- Queue status
- Relevant timestamps
- Successful comparison cases
- Previous investigation notes

A supplied CCR ID is contextual information only.

Manually pasted evidence is identified as user-supplied and is not described as independently verified.

## Example use cases

IRIS Resolve can assist with investigations such as:

- An expected HL7 message was not generated
- A message was generated but not routed or transmitted
- A CCR item set failed during `Load()`
- A CCR contains missing GUID references
- A CCR appears to have an incorrect prerequisite
- A rescheduled appointment lost an association required by an interface
- Ticket communications contain incomplete or contradictory evidence

## Project structure

```text
iris-resolve-agent/
|-- src/
|   |-- python/
|   |   |-- agent.py
|   |   |-- policy.py
|   |   |-- solver.py
|   |   `-- validation.py
|   `-- SupportAgent/
|       |-- Production.cls
|       |-- ResolutionProcess.cls
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

`submit_ticket.py` collects ticket details and evidence, displays a review screen, and submits the JSON payload through the IRIS Native API.

The CLI does not call the Python solver directly.

### Business Service

`SupportAgent.TicketService` is the entry point into the Interoperability production.

The service:

1. Receives the JSON payload.
2. Creates a `SupportAgent.TicketRequest`.
3. Sends the request to `IRIS Resolve Process`.
4. Receives a `SupportAgent.ResolutionResponse`.
5. Returns the resolution JSON to the CLI.

### Business Process

`SupportAgent.ResolutionProcess` invokes `solver.process_ticket()` through Embedded Python.

The process runs the AI-assisted investigation and returns the validated result.

### Python solver

The Python implementation is divided into four focused modules:

| Module | Responsibility |
|---|---|
| `solver.py` | Public entry point and workflow coordination |
| `agent.py` | IRIS AI Hub model execution and response parsing |
| `policy.py` | Evidence validation, confidence, decisions, and result construction |
| `validation.py` | Ticket parsing, normalisation, required fields, and injection checks |

### Setup

`SupportAgent.Setup` configures:

- IRIS Wallet credentials
- Amazon Bedrock model configuration
- `AI.LLM.claude_single`

The model is loaded through the IRIS AI Hub Config Store.

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

Set the private local IRIS password:

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

Check the status:

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
- IRIS AI Hub configuration

Do not run:

```cmd
docker compose down -v
```

The `-v` option deletes the persistent volume.

## Configure IRIS Resolve

Open the IRIS terminal in the `USER` namespace:

```cmd
docker exec -it iris-ai-hub iris session IRIS -U USER
```

Compile the application classes:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/TicketRequest.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionResponse.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionProcess.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/TicketService.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/Production.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/Setup.cls","ck")
```

Register the IRIS AI Hub descriptors:

```objectscript
Do ##class(%ConfigStore.DescriptorManager).RebuildRegistry()
```

Initialise the Amazon Bedrock model using a private API key:

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

Exit:

```objectscript
Halt
```

## Verify the production

Open the IRIS System Management Portal:

```text
http://localhost:9092/csp/sys/UtilHome.csp
```

Select the `USER` namespace, then open:

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

Start the CLI:

```cmd
python submit_ticket.py
```

The CLI prompts for:

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

Enter `END` on a new line to finish a multiline field.

## Demonstration

The following synthetic example produces a supported resolution:

```text
Ticket ID: SIMPLIFIED-RESOLUTION-001
Ticket title:
Rescheduled appointment lost the order association required for Patient Hub
messaging

Ticket description:
A rescheduled TrakCare appointment did not generate the expected Patient Hub
message.

A read-only comparison of the original appointment, rescheduled appointment,
and a successful equivalent appointment has been completed.
END

CCR ID:

Application or product: TrakCare T2024
Site or customer: Synthetic demonstration
IRIS namespace: DEMO-TEST
Affected identifier: Appointments DEMO-111111 and DEMO-654321
Expected interface or message type: Appointment message to Patient Hub
Relevant timestamp or time range:
Appointment rescheduled at 10:15; trace reviewed from 10:00 to 10:30

Additional evidence:
The original appointment DEMO-111111 links to order DEMO-ORDER-001.
The rescheduled appointment DEMO-654321 has an empty order-link field.
The order remains linked to the original appointment.
No Patient Hub message was generated for DEMO-654321.
A successful equivalent appointment has a valid order link and generated the
expected message.
The missing order association was the only material difference found.
No data or configuration was changed.
END

Affected environment: TEST
```

A representative result is:

```text
Decision:              PROPOSE_RESOLUTION
Confidence:            100%
Manual evidence:       Yes
Human approval:        Yes
Automatic changes:     No
```

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

The first message contains the ticket request.

The second message contains the complete structured AI result.

Open the session in Visual Trace to inspect the full request and response path.

## Example structured result

```json
{
  "decision": "PROPOSE_RESOLUTION",
  "confidence": 1.0,
  "confidence_percent": 100,
  "root_cause_supported": true,
  "investigation_areas": [
    "MANUAL_EVIDENCE",
    "OUTBOUND_TRACE",
    "ENVIRONMENT"
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