# IRIS Resolve

IRIS Resolve is a read-only support ticket investigation agent built with InterSystems IRIS, IRIS Interoperability, IRIS AI Hub, LangChain, Amazon Bedrock, and a locally indexed copy of public InterSystems documentation.

Users submit ticket details and technical evidence through an interactive command-line interface. The request passes through an IRIS Interoperability production, where IRIS Resolve retrieves relevant official documentation, uses an IRIS AI Hub model to select the most useful sections, analyses the supplied evidence, and returns a structured recommendation for human review.

IRIS Resolve never performs automatic corrective actions.

## Key features

- InterSystems IRIS Interoperability production
- Business Service and Business Process message flow
- IRIS AI Hub agent using Amazon Bedrock
- Interactive command-line interface
- General and CCR-related ticket support
- TrakCare and IRIS technical context
- Evidence-based investigation recommendations
- Locally indexed public InterSystems documentation
- SQLite FTS5 section-level documentation search
- Context-aware documentation query expansion
- AI-assisted documentation reranking
- Documentation evidence linked by validated section IDs
- Deterministic structured-output validation and repair
- Instruction-injection detection
- Five controlled decision outcomes
- Message Viewer and Visual Trace support
- Mandatory human approval
- No automatic ticket, CCR, data, code, message, or configuration changes

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
        +-------------------------------+
        |                               |
        v                               v
Local documentation search         IRIS AI Hub
        |                               |
        v                               v
SQLite FTS5 candidates          Amazon Bedrock
        |
        v
AI documentation reranker
        |
        v
Validated documentation context
        |
        +---------------+
                        |
                        v
               Main ticket agent
                        |
                        v
       Deterministic policy validation
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
| `PROPOSE_RESOLUTION` | The supplied evidence directly supports a likely root cause and a human-reviewed resolution. |
| `PROPOSE_DIAGNOSTICS` | A focused read-only investigation can be proposed, but the root cause is not yet established. |
| `REQUEST_INFORMATION` | Essential ticket or technical information is missing. |
| `NEEDS_INVESTIGATION` | The evidence is insufficient, inconclusive, or materially conflicting. |
| `REJECT` | The input is invalid or contains a detected instruction-injection attempt. |

The AI model selects a preliminary decision. Python then validates the evidence, decision, recommended actions, missing information, investigation areas, and safety properties.

IRIS Resolve does not calculate or display confidence scores.

## Structured-output consistency

Python validates and repairs predictable omissions in the model output.

Examples include:

- `REQUEST_INFORMATION` must contain missing-information items.
- `PROPOSE_DIAGNOSTICS` must contain read-only recommended actions.
- `NEEDS_INVESTIGATION` must identify unresolved information or conflicts.
- `PROPOSE_RESOLUTION` requires a directly supported root cause.
- `REJECT` must not contain operational recommendations.
- Selected documentation is included only when it is materially cited by the final agent.

This prevents contradictory output such as:

```text
Decision: REQUEST_INFORMATION
Missing information: None
```

or:

```text
Decision: PROPOSE_DIAGNOSTICS
Recommended actions: None
```

## Investigation areas

IRIS Resolve classifies recommendations into controlled investigation areas:

- `MANUAL_EVIDENCE`
- `ENVIRONMENT`
- `OUTBOUND_TRACE`
- `FIND_GUID`
- `CCR_TRANSPORT`

These values categorise a recommended investigation. They do not represent live connections to customer systems.

## Official documentation retrieval

IRIS Resolve can use public documentation from `docs.intersystems.com` as a read-only reference source.

The documentation workflow is:

```text
Approved InterSystems documentation URLs
        |
        | HTTPS GET only
        v
Bounded documentation index build
        |
        v
HTML section extraction
        |
        v
Local SQLite FTS5 database
        |
        v
Context-aware query expansion
        |
        v
Top candidate sections
        |
        v
IRIS AI Hub reranker
        |
        v
Validated documentation evidence
```

### Documentation safety

External documentation access is restricted to:

- HTTPS
- `GET` requests
- `docs.intersystems.com`
- Approved documentation paths
- Bounded page counts and crawl depth
- Bounded response sizes
- No authentication
- No cookies or session tokens
- No form submission
- No upload
- No customer-system access
- No database updates

The ticket workflow searches the local SQLite database. It does not crawl the documentation site for every ticket.

### Documentation grounding

The documentation reranker can select only section IDs supplied by the local search.

Selected IDs use this format:

```text
ISC-SECTION-2E9915F33FEE3A35
```

Python discards:

- Invented section IDs
- Duplicate selections
- Unsupported output structures
- Documentation sections not present in the candidate set

Documentation establishes expected product behaviour only. It does not prove what occurred in a customer environment.

If no relevant documentation exists, IRIS Resolve returns:

```text
NO_RELEVANT_DOCUMENTATION
```

It does not force a generic or misleading documentation source into the investigation.

## Safety model

IRIS Resolve treats ticket content, pasted evidence, and retrieved documentation as untrusted input.

The application can:

- Analyse ticket descriptions
- Analyse manually pasted technical evidence
- Retrieve locally indexed public InterSystems documentation
- Select relevant documentation sections
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
- Resend or replay interface messages
- Purge queues or messages
- Restart customer productions
- Perform automatic corrective actions

Every completed result includes:

```json
{
  "requires_human_approval": true,
  "automatic_changes_performed": false
}
```

## Supported evidence

Users can paste information and evidence such as:

- Affected episode, appointment, order, event, or message identifiers
- Expected interface or message type
- Relevant timestamps or time ranges
- Error messages
- Application and production logs
- CCR transport output
- Outbound interface traces
- Find GUID results
- SQL query output
- Configuration details
- Queue status
- Successful comparison cases
- Previous investigation notes

A supplied CCR ID is contextual information only.

Manually pasted evidence is identified as user-supplied and is not described as independently verified.

## Example use cases

IRIS Resolve can assist with investigations such as:

- An expected HL7 message was not generated
- A message was generated but not routed or transmitted
- A business operation is not processing queued messages
- A result attached to an unexpected episode
- A CCR item set failed during `Load()`
- A CCR contains missing GUID references
- A CCR appears to have an incorrect prerequisite
- A rescheduled appointment lost an association required by an interface
- A clinical document did not render
- Ticket communications contain incomplete or contradictory evidence

## Project structure

```text
iris-resolve-agent/
|-- data/
|   `-- documentation/
|       `-- docs.db
|-- src/
|   |-- python/
|   |   |-- documentation/
|   |   |   |-- __init__.py
|   |   |   |-- client.py
|   |   |   |-- index.py
|   |   |   `-- reranker.py
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

The generated documentation database is excluded from Git.

## Main components

### Interactive CLI

`submit_ticket.py` collects ticket details and evidence, displays a review screen, and submits the JSON payload through the IRIS Native API.

The CLI asks for:

- Ticket ID
- Ticket title
- Ticket description
- Optional CCR reference
- Application or product
- Site or customer
- IRIS namespace
- Additional information and evidence
- Affected environment

Affected identifiers, message types, timestamps, traces, and other technical details can be included together under **Additional information and evidence**.

The CLI does not call the Python solver directly.

### Business Service

`SupportAgent.TicketService` is the programmatic entry point into the Interoperability production.

The service:

1. Receives the JSON payload.
2. Creates a `SupportAgent.TicketRequest`.
3. Sends the request to `IRIS Resolve Process`.
4. Receives a `SupportAgent.ResolutionResponse`.
5. Returns the resolution JSON to the CLI.

The service does not use a polling inbound adapter. It is invoked programmatically by the CLI.

### Business Process

`SupportAgent.ResolutionProcess` invokes `solver.process_ticket()` through Embedded Python.

The process runs the documentation-assisted investigation and returns the validated result.

### Python solver

The core implementation is divided into focused modules:

| Module | Responsibility |
|---|---|
| `solver.py` | Public entry point, workflow coordination, documentation context, and evidence integration |
| `agent.py` | IRIS AI Hub model execution, investigation instructions, and response parsing |
| `policy.py` | Evidence validation, decision validation, diagnostic repair, and result construction |
| `validation.py` | Ticket parsing, normalisation, required fields, limits, and injection checks |

### Documentation package

| Module | Responsibility |
|---|---|
| `documentation/client.py` | Safe read-only access to approved InterSystems documentation |
| `documentation/index.py` | Bounded indexing, section extraction, SQLite FTS5 search, and query expansion |
| `documentation/reranker.py` | AI Hub reranking, candidate validation, and local fallback |

### Setup

`SupportAgent.Setup` configures:

- IRIS Wallet credentials
- Amazon Bedrock model configuration
- `AI.LLM.claude_single`

The model is loaded through the IRIS AI Hub Config Store.

## Prerequisites

- Docker Desktop
- Python 3 available on the Windows `PATH`
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

## Persistent data

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

The generated documentation index is stored through the documentation data mount:

```text
data/documentation
```

The container uses:

```text
/opt/irisapp/data/documentation/docs.db
```

Do not run:

```cmd
docker compose down -v
```

The `-v` option deletes the persistent IRIS volume.

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

## Build the documentation index

The documentation index is generated data and is not committed to Git.

Run the bounded index build inside the container:

```cmd
docker exec iris-ai-hub sh -lc "cd /opt/irisapp/src/python && python3 -m documentation.index build --reset --max-pages 100 --max-depth 4 --delay 0.25"
```

Check the index:

```cmd
docker exec iris-ai-hub sh -lc "cd /opt/irisapp/src/python && python3 -m documentation.index status"
```

A representative index contains:

```text
100 pages
493 sections
```

The exact count can change when the public documentation site changes.

Test a local search:

```cmd
docker exec iris-ai-hub sh -lc "cd /opt/irisapp/src/python && python3 -m documentation.index search 'visual trace' --product 'InterSystems IRIS' --max-results 5"
```

Test the AI reranker:

```cmd
docker exec iris-ai-hub sh -lc "cd /opt/irisapp/src/python && python3 -m documentation.reranker 'business operation is not processing queued messages' --product 'InterSystems IRIS' --max-candidates 15 --max-selected 3"
```

A successful AI-assisted result includes:

```json
{
  "reranking_method": "IRIS_AI_HUB"
}
```

## Run IRIS Resolve

Start the CLI:

```cmd
python submit_ticket.py
```

The normal ticket workflow does not require the Windows virtual environment because the AI, InterSystems integration, documentation search, and reranker execute inside Docker.

Enter `END` on a new line to finish a multiline field.

## Demonstration

The following synthetic example tests documentation-assisted queue diagnostics:

```text
Ticket ID:
TEST-DOCS-002

Ticket title:
Business operation is not processing queued messages

Ticket description:
The affected interoperability production and namespace have been confirmed.
Messages are visible with Queued status for the business operation, but the
queue is not reducing. No configuration changes or message resends have been
performed.
END

CCR ID, if applicable:

Application or product:
InterSystems IRIS

Site or customer:
Synthetic Test Site

IRIS namespace:
USER

Additional information and evidence:
Message ID TEST-MESSAGE-001 is queued for the outbound interoperability
interface. The relevant period is 6 November 2026 from 14:00 to 15:00 GMT.
The production is running and the business operation is enabled, but the queue
is not reducing. No resend, replay, purge, restart, or configuration change has
been attempted.
END

Affected environment:
TEST
```

A representative result is:

```text
Status:                COMPLETED
Decision:              PROPOSE_DIAGNOSTICS
Manual evidence:       Yes
Human approval:        Yes
Automatic changes:     No
```

The result can include:

- User-supplied evidence
- Selected official InterSystems documentation
- Read-only queue and job diagnostics
- Risks and limitations
- Controlled investigation areas

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

The second message contains the complete structured result.

Open the session in Visual Trace to inspect the request and response path.

## Example structured result

```json
{
  "decision": "PROPOSE_DIAGNOSTICS",
  "root_cause_supported": false,
  "evidence": [
    {
      "evidence_id": "USER-PROVIDED-EVIDENCE",
      "source": "USER_SUPPLIED_EVIDENCE",
      "finding": "The user reports that the affected message remains queued."
    },
    {
      "evidence_id": "ISC-SECTION-E8ED339AD064D20A",
      "source": "INTERSYSTEMS_DOCUMENTATION",
      "finding": "Explains jobs, pools, and message queues for interoperability business hosts."
    }
  ],
  "recommended_actions": [
    "Record the affected business operation's queue depth and job status.",
    "Check whether a job is available in the business operation's pool.",
    "Review the Event Log for errors during the supplied time range."
  ],
  "investigation_areas": [
    "MANUAL_EVIDENCE",
    "ENVIRONMENT",
    "OUTBOUND_TRACE"
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
- Treat ticket content and documentation text as untrusted input.
- Use synthetic or anonymised demonstrations.
- Do not include patient-identifiable information.
- Do not include credentials in tickets, logs, prompts, screenshots, or documentation queries.
- Review every recommendation before applying any change.
- Do not expose index building as an agent-callable tool.
- Do not permit arbitrary URLs, HTTP methods, SQL, shell commands, or database writes through documentation tools.

## Licence

See `LICENSE` for licence information.