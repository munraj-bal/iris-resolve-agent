# IRIS Resolve

IRIS Resolve is an evidence-grounded support ticket resolution agent built with InterSystems IRIS AI Hub, IRIS Interoperability, AWS Bedrock, MCP tools, and read-only CCR evidence providers.

The user supplies an iService-style ticket title and description, plus an optional CCR identifier. The completed agent will decide which read-only CCR tools to call, inspect the returned evidence, propose a resolution or diagnostic steps, calculate a deterministic confidence score, and store an auditable result in IRIS.

> Current status: The ticket data models and synthetic read-only CCR provider are implemented and tested. The MCP tools, AI solver, IRIS Interoperability production, persistence operation, and CLI submission flow are being implemented.

## Contents

- [Current functionality](#current-functionality)
- [Planned workflow](#planned-workflow)
- [Decision outcomes](#decision-outcomes)
- [Confidence scoring](#confidence-scoring)
- [CCR provider modes](#ccr-provider-modes)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Testing the ticket models](#testing-the-ticket-models)
- [Testing the CCR provider](#testing-the-ccr-provider)
- [Security](#security)
- [Development status](#development-status)
- [License](#license)

## Current functionality

The following components are implemented:

- IRIS ticket request model
- IRIS resolution response model
- Persistent IRIS resolution record
- Conversion of ticket requests into JSON
- Synthetic read-only CCR provider
- CCR identifier validation
- Normalised CCR details
- Normalised CCR transport-log evidence
- Protection against path-traversal attempts
- Controlled handling of unknown CCR identifiers
- Disabled live CCR provider that fails safely
- Docker mounting of synthetic CCR fixtures as read-only data
- Environment-based CCR provider selection

The following components are being implemented:

- MCP tools that expose the CCR provider to the AI agent
- `solver.py` AI Hub orchestration
- Deterministic confidence calculation
- IRIS Business Service
- IRIS Business Process
- IRIS Business Operation
- IRIS Interoperability production
- CLI ticket submission
- End-to-end IRIS Message Trace demonstration

## Planned workflow

The completed application will follow this flow:

```text
User enters ticket title and description
                |
                v
SupportAgent.TicketService
                |
                v
SupportAgent.TicketRequest
                |
                v
SupportAgent.ResolutionProcess
                |
                v
IRIS AI Hub model configuration
                |
                v
AWS Bedrock Claude model
                |
                v
Agent selects read-only MCP tools
                |
                +--> get_ccr_details()
                |
                +--> get_ccr_transport_logs()
                |
                +--> get_resolution_policy()
                |
                v
Evidence validation and confidence calculation
                |
                v
SupportAgent.ResolutionOperation
                |
                v
SupportAgent.ResolutionRecord
```

The user will provide:

- Ticket ID, optional
- Ticket title, required
- Ticket description, required
- CCR ID, optional
- Affected environment, optional

The agent will then:

1. Inspect the supplied ticket information.
2. Determine whether a CCR is relevant.
3. Decide whether CCR details are needed.
4. Decide whether CCR transport logs are needed.
5. Call the appropriate read-only MCP tools.
6. Evaluate the returned evidence.
7. Select a supported outcome.
8. Generate recommended actions.
9. Identify missing information and risks.
10. Calculate an evidence-based confidence score.
11. Store the result in IRIS.
12. Require human approval before any operational action.

## Decision outcomes

The completed solver will support these outcomes:

| Decision | Meaning |
|---|---|
| `PROPOSE_RESOLUTION` | Available evidence strongly supports a likely resolution |
| `PROPOSE_DIAGNOSTICS` | A cause is plausible, but diagnostic checks are still required |
| `REQUEST_INFORMATION` | Required ticket or technical evidence is missing |
| `NEEDS_INVESTIGATION` | Evidence is insufficient, conflicting, or inconclusive |
| `REJECT` | The input is invalid or contains an instruction-injection attempt |

A proposed resolution remains advisory and requires human review.

IRIS Resolve will not automatically:

- Change a CCR
- Create a CCR
- Transport a CCR
- Start a change session
- Upload a bundle
- Retry a transport
- Modify a target environment
- Change production source code
- Resolve an iService ticket

## Confidence scoring

The final confidence percentage will be calculated by Python from validated evidence. The model will not choose the final percentage by itself.

Planned confidence factors include:

| Factor | Maximum contribution |
|---|---:|
| Ticket title present | `0.05` |
| Ticket description present | `0.10` |
| CCR reference present | `0.05` |
| CCR details retrieved | `0.15` |
| Transport-log evidence found | `0.25` |
| Root cause supported by evidence | `0.20` |
| Diagnostic checks available | `0.10` |
| No conflicting evidence | `0.10` |

Planned thresholds:

| Confidence | Result |
|---|---|
| `0.85` to `1.00` | `PROPOSE_RESOLUTION` |
| `0.65` to `0.84` | `PROPOSE_DIAGNOSTICS` |
| `0.40` to `0.64` | `REQUEST_INFORMATION` |
| Below `0.40` | `NEEDS_INVESTIGATION` |

## CCR provider modes

IRIS Resolve uses a provider abstraction with two modes.

### Synthetic provider

```env
CCR_PROVIDER=synthetic
```

This is the default public demonstration mode.

The provider reads synthetic CCR data from:

```text
test_data/ccr/
```

This mode:

- Performs no network calls
- Uses no internal credentials
- Does not contact a real CCR system
- Cannot create or update a CCR
- Is reproducible for competition reviewers
- Provides stable evidence for testing

### Live API provider

```env
CCR_PROVIDER=api
```

The live provider is disabled.

The provider raises a controlled configuration error until the CCR service owner supplies:

- An approved base URL
- Approved read-only endpoints
- An authentication method
- A read-only API scope
- Required request headers
- A documented response schema
- Rate limits
- Permission for competition or open-source use

No live CCR URL or credential is included in this repository.

## Project structure

```text
iris-resolve-agent/
├── src/
│   ├── SupportAgent/
│   │   ├── Production.cls
│   │   ├── ResolutionOperation.cls
│   │   ├── ResolutionProcess.cls
│   │   ├── ResolutionRecord.cls
│   │   ├── ResolutionResponse.cls
│   │   ├── Setup.cls
│   │   ├── TicketRequest.cls
│   │   └── TicketService.cls
│   │
│   └── python/
│       ├── ccr_provider.py
│       ├── solver.py
│       ├── ticket_mcp_server.py
│       └── langchain_intersystems-0.0.1-py3-none-any.whl
│
├── test_data/
│   ├── ccr/
│   │   ├── SYNTH-CCR-1001-details.json
│   │   └── SYNTH-CCR-1001-transport.json
│   └── tickets/
│
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── LICENSE
├── README.md
└── submit_ticket.py
```

Some files shown above are placeholders or are still being implemented.

The following local content is excluded from Git:

```text
.env
Wheel packages
Python cache directories
Compiled Python cache files
Local logs
Temporary files
```

## Prerequisites

The current development environment requires:

- Docker Desktop using Linux containers
- Git
- Python for local syntax checks
- InterSystems IRIS Community with AI Hub
- Access to the InterSystems AI Hub Early Access Program
- The `langchain_intersystems` wheel
- An AWS Bedrock API key for the AI solver stage
- Access to the configured AWS Bedrock model

This project was developed using:

```text
iris-community-2027.1.0AI.109.0-docker.tar.gz
```

> Confirm that the selected AI Hub EAP build is accepted by the competition organisers before final submission.

## Installation

### 1. Clone the repository

```cmd
git clone https://github.com/munraj-bal/iris-resolve-agent.git
cd iris-resolve-agent
```

### 2. Download the IRIS AI Hub image

Download the x64 IRIS Community AI Hub Docker image from the InterSystems AI Hub Early Access portal.

The current development image is:

```text
iris-community-2027.1.0AI.109.0-docker.tar.gz
```

Store the image archive outside the Git repository.

Example:

```text
C:\Users\your-user\Documents\iris_images\
```

Load the image:

```cmd
docker image load -i "C:\Users\your-user\Documents\iris_images\iris-community-2027.1.0AI.109.0-docker.tar.gz"
```

Expected output includes:

```text
Loaded image: docker.iscinternal.com/docker-intersystems/intersystems/iris-community:2027.1.0AI.109.0
```

Confirm the image exists:

```cmd
docker images
```

### 3. Download the InterSystems LangChain wheel

Download:

```text
langchain_intersystems-0.0.1-py3-none-any.whl
```

from the InterSystems AI Hub Early Access portal.

Place the wheel in:

```text
src\python\langchain_intersystems-0.0.1-py3-none-any.whl
```

The wheel is excluded from Git because it is distributed through the InterSystems Early Access Program.

### 4. Create the private environment file

Copy the example:

```cmd
copy .env.example .env
```

Edit `.env`:

```cmd
notepad .env
```

Use:

```env
IRIS_PASSWORD=replace_with_your_private_local_IRIS_password
CCR_PROVIDER=synthetic
```

Replace the password placeholder privately.

Do not commit `.env`.

The committed `.env.example` contains placeholders only:

```env
IRIS_PASSWORD=replace_with_your_local_IRIS_password
CCR_PROVIDER=synthetic
```

### 5. Review Docker Compose

The current `docker-compose.yml` is:

```yaml
name: iris-resolve-agent

services:
  iris:
    image: docker.iscinternal.com/docker-intersystems/intersystems/iris-community:2027.1.0AI.109.0
    pull_policy: never
    container_name: iris-ai-hub
    environment:
      IRIS_PASSWORD: "${IRIS_PASSWORD}"
      CCR_PROVIDER: "${CCR_PROVIDER:-synthetic}"
    ports:
      - "9091:1972"
      - "9092:52773"
    volumes:
      - ./src:/opt/irisapp/src
      - ./test_data:/opt/irisapp/test_data:ro
```

### 6. Start the container

```cmd
docker compose up -d
docker compose ps
```

Wait until the status shows:

```text
healthy
```

Confirm the environment variables without printing the password:

```cmd
docker exec iris-ai-hub python3 -c "import os; print('IRIS password set:', bool(os.getenv('IRIS_PASSWORD'))); print('CCR provider:', os.getenv('CCR_PROVIDER'))"
```

Expected:

```text
IRIS password set: True
CCR provider: synthetic
```

### 7. Set the local IRIS password

Open:

```text
http://localhost:9092/csp/sys/UtilHome.csp
```

For a new container, sign in with:

```text
Username: _SYSTEM
Password: SYS
```

Change the `_SYSTEM` password to the exact value stored in `.env`.

## Testing the ticket models

Open the IRIS terminal:

```cmd
docker exec -it iris-ai-hub iris session iris
```

The prompt should show:

```text
USER>
```

If required:

```objectscript
ZN "USER"
```

Compile the request model:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/TicketRequest.cls","ck")
```

Compile
Compile the resolution process:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionProcess.cls","ck")
```

Compile the setup class:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/Setup.cls","ck")
```

Confirm the classes exist:

```objectscript
Write ##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.TicketRequest"),!
Write ##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.ResolutionResponse"),!
Write ##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.ResolutionRecord"),!
Write ##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.ResolutionProcess"),!
Write ##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.Setup"),!
```

Expected:

```text
1
1
1
1
1
```

### Test request JSON conversion

```objectscript
Set request = ##class(SupportAgent.TicketRequest).%New()
Set request.TicketID = "SYNTH-I615950"
Set request.Title = "Cancellation message was not generated"
Set request.Description = "After cancellation, no SIU_S15 message appeared in the outbound trace."
Set request.CCRID = "SYNTH-CCR-1001"
Set request.Environment = "TEST"
Write request.ToJSON(),!
```

Expected:

```json
{"ticket_id":"SYNTH-I615950","title":"Cancellation message was not generated","description":"After cancellation, no SIU_S15 message appeared in the outbound trace.","ccr_id":"SYNTH-CCR-1001","environment":"TEST"}
```

Remove the temporary object:

```objectscript
Kill request
```

This test does not save or send anything.

## Testing the CCR provider

Leave the IRIS terminal:

```objectscript
Halt
```

### Check Python syntax

```cmd
python -m py_compile src\python\ccr_provider.py
```

No output means the syntax is valid.

### Confirm fixtures are mounted

```cmd
docker exec iris-ai-hub ls -la /opt/irisapp/test_data/ccr
```

Expected:

```text
SYNTH-CCR-1001-details.json
SYNTH-CCR-1001-transport.json
```

### Retrieve synthetic CCR details

```cmd
docker exec iris-ai-hub python3 -c "import sys,asyncio,json; sys.path.insert(0,'/opt/irisapp/src/python'); from ccr_provider import get_ccr_provider; provider=get_ccr_provider(); result=asyncio.run(provider.get_details('SYNTH-CCR-1001')); print('Provider:',provider.provider_name); print(json.dumps(result,indent=2))"
```

Expected:

```text
Provider: synthetic
```

The result includes:

```text
CCR ID: SYNTH-CCR-1001
Status: Executed
Environment: TEST
ITEM-001: Completed
ITEM-002: Pending
```

### Retrieve synthetic transport logs

```cmd
docker exec iris-ai-hub python3 -c "import sys,asyncio,json; sys.path.insert(0,'/opt/irisapp/src/python'); from ccr_provider import get_ccr_provider; provider=get_ccr_provider(); result=asyncio.run(provider.get_transport_logs('SYNTH-CCR-1001')); print(json.dumps(result,indent=2))"
```

Expected evidence identifiers:

```text
SYNTH-CCR-1001-LOG-001
SYNTH-CCR-1001-LOG-002
```

### Test an unknown CCR

```cmd
docker exec iris-ai-hub python3 -c "import sys,asyncio; sys.path.insert(0,'/opt/irisapp/src/python'); from ccr_provider import get_ccr_provider; provider=get_ccr_provider(); asyncio.run(provider.get_details('SYNTH-CCR-9999'))"
```

Expected:

```text
CCRNotFoundError
```

### Test invalid identifier protection

```cmd
docker exec iris-ai-hub python3 -c "import sys; sys.path.insert(0,'/opt/irisapp/src/python'); from ccr_provider import validate_ccr_id; validate_ccr_id('../../etc/passwd')"
```

Expected:

```text
ValueError
```

### Confirm live access is disabled

```cmd
docker exec iris-ai-hub python3 -c "import sys,asyncio; sys.path.insert(0,'/opt/irisapp/src/python'); from ccr_provider import get_ccr_provider; provider=get_ccr_provider('api'); asyncio.run(provider.get_details('SCFI5105'))"
```

Expected:

```text
CCRConfigurationError
```

## Security

- Never commit `.env`.
- Never commit an AWS Bedrock API key.
- Never hard-code the IRIS `_SYSTEM` password.
- Never print secret values during environment checks.
- Never publish internal CCR URLs.
- Never publish CCR credentials.
- Never include real iService ticket data.
- Never include customer or patient information.
- Keep CCR MCP tools read-only.
- Require human review for all proposed resolutions.
- Rotate exposed credentials.

## Development status

### Completed

- [x] Rename project to IRIS Resolve
- [x] Define ticket request model
- [x] Define resolution response model
- [x] Define persistent resolution record
- [x] Convert ticket request to JSON
- [x] Implement synthetic read-only CCR provider
- [x] Validate CCR identifiers
- [x] Normalise CCR details
- [x] Normalise CCR transport logs
- [x] Reject unknown CCR fixtures
- [x] Reject unsafe CCR identifiers
- [x] Disable unapproved live CCR access
- [x] Mount synthetic CCR fixtures as read-only
- [x] Refactor the process and setup namespaces

### In progress

- [ ] Implement read-only CCR MCP tools
- [ ] Implement resolution policy MCP tool
- [ ] Implement diagnostic-check MCP tool
- [ ] Implement `solver.py`
- [ ] Connect `solver.py` to IRIS AI Hub
- [ ] Implement deterministic confidence scoring
- [ ] Implement `ResolutionOperation.cls`
- [ ] Implement `TicketService.cls`
- [ ] Implement `Production.cls`
- [ ] Implement `submit_ticket.py`
- [ ] Add synthetic ticket fixtures
- [ ] Demonstrate the workflow in IRIS Message Trace
- [ ] Add automated tests
- [ ] Add a reproducible container build
- [ ] Record a demonstration video

## Competition qualification target

The finished application is intended to demonstrate:

- InterSystems IRIS AI Hub model configuration
- An AI agent performing a decision-making task
- Autonomous MCP tool selection
- Read-only CCR evidence retrieval
- Deterministic confidence scoring
- An IRIS Interoperability Business Service
- An IRIS Interoperability Business Process
- An IRIS Interoperability Business Operation
- Persistent evidence and decisions in IRIS
- End-to-end IRIS Message Trace
- Synthetic data for reproducible judging
- Human approval before operational action

The project is not competition-complete until the Interoperability production and Message Trace work end to end.

## License

This project is licensed under the MIT License. See `LICENSE`.