## Reproducible Docker setup

IRIS Resolve uses a custom Docker image based on InterSystems IRIS Community AI.

The image automatically installs:

- The InterSystems IRIS Python driver
- The InterSystems LangChain integration wheel
- LangChain and its required dependencies
- LangChain MCP adapters
- The LangChain AWS integration required for Amazon Bedrock

Python dependencies are installed into:

```text
/opt/irisapp/python-packages
```

The directory is added to `PYTHONPATH` by the Docker image and Docker Compose configuration.

### Prerequisites

The following are required:

- Docker Desktop
- Access to the InterSystems internal Docker registry
- The InterSystems `langchain_intersystems` wheel
- An Amazon Bedrock API key
- A local `.env` file containing the private IRIS password
- Synthetic ticket and CCR fixture data for local testing

The following wheel must be placed in `src/python`:

```text
langchain_intersystems-0.0.1-py3-none-any.whl
```

The wheel is distributed through the InterSystems Early Access Program and is excluded from Git.

### Private environment configuration

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
CCR_PROVIDER=synthetic
```

Replace the password placeholder privately.

Do not commit `.env`.

### Build the custom image

Build the Docker image:

```cmd
docker compose build
```

Use a clean build when testing Dockerfile changes:

```cmd
docker compose build --no-cache
```

### Start the container

Start IRIS Resolve:

```cmd
docker compose up -d
```

Check its status:

```cmd
docker compose ps
```

Wait for `iris-ai-hub` to report `healthy`.

### Persistent IRIS data

Docker Compose uses the named volume:

```text
iris-mgr
```

This preserves:

- The IRIS database
- The `_SYSTEM` password state
- Compiled application classes
- IRIS Wallet entries
- Amazon Bedrock credentials stored in the Wallet
- AI Hub model configuration
- MCP server configuration

A normal container recreation retains this information.

Do not use:

```cmd
docker compose down -v
```

The `-v` option deletes the persistent volume and removes the saved IRIS configuration.

### Verify the Python dependencies

Run:

```cmd
docker exec iris-ai-hub python3 -c "import iris,langchain,langchain_aws,langchain_intersystems; print('All Python dependencies available')"
```

Expected:

```text
All Python dependencies available
```

### Verify the IRIS connection

Run:

```cmd
docker exec iris-ai-hub python3 -c "import os,iris; c=iris.connect('localhost',1972,'USER','_SYSTEM',os.environ['IRIS_PASSWORD']); print('IRIS connection successful'); c.close()"
```

Expected:

```text
IRIS connection successful
```

If IRIS returns `Access Denied`, confirm that the `_SYSTEM` password in IRIS matches the value in `.env`.

### Initial IRIS setup

The following steps are required once when creating a fresh `iris-mgr` volume.

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

Compile the production classes when required:

```objectscript
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/TicketService.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/ResolutionOperation.cls","ck")
Do $SYSTEM.OBJ.Load("/opt/irisapp/src/SupportAgent/Production.cls","ck")
```

### Register the AI Hub descriptors

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

### Initialise Amazon Bedrock and MCP

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

### Confirm the compiled classes

At the `USER>` prompt, the following commands should each return `1`:

```objectscript
Write "TicketRequest: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.TicketRequest"),!
Write "ResolutionResponse: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.ResolutionResponse"),!
Write "ResolutionRecord: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.ResolutionRecord"),!
Write "ResolutionProcess: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.ResolutionProcess"),!
Write "Setup: ",##class(%Dictionary.ClassDefinition).%ExistsId("SupportAgent.Setup"),!
```

### Test the solver

Run the synthetic end-to-end test:

```cmd
docker exec iris-ai-hub python3 -c "import json,solver; payload=json.dumps({'ticket_id':'SYNTH-I615950','title':'Cancellation message was not generated','description':'After cancellation, no SIU_S15 message appeared in the outbound trace. Check whether the associated CCR was fully transported.','ccr_id':'SYNTH-CCR-1001','environment':'TEST'}); result=solver.process_ticket(payload); print(json.dumps(json.loads(result),indent=2))"
```

A successful result should contain:

```json
{
  "ccr_details_retrieved": true,
  "ccr_transport_logs_retrieved": true,
  "ccr_provider": "synthetic",
  "requires_human_approval": true,
  "automatic_changes_performed": false,
  "status": "COMPLETED"
}
```

The synthetic CCR provider reads local test fixtures. It does not call or modify the real CCR system.

### Read-only safety

IRIS Resolve currently uses read-only support tools.

The agent can:

- Read synthetic ticket details
- Read synthetic CCR details
- Read synthetic CCR transport logs
- Propose diagnostics
- Identify missing evidence
- Recommend actions for human review

The agent does not:

- Retry CCR transports
- Change CCR item sets
- Modify ticket records
- Send outbound HL7 messages
- Apply production configuration changes
- Perform automatic corrective actions

The result includes:

```json
{
  "requires_human_approval": true,
  "automatic_changes_performed": false
}
```

### Rebuilding after dependency changes

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

Do not use `docker compose down -v`.