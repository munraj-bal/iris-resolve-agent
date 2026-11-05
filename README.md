# IRIS Resolve

IRIS Resolve is a read-only, AI-assisted support ticket investigation agent built with InterSystems IRIS, IRIS AI Hub, Interoperability, Model Context Protocol tools, LangChain, and Amazon Bedrock.

The application accepts manually entered support ticket information and optional technical evidence. It uses an AI agent to assess the available evidence, identify missing information, propose safe diagnostic procedures, and return a structured recommendation for human review.

IRIS Resolve does not modify support tickets, CCRs, source code, configuration, databases, interfaces, or target environments.

## Key features

- User-friendly interactive command-line interface
- Support for both CCR-related and general support tickets
- Optional CCR reference supplied as contextual information
- Multiline copy-and-paste support for ticket descriptions
- Optional manually supplied technical evidence
- IRIS AI Hub model configuration
- Amazon Bedrock model integration
- Read-only MCP tools
- Deterministic confidence calculation
- Structured decisions and recommendations
- Instruction-injection checks
- Evidence validation
- Mandatory human approval
- No automatic corrective changes

## Supported evidence

Users can paste evidence directly into the command-line interface, including:

- Error messages
- Application logs
- CCR transport evidence
- Outbound interface traces
- Find GUID output
- SQL query results
- Configuration details
- Previous investigation notes
- Relevant timestamps
- Expected and actual behaviour

Users do not need to create JSON fixture files.

## Current data-source limitations

IRIS Resolve does not currently connect directly to:

- The live CCR website
- The live iService system
- Production databases
- Customer environments
- Live interface monitoring systems

A supplied CCR ID is treated as contextual information only.

The AI must not claim that a live system was queried unless the user manually includes the relevant output as evidence.

An authorised live, read-only provider can be added later without changing the interactive CLI workflow.

## Architecture

The current workflow is:

```text
User enters ticket information
        |
        v
Optional CCR reference
        |
        v
Optional manually pasted evidence
        |
        v
IRIS Resolve CLI
        |
        v
Python ticket solver
        |
        v
IRIS AI Hub model configuration
        |
        v
Amazon Bedrock model
        |
        v
Read-only MCP policy and diagnostic tools
        |
        v
Evidence validation and confidence calculation
        |
        v
Structured recommendation for human review
```

The InterSystems Interoperability classes provide the foundation for running the resolution workflow inside an IRIS production.

## Safety model

IRIS Resolve is read-only.

The agent can:

- Analyse manually entered ticket details
- Analyse manually pasted technical evidence
- Treat an optional CCR ID as contextual information
- Separate observed facts from assumptions
- Identify conflicting evidence
- Identify missing information
- Propose approved read-only diagnostics
- Recommend human-reviewed next steps
- Return a structured investigation result

The agent does not:

- Connect to the live CCR website
- Retrieve live CCR details
- Retrieve live CCR transport logs
- Retrieve live iService ticket information
- Create or update a CCR
- Retry a CCR transport
- Change CCR item sets
- Resolve an iService ticket
- Execute database updates
- Modify source code
- Apply configuration changes
- Send outbound HL7 messages
- Change a target environment
- Perform automatic corrective actions

Every result includes:

```json
{
  "requires_human_approval": true,
  "automatic_changes_performed": false
}
```

## Decision types

IRIS Resolve can return one of the following decisions:

| Decision | Meaning |
|---|---|
| `PROPOSE_RESOLUTION` | The available evidence directly supports a likely root cause and a human-reviewed resolution. |
| `PROPOSE_DIAGNOSTICS` | A plausible cause exists, but further read-only diagnostics are required. |
| `REQUEST_INFORMATION` | Important ticket or technical information is missing. |
| `NEEDS_INVESTIGATION` | The evidence is insufficient, inconclusive, or conflicting. |
| `REJECT` | The input is invalid, malicious, or contains an instruction-injection attempt. |

The AI proposes a preliminary decision. Python then validates the evidence, calculates confidence, and selects the final decision.

## Approved diagnostic procedures

The MCP server currently exposes read-only policy and diagnostic tools.

Available diagnostic procedures include:

- `MANUAL_EVIDENCE_REVIEW`
- `ENVIRONMENT_CONFIRMATION`
- `OUTBOUND_TRACE_REVIEW`
- `FIND_GUID_REVIEW`
- `CCR_TRANSPORT_EVIDENCE_REVIEW`

These tools provide approved investigation steps. They do not access or modify external systems.

## Project structure

```text
iris-resolve-agent/
|-- src/
|   |-- python/
|   |   |-- solver.py
|   |   |-- ticket_mcp_server.py
|   |   `-- langchain_intersystems-0.0.1-py3-none-any.whl
|   `-- SupportAgent/
|       |-- Production.cls
|       |-- ResolutionOperation.cls
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

### `submit_ticket.py`

Provides the user-friendly interactive CLI.

The CLI collects:

- Ticket ID
- Ticket title
- Ticket description
- Optional CCR ID
- Optional manually pasted evidence
- Affected environment

The CLI converts the information into the internal format required by the solver. Users do not need to create JSON manually.

### `solver.py`

Provides the main AI-assisted investigation workflow.

The solver:

1. Validates the supplied ticket information.
2. Checks for required fields.
3. Checks for common instruction-injection phrases.
4. Starts the read-only MCP server.
5. Loads the configured AI model through IRIS AI Hub.
6. Sends the ticket and evidence to the AI agent.
7. Validates evidence references.
8. Validates requested diagnostic procedures.
9. Calculates confidence deterministically.
10. Returns structured result data.

### `ticket_mcp_server.py`

Provides read-only MCP tools for:

- Resolution policy
- Safety requirements
- Approved diagnostic procedures

The MCP server does not retrieve CCR records and does not modify external systems.

### `SupportAgent.TicketRequest`

Represents a support ticket request in ObjectScript.

The request supports:

- Ticket ID
- Title
- Description
- Optional CCR ID
- Optional additional evidence
- Environment

### `SupportAgent.ResolutionProcess`

Invokes the Python solver from an InterSystems Interoperability business process.

### `SupportAgent.Setup`

Creates the IRIS Wallet entry, Amazon Bedrock model configuration, and MCP server configuration.

### `SupportAgent.Production`

Defines the InterSystems Interoperability production structure.

## Prerequisites

The following are required:

- Docker Desktop
- Access to the required InterSystems Docker registry
- InterSystems IRIS Community AI image
- InterSystems `langchain_intersystems` wheel
- An Amazon Bedrock API key
- A local `.env` file containing a private IRIS password
- Python 3 for running the host-side interactive CLI

The following wheel must be placed in `src/python`:

```text
langchain_intersystems-0.0.1-py3-none-any.whl
```

The wheel is distributed through the InterSystems Early Access Program and is excluded from Git.

## Reproducible Docker setup

IRIS Resolve uses a custom Docker image based on InterSystems IRIS Community AI.

The image automatically installs:

- The InterSystems IRIS Python driver
- The InterSystems LangChain integration wheel
- LangChain
- LangChain Core
- LangChain MCP adapters
- LangChain AWS integration
- Required Python dependencies

Python dependencies are installed into:

```text
/opt/irisapp/python-packages
```

The directory is added to `PYTHONPATH` by the Docker image and Docker Compose configuration.

## Private environment configuration

Create the private environment file:

```cmd
copy .env.example .env
```

Edit it:

```cmd
notepad .env
```

Use:

```env
IRIS_PASSWORD=replace_with_your_private_local_IRIS_password
```

Replace the placeholder privately.

Do not commit `.env`.

## Build the custom image

Build the Docker image:

```cmd
docker compose build
```

Use a clean build after changing the Dockerfile, requirements, or InterSystems wheel:

```cmd
docker compose build --no-cache
```

## Start the container

Start IRIS Resolve:

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

- The IRIS database
- The `_SYSTEM` password state
- Compiled application classes
- IRIS Wallet entries
- Amazon Bedrock credentials stored in the Wallet
- AI Hub model configuration
- MCP server configuration

Normal container recreation retains this information.

Do not run:

```cmd
docker compose down -v
```

The `-v` option deletes the persistent volume and removes the saved IRIS configuration.

## Verify Python dependencies

Run:

```cmd
docker exec iris-ai-hub python3 -c "import iris,langchain,langchain_aws,langchain_intersystems; print('All Python dependencies available')"
```

Expected:

```text
All Python dependencies available
```

## Verify the IRIS connection

Run:

```cmd
docker exec iris-ai-hub python3 -c "import os,iris; c=iris.connect('localhost',1972,'USER','_SYSTEM',os.environ['IRIS_PASSWORD']); print('IRIS connection successful'); c.close()"
```

Expected:

```text
IRIS connection successful
```

If IRIS returns `Access Denied`, confirm that the `_SYSTEM` password inside IRIS matches the value in `.env`.

## Initial IRIS setup

These steps are required when creating a fresh `iris-mgr` volume.

Open the IRIS terminal:

```cmd
docker exec -it iris-ai-hub iris session IRIS -U USER
```

The prompt should show:

```text
USER>
```

Compile the request class:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/TicketRequest.cls","ck")
```

Compile the response class:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionResponse.cls","ck")
```

Compile the persisted resolution record:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionRecord.cls","ck")
```

Compile the resolution process:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionProcess.cls","ck")
```

Compile the setup class:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/Setup.cls","ck")
```

Compile the production classes:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/TicketService.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionOperation.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/Production.cls","ck")
```

## Confirm compiled classes

At the `USER>` prompt, run:

```objectscript
Write "TicketRequest: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.TicketRequest"),!
Write "ResolutionResponse: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.ResolutionResponse"),!
Write "ResolutionRecord: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.ResolutionRecord"),!
Write "ResolutionProcess: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.ResolutionProcess"),!
Write "Setup: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.Setup"),!
Write "TicketService: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.TicketService"),!
Write "ResolutionOperation: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.ResolutionOperation"),!
Write "Production: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.Production"),!
```

Each class should return:

```text
1
```

## Register the AI Hub descriptors

Register the model and MCP configuration descriptors:

```objectscript
Do ##class(%ConfigStore.DescriptorManager).RebuildRegistry()
```

Confirm the LLM descriptor:

```objectscript
Set descriptorClass = ""
Set sc = ##class(%ConfigStore.DescriptorManager).GetDescriptorClass("AI","LLM","",.descriptorClass)
Do $SYSTEM.Status.DisplayError(sc)
Write "LLM descriptor: ",descriptorClass,!
```

Expected:

```text
LLM descriptor: %AI.ConfigStore.LLMDescriptor
```

Confirm the MCP descriptor:

```objectscript
Set descriptorClass = ""
Set sc = ##class(%ConfigStore.DescriptorManager).GetDescriptorClass("AI","MCP","",.descriptorClass)
Do $SYSTEM.Status.DisplayError(sc)
Write "MCP descriptor: ",descriptorClass,!
```

Expected:

```text
MCP descriptor: %AI.ConfigStore.MCPDescriptor
```

## Initialise Amazon Bedrock and MCP

Run the setup method using a private Amazon Bedrock API key:

```objectscript
Set sc = ##class(SupportAgent.Setup).Init("YOUR_PRIVATE_BEDROCK_API_KEY")
Do $SYSTEM.Status.DisplayError(sc)
```

Do not commit, paste, log, or share the real API key.

The setup creates:

- The `SingleKeyAuth.claude` IRIS Wallet secret
- The `AI.LLM.claude_single` model configuration
- The `AI.MCP.ticket_tools` MCP configuration

Expected:

```text
IRIS Resolve Bedrock and Config Store initialised successfully!
```

Exit the IRIS terminal:

```objectscript
Halt
```

## Run the interactive CLI

Run:

```cmd
python submit_ticket.py
```

The CLI asks for:

```text
Ticket ID:
Ticket title:

Ticket description
Enter END on a new line when finished.

CCR ID, if applicable:

Additional evidence, if available
Enter END on a new line when finished.

Environment:
```

The user can review the supplied information before submitting it to IRIS Resolve.

## General ticket demonstration

Run:

```cmd
python submit_ticket.py
```

Enter:

```text
Ticket ID: DEMO-I001
Ticket title: Cancellation message was not generated
```

For the description:

```text
A cancellation was entered, but no SIU_S15 message appeared in the outbound trace. The cancellation is visible in the application and no error was shown to the user.
END
```

Leave the CCR ID blank:

```text
CCR ID, if applicable:
```

For additional evidence:

```text
The cancellation was entered at 14:10.

No SIU_S15 message appeared in the outbound trace between 14:00 and 14:30.

The expected message type was SIU_S15.
END
```

Enter:

```text
Environment, for example BASE, TEST, UAT, or LIVE: TEST
```

The agent should identify the known facts, avoid claiming a confirmed root cause, and propose a read-only outbound-trace investigation.

## CCR-related ticket demonstration

Run:

```cmd
python submit_ticket.py
```

Enter:

```text
Ticket ID: DEMO-I002
Ticket title: CCR fails to load with missing GUID references
```

For the description:

```text
CCR ENNN1110 fails while being loaded into TEST.
END
```

Enter the CCR reference:

```text
CCR ID, if applicable: ENNN1110
```

For additional evidence:

```text
ERROR #5001: GUID reference(s) missing from stream.

Missing GUIDs:

2E02AC50-BC93-11EF-AD8D-005056842598
AF885D91-630C-11F1-AC6F-005056842598
AF819C24-630C-11F1-AC6F-005056842598

The item set failed while loading into TEST.

Find GUID output requires review to determine whether the referenced records exist in BASE and whether they previously progressed to TEST.
END
```

Enter:

```text
Environment, for example BASE, TEST, UAT, or LIVE: TEST
```

The agent should recognise the supplied evidence, recommend a read-only Find GUID review, identify possible prerequisite changes, and avoid proposing an automatic GUID update.

## Expected output

A successful result should include:

```text
Status:              COMPLETED
Human approval:      Yes
Automatic changes:   No
```

When optional evidence was supplied, the result should include:

```text
Manual evidence:     Yes
```

The structured result contains:

```json
{
  "user_evidence_supplied": true,
  "requires_human_approval": true,
  "automatic_changes_performed": false,
  "status": "COMPLETED"
}
```

## Test Python syntax

Run:

```cmd
python -m py_compile src\python\solver.py
python -m py_compile src\python\ticket_mcp_server.py
python -m py_compile submit_ticket.py
```

Successful syntax checks return no output.

## Rebuilding after dependency changes

After changing `Dockerfile`, `requirements.txt`, or the InterSystems wheel, rebuild the image:

```cmd
docker compose build --no-cache
```

Recreate the container without deleting the persistent volume:

```cmd
docker compose up -d --force-recreate
```

Check its status:

```cmd
docker compose ps
```

Do not use:

```cmd
docker compose down -v
```

## Development roadmap

### Current capabilities

- Interactive ticket input
- General and CCR-related ticket support
- Optional manually pasted evidence
- IRIS AI Hub model configuration
- Amazon Bedrock model integration
- Read-only MCP tools
- Deterministic evidence validation
- Deterministic confidence scoring
- Human-reviewed recommendations
- No automatic changes

### Planned improvements

- Automated tests for general tickets
- Automated tests for CCR-related tickets
- Read-only outbound-trace tools
- Read-only Find GUID tools
- Reusable and idempotent setup
- Improved Interoperability production integration
- Authorised live CCR provider
- Authorised live ticket provider
- Structured audit history
- Token and model-cost reporting

## Security considerations

- Never commit `.env`.
- Never commit an Amazon Bedrock API key.
- Never paste a real API key into documentation, tickets, logs, or screenshots.
- Store model credentials in the IRIS Wallet.
- Rotate any credential that has been exposed.
- Treat manually supplied ticket content as untrusted input.
- Review every recommendation before applying a change.
- Do not use customer-identifiable or patient-identifiable information in public demonstrations.
- Use synthetic or anonymised examples for public demonstrations.

## Licence

See `LICENSE` for licence information.