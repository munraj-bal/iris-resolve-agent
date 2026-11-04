# IRIS Resolve

IRIS Resolve is an evidence-grounded support ticket resolution agent built with InterSystems IRIS AI Hub, AWS Bedrock, MCP tools, and read-only CCR evidence providers.

The user supplies an iService-style ticket title and description, plus an optional CCR identifier. The planned IRIS AI Hub agent will decide which read-only CCR tools to call, examine the returned evidence, propose a resolution or diagnostic steps, calculate a deterministic confidence score, and store an auditable result in IRIS.

> **Current status:** The ticket data models and synthetic read-only CCR provider are implemented and tested. The MCP tools, AI solver, IRIS Interoperability production, persistence operation, and CLI submission flow are still being implemented.

## Contents

- [Current functionality](#current-functionality)
- [Planned workflow](#planned-workflow)
- [Decision outcomes](#decision-outcomes)
- [Project structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Testing the ticket models](#testing-the-ticket-models)
- [Testing the CCR provider](#testing-the-ccr-provider)
- [Security](#security)
- [Development status](#development-status)
- [License](#license)

## Current functionality

The following components are currently implemented:

- IRIS ticket request, resolution response, and persistent resolution data models
- Synthetic, read-only CCR provider
- CCR identifier validation
- Normalised CCR details
- Normalised CCR transport-log evidence
- Protection against path-traversal identifiers
- Controlled handling of unknown CCR identifiers
- Disabled live CCR provider that fails safely
- Docker mounting of synthetic CCR fixtures as read-only data
- Environment-based provider selection

The following components are currently being implemented:

- MCP tools that expose the CCR provider to the agent
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

- ticket ID, optional
- ticket title, required
- ticket description, required
- CCR ID, optional
- affected environment, optional

The agent will then autonomously:

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

A proposed resolution will remain advisory and will require human review.

IRIS Resolve will not automatically:

- change a CCR
- transport a CCR
- create a change session
- upload a bundle
- retry a transport
- modify a target environment
- make a production code change
- resolve an iService ticket

## Confidence scoring

The final confidence percentage will be calculated by Python from validated evidence. The model will not be trusted to choose its own final percentage.

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

A confidence score is not produced solely from model opinion. It must be supported by observable ticket and CCR evidence.

## CCR provider modes

IRIS Resolve supports a provider abstraction with two modes.

### Synthetic provider

```env
CCR_PROVIDER=synthetic
```

This is the default public demonstration mode.

It reads synthetic CCR data from:

```text
test_data/ccr/
```

This mode:

- performs no network calls
- uses no internal credentials
- does not connect to a real CCR system
- cannot create or update a CCR
- is reproducible for competition reviewers
- provides stable evidence for testing

### Live API provider

```env
CCR_PROVIDER=api
```

The live provider is currently disabled.

It deliberately raises a configuration error until the following are supplied by the CCR service owner:

- approved base URL
- read-only endpoints
- authentication method
- required API scope
- request headers
- response schema
- rate limits
- permission for competition or open-source use

No live CCR endpoint or credential is included in this repository.

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

The following files are deliberately excluded from Git:

```text
.env
*.whl
__pycache__/
*.pyc
```

Each *ser must obtain the InterSystems E*P wheel independently.

## Prerequ*sites

The current development env*ronment requires:

- Docker Deskto* using Linux containers
- Git
- Py*hon 3.12 or a compatible Python ve*sion for local syntax checks
- Int*rSystems IRIS Community with AI Hu*
- Access to the InterSystems AI H*b Early Access Program
- The `lang*hain_intersystems` wheel
- An AWS *edrock API key for the later AI so*ver stage
- Access to the configur*d AWS Bedrock model

This project *as developed against:

```text
iri*-community-2027.1.0AI.109.0-docker*tar.gz
```

> Confirm that the sel*cted AI Hub EAP build is accepted *y the competition organisers befor* final submission.

## Installatio*

### 1. Clone the repository

```*md
git clone https://github.com/munraj-bal/iris-resolve-agent.git
cd *ris-resolve-agent
```

### 2. Down*oad the IRIS AI Hub image

Downloa* the x64 IRIS Community AI Hub Doc*er image from the InterSystems AI *ub Early Access portal.

The curre*t development image is:

```text
i*is-community-2027.1.0AI.109.0-dock*r.tar.gz
```

Store the image arch*ve outside the Git repository.

Ex*mple location:

```text
C:\Users\y*ur-user\Documents\iris_images\
```*
Load the image:

```cmd
docker im*ge load -i "C:\Users\your-user\Doc*ments\iris_images\iris-community-2*27.1.0AI.109.0-docker.tar.gz"
```
*Expected output includes:

```text*Loaded image: docker.iscinternal.c*m/docker-intersystems/intersystems*iris-community:2027.1.0AI.109.0
``*

Confirm the image exists:

```cm*
docker images
```

### 3. Downloa* the InterSystems LangChain wheel
*Download:

```text
langchain_inter*ystems-0.0.1-py3-none-any.whl
```
*from the InterSystems AI Hub Early*Access portal.

Place it in:

```t*xt
src\python\langchain_intersyste*s-0.0.1-py3-none-any.whl
```

> Th* wheel is excluded from Git becaus* it is distributed through the Int*rSystems Early Access Program.

##* 4. Create the private environment*file

Copy the example:

```cmd
co*y .env.example .env
```

Edit `.en*`:

```cmd
notepad .env
```

Use:
*```env
IRIS_PASSWORD=replace_with_*our_private_local_IRIS_password
CC*_PROVIDER=synthetic
```

Replace t*e password placeholder privately.
*Do not commit `.env`.

The committ*d `.env.example` must contain plac*holders only:

```env
IRIS_PASSWOR*=replace_with_your_local_IRIS_pass*ord
CCR_PROVIDER=synthetic
```

##* 5. Review Docker Compose

The cur*ent `docker-compose.yml` is:

```y*ml
name: iris-resolve-agent

servi*es:
  iris:
    image: docker.isci*ternal.com/docker-intersystems/int*rsystems/iris-community:2027.1.0AI*109.0
    pull_policy: never
    c*ntainer_name: iris-ai-hub
    envi*onment:
      IRIS_PASSWORD: "${IR*S_PASSWORD}"
      CCR_PROVIDER: "*{CCR_PROVIDER:-synthetic}"
    por*s:
      - "9091:1972"
      - "90*2:52773"
    volumes:
      - ./sr*:/opt/irisapp/src
      - ./test_d*ta:/opt/irisapp/test_data:ro
```

*he mounts provide:

| Host directo*y | Container directory | Access |*|---|---|---|
| `src` | `/opt/iris*pp/src` | Read/write development m*unt |
| `test_data` | `/opt/irisap*/test_data` | Read-only fixture mo*nt |

### 6. Start the container

*``cmd
docker compose up -d
docker *ompose ps
```

Wait until the stat*s shows:

```text
healthy
```

Con*irm the required environment varia*les without displaying the passwor*:

```cmd
docker exec iris-ai-hub *ython3 -c "import os; print('IRIS *assword set:', bool(os.getenv('IRI*_PASSWORD'))); print('CCR provider*', os.getenv('CCR_PROVIDER'))"
```*
Expected:

```text
IRIS password *et: True
CCR provider: synthetic
`*`

### 7. Set the local IRIS passw*rd

Open:

```text
http://localhos*:9092/csp/sys/UtilHome.csp
```

Fo* a new container, sign in with:

`*`text
Username: _SYSTEM
Password: *YS
```

When prompted, change the *_SYSTEM` password to the exact val*e stored in `.env`.

The environme*t variable does not automatically *hange the IRIS account password. T*e values must be kept identical ma*ually.

## Testing the ticket mode*s

Open the IRIS terminal:

```cmd*docker exec -it iris-ai-hub iris s*ssion iris
```

The prompt should *how:

```text
USER>
```

If requir*d:

```objectscript
ZN "USER"
```
*### Compile the request model

```*bjectscript
Do $SYSTEM.OBJ.Load("/*pt/irisapp/src/SupportAgent/Ticket*equest.cls","ck")
```

### Compile*the response model

```objectscrip*
Do $SYSTEM.OBJ.Load("/opt/irisapp*src/SupportAgent/ResolutionRespons*.cls","ck")
```

### Compile the p*rsistent record

```objectscript
D* $SYSTEM.OBJ.Load("/opt/irisapp/sr*/SupportAgent/ResolutionRecord.cls*,"ck")
```

All three commands sho*ld finish with:

```text
Load fini*hed successfully.
```

Confirm tha* the classes exist:

```objectscri*t
Write ##class(%Dictionary.ClassD*finition).%ExistsId("SupportAgent.*icketRequest"),!
Write ##class(%Di*tionary.ClassDefinition).%ExistsId*"SupportAgent.ResolutionResponse")*!
Write ##class(%Dictionary.ClassD*finition).%ExistsId("SupportAgent.*esolutionRecord"),!
```

Expected:*
```text
1
1
1
```

### Test the r*quest JSON conversion

```objectsc*ipt
Set request = ##class(SupportA*ent.TicketRequest).%New()
Set requ*st.TicketID = "SYNTH-I615950"
Set *equest.Title = "Cancellation messa*e was not generated"
Set request.D*scription = "After cancellation, n* SIU_S15 message appeared in the o*tbound trace."
Set request.CCRID =*"SYNTH-CCR-1001"
Set request.Envir*nment = "TEST"
Write request.ToJSO*(),!
```

Expected:

```json
{"tic*et_id":"SYNTH-I615950","title":"Ca*cellation message was not generate*","description":"After cancellatio*, no SIU_S15 message appeared in t*e outbound trace.","ccr_id":"SYNTH*CCR-1001","environment":"TEST"}
``*

Remove the temporary object:

``*objectscript
Kill request
```

Thi* test does not:

- save a ticket
-*call AI Hub
- call MCP tools
- con*ect to CCR
- modify a CCR
- invoke*a production

It only creates a te*porary in-memory request and conve*ts it to JSON.

## Testing the CCR*provider

Leave the IRIS terminal *f necessary:

```objectscript
Halt*```

### 1. Check Python syntax

`*cted:

```text
SYNTH-CCR-1001-details.json
SYNTH-CCR-1001-transport.json
```

### 3. Retrieve synthetic CCR details

```cmd
docker exec iris-ai-hub python3 -c "import sys,asyncio,json; sys.path.insert(0,'/opt/irisapp/src/python'); from ccr_provider import get_ccr_provider; provider=get_ccr_provider(); result=asyncio.run(provider.get_details('SYNTH-CCR-1001')); print('Provider:',provider.provider_name); print(json.dumps(result,indent=2))"
```

Expected output begins with:

```text
Provider: synthetic
```

The returned data includes:

```text
CCR ID: SYNTH-CCR-1001
Status: Executed
Environment: TEST
ITEM-001: Completed
ITEM-002: Pending
```

### 4. Retrieve synthetic transport logs

```cmd
docker exec iris-ai-hub python3 -c "import sys,asyncio,json; sys.path.insert(0,'/opt/irisapp/src/python'); from ccr_provider import get_ccr_provider; provider=get_ccr_provider(); result=asyncio.run(provider.get_transport_logs('SYNTH-CCR-1001')); print(json.dumps(result,indent=2))"
```

Expected evidence identifiers:

```text
SYNTH-CCR-1001-LOG-001
SYNTH-CCR-1001-LOG-002
```

### 5. Test an unknown CCR

```cmd
docker exec iris-ai-hub python3 -c "import sys,asyncio; sys.path.insert(0,'/opt/irisapp/src/python'); from ccr_provider import get_ccr_provider; provider=get_ccr_provider(); asyncio.run(provider.get_details('SYNTH-CCR-9999'))"
```

Expected:

```text
CCRNotFoundError
```

This proves that the provider does not invent information for an unknown CCR.

### 6. Test invalid identifier protection

```cmd
docker exec iris-ai-hub python3 -c "import sys; sys.path.insert(0,'/opt/irisapp/src/python'); from ccr_provider import validate_ccr_id; validate_ccr_id('../../etc/passwd')"
```

Expected:

```text
ValueError
```

This proves that unsafe path identifiers are rejected.

### 7. Confirm live access is disabled

```cmd
docker exec iris-ai-hub python3 -c "import sys,asyncio; sys.path.insert(0,'/opt/irisapp/src/python'); from ccr_provider import get_ccr_provider; provider=get_ccr_provider('api'); asyncio.run(provider.get_details('SCFI5105'))"
```

Expected:

```text
CCRConfigurationError
```

This proves that the current repository cannot accidentally contact or modify a real CCR system.

## Synthetic CCR fixtures

The public demonstration uses:

```text
test_data/ccr/SYNTH-CCR-1001-details.json
test_data/ccr/SYNTH-CCR-1001-transport.json
```

These files are:

- synthetic
- non-confidential
- mounted read-only
- independent of internal systems
- safe for competition reviewers

They are not real CCR records.

## Security

- Never commit `.env`.
- Never commit an AWS Bedrock API key.
- Never hard-code the IRIS `_SYSTEM` password.
- Never commit the InterSystems EAP wheel.
- Never publish internal CCR URLs.
- Never publish CCR credentials.
- Never include real iService ticket data.
- Never include customer, patient, NHS, or production information.
- Keep CCR MCP tools read-only.
- Require human approval for any proposed resolution.
- Rotate credentials exposed in source code, screenshots, terminals, or chat messages.

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

### In progress

- [ ] Implement read-only CCR MCP tools
- [ ] Implement resolution policy MCP tool
- [ ] Implement diagnostic-check MCP tool
- [ ] Implement `solver.py`
- [ ] Connect `solver.py` to IRIS AI Hub
- [ ] Implement deterministic confidence scoring
- [ ] Implement `ResolutionProcess.cls`
- [ ] Implement `ResolutionOperation.cls`
- [ ] Implement `TicketService.cls`
- [ ] Implement `Production.cls`
- [ ] Implement `submit_ticket.py`
- [ ] Add synthetic ticket fixtures
- [ ] Demonstrate the end-to-end workflow in IRIS Message Trace
- [ ] Document AWS Bedrock setup
- [ ] Add automated tests
- [ ] Add a reproducible container build
- [ ] Record a demonstration video

## Competition qualification target

The final application is intended to demonstrate:

- InterSystems IRIS AI Hub model configuration
- an AI agent performing a decision-making task
- autonomous MCP tool selection
- read-only CCR evidence retrieval
- deterministic confidence scoring
- IRIS Interoperability Business Service
- IRIS Interoperability Business Process
- IRIS Interoperability Business Operation
- persistent evidence and decisions in IRIS
- end-to-end IRIS Message Trace
- synthetic data for reproducible judging
- human approval before operational action

The project should not be treated as competition-complete until the Interoperability production and Message Trace are working.

## License

This project is licensed under the MIT License. See LICENSE.