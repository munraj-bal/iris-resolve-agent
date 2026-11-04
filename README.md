# AutoSchema AI Agent

AutoSchema is an AI-assisted schema validation and repair application built on InterSystems IRIS. The core agent is implemented as an `Ens.BusinessProcess` and uses IRIS AI Hub model configuration, MCP tools, Embedded Python, AWS Bedrock, and IRIS persistence.

Incoming order JSON is validated against a strict target schema. Compatible payloads can be repaired automatically, incomplete payloads are quarantined for review, and malformed or unsafe payloads are rejected. Each decision, explanation, original payload, and safely mapped values are stored in IRIS.

> **Current implementation status:** The agent logic can be tested directly through `AutoSchema.AgentProcess.RunAgent()`. The `Ens.BusinessProcess` and `OnRequest()` entry point are implemented, but a configured IRIS Interoperability production and end-to-end message trace are still required for the final competition workflow.

## Contents

- [Architecture](#architecture)
- [Decision paths](#decision-paths)
- [Target order schema](#target-order-schema)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Testing](#testing)
- [Viewing saved records](#viewing-saved-records)
- [MCP transport workaround](#mcp-transport-workaround)
- [Troubleshooting](#troubleshooting)
- [Rebuild warning](#rebuild-warning)
- [Security](#security)
- [Current development limitations](#current-development-limitations)

## Architecture

The current processing flow is:

```text
Incoming order JSON
        |
        v
Strict deterministic validation
        |
        +-----------------------------+
        | Valid                       | Invalid or non-standard
        v                             v
Save as VALIDATED             Load model configuration
                              from IRIS AI Hub
                                      |
                                      v
                              Start schema MCP server
                                      |
                                      v
                              Agent calls schema tools
                                      |
                                      v
                         AUTO_HEAL / QUARANTINE / REJECT
                                      |
                                      v
                         Deterministic safety validation
                                      |
                                      v
                         Save decision and explanation
                                  in IRIS
```

The main components are:

| Component | Purpose |
|---|---|
| `AutoSchema.AgentProcess` | IRIS business process and Embedded Python entry point |
| `AutoSchema.PayloadMsg` | Interoperability request carrying the raw JSON payload |
| `AutoSchema.OrderRecord` | Persistent IRIS record containing the decision and mapped fields |
| `AutoSchema.Setup` | Wallet and AI Hub Config Store initialisation |
| `autoschema_agent.py` | Validation, AI invocation, safety checks, and persistence logic |
| `schema_mcp_server.py` | MCP tools for schema discovery and amount conversion |
| AWS Bedrock | Hosts the Claude model used by the agent |
| IRIS AI Hub Config Store | Stores and supplies the model configuration |
| IRIS Wallet | Stores the Bedrock credential securely |

## Decision paths

AutoSchema supports four outcomes:

| Status | Description |
|---|---|
| `VALIDATED` | The payload already matches the strict target schema. No model call is required. |
| `AUTO_HEALED` | The agent safely mapped and converted all required fields with at least `0.85` confidence. |
| `QUARANTINED` | Required information is missing, ambiguous, or unsafe to infer. Safely mapped fields are retained. |
| `REJECTED` | The payload is malformed or contains an instruction-injection attempt. |

An `AUTO_HEAL` decision is accepted only when:

1. The returned confidence is a numeric value from `0` to `1`.
2. The confidence is at least `0.85`.
3. The healed payload passes the strict deterministic schema validator.
4. All four required fields are present.
5. `OrderTotalCents` is an integer.
6. `CustomerEmail` contains `@`.
7. `Currency` is a three-letter uppercase value.

If any of these checks fail, the application changes the decision to `QUARANTINE`.

## Target order schema

The target schema is:

```json
{
  "OrderID": "String, required",
  "CustomerEmail": "String containing @, required",
  "OrderTotalCents": "Integer amount in cents, required",
  "Currency": "Three-letter uppercase currency code, required"
}
```

Example valid payload:

```json
{
  "OrderID": "ORD-1001",
  "CustomerEmail": "customer@example.com",
  "OrderTotalCents": 14999,
  "Currency": "USD"
}
```

## Prerequisites

Install or obtain the following:

- Docker Desktop using Linux containers
- Git
- InterSystems IRIS Community with AI Hub
- An AWS Bedrock API key
- Access to the required Amazon Bedrock model
- The `langchain_intersystems` wheel from the InterSystems AI Hub Early Access portal

> This repository was developed against AI Hub EAP build `2027.1.0AI.109.0`, which was the build available from the EAP portal at development time. Confirm that this build is accepted for the competition before final submission.

## Installation

### 1. Clone the repository

```cmd
git clone https://github.com/munraj-bal/iris-autoschema-agent.git
cd iris-autoschema-agent
```

### 2. Download the IRIS AI Hub Docker image

Download the x64 Community Docker image from the InterSystems AI Hub Early Access portal.

This project was developed using:

```text
iris-community-2027.1.0AI.109.0-docker.tar.gz
```

Save the archive outside the Git repository, for example:

```text
C:\Users\your-user\Documents\iris_images\
```

Load the image into Docker:

```cmd
docker image load -i "C:\Users\your-user\Documents\iris_images\iris-community-2027.1.0AI.109.0-docker.tar.gz"
```

Successful output should include:

```text
Loaded image: docker.iscinternal.com/docker-intersystems/intersystems/iris-community:2027.1.0AI.109.0
```

Confirm that the image is available:

```cmd
docker images
```

### 3. Download the InterSystems LangChain wheel

Download:

```text
langchain_intersystems-0.0.1-py3-none-any.whl
```

from the InterSystems AI Hub Early Access portal.

Place it in:

```text
src\python\langchain_intersystems-0.0.1-py3-none-any.whl
```

> The wheel is excluded from Git because it is distributed through the InterSystems AI Hub Early Access Program. Each user must download it independently and place it in `src/python`.

The expected local project structure is:

```text
iris-autoschema-agent\
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── LICENSE
├── README.md
├── src\
│   ├── AutoSchema\
│   │   ├── AgentProcess.cls
│   │   ├── OrderRecord.cls
│   │   ├── PayloadMsg.cls
│   │   └── Setup.cls
│   └── python\
│       ├── autoschema_agent.py
│       ├── schema_mcp_server.py
│       └── langchain_intersystems-0.0.1-py3-none-any.whl
└── test_payloads\
    └── .gitkeep
```

The wheel, `.env`, and Python cache files are present locally but excluded from Git.

### 4. Configure the local IRIS password

Create a file named `.env` in the same directory as `docker-compose.yml`:

```env
IRIS_PASSWORD=replace_with_your_local_IRIS_password
```

Replace the placeholder with the password that will be assigned to the local IRIS `_SYSTEM` account.

Do not include quotes around the password unless the value specifically requires them.

Do not commit `.env`.

The repository contains a safe `.env.example` file:

```env
IRIS_PASSWORD=replace_with_your_local_IRIS_password
```

The `.gitignore` file must contain:

```gitignore
.env
.env.*
!.env.example
```

### 5. Review Docker Compose

The supplied `docker-compose.yml` contains:

```yaml
services:
  iris:
    image: docker.iscinternal.com/docker-intersystems/intersystems/iris-community:2027.1.0AI.109.0
    pull_policy: never
    container_name: iris-ai-hub
    environment:
      IRIS_PASSWORD: "${IRIS_PASSWORD}"
    ports:
      - "9091:1972"
      - "9092:52773"
    volumes:
      - ./src:/opt/irisapp/src
      - ./test_payloads:/opt/irisapp/test_payloads
```

The mapped ports are:

| Local port | Container port | Purpose |
|---|---:|---|
| `9091` | `1972` | IRIS database connection from the Windows host |
| `9092` | `52773` | IRIS System Management Portal |

Python executing inside the container connects to IRIS through:

```text
localhost:1972
```

The mapped port `9091` is only required when connecting from the Windows host.

### 6. Start the container

From the repository directory:

```cmd
docker compose up -d
```

Check the container:

```cmd
docker compose ps
```

The expected status is:

```text
Up ... (healthy)
```

Confirm that `IRIS_PASSWORD` was supplied without displaying its value:

```cmd
docker exec iris-ai-hub python3 -c "import os; print('IRIS_PASSWORD set:', bool(os.getenv('IRIS_PASSWORD')))"
```

Expected output:

```text
IRIS_PASSWORD set: True
```

### 7. Set the IRIS `_SYSTEM` password

Open the IRIS System Management Portal:

```text
http://localhost:9092/csp/sys/UtilHome.csp
```

For a new container, sign in using:

```text
Username: _SYSTEM
Password: SYS
```

IRIS should request a password change.

Set the new `_SYSTEM` password to the exact same value stored in `.env`.

The `.env` environment variable does not automatically change the IRIS user account password. The following two values must match:

```text
IRIS _SYSTEM password
IRIS_PASSWORD value in .env
```

Do not include the real password in documentation, source code, screenshots, support messages, or Git commits.

### 8. Install the Python dependencies

Run from Windows Command Prompt:

```cmd
docker exec -u root iris-ai-hub python3 -m pip install --target /usr/irissys/mgr/python langchain langchain-aws
```

Install the InterSystems LangChain integration wheel:

```cmd
docker exec -u root iris-ai-hub python3 -m pip install --target /usr/irissys/mgr/python /opt/irisapp/src/python/langchain_intersystems-0.0.1-py3-none-any.whl
```

The warning about running `pip` as root is expected in this development container.

Warnings that target directories already exist may appear because the InterSystems wheel installs dependencies that overlap with the first command. Check that the installation finishes with:

```text
Successfully installed
```

### 9. Open the IRIS terminal

```cmd
docker exec -it iris-ai-hub iris session iris
```

The terminal should open in the `USER` namespace:

```text
USER>
```

If the prompt is in a different namespace:

```objectscript
ZN "USER"
```

### 10. Import and compile the project classes

At the `USER>` prompt:

```objectscript
Do $SYSTEM.OBJ.LoadDir("/opt/irisapp/src/AutoSchema","ck")
```

The output11. Rebuild the AI Hub Config Store registry

Run:

```objectscript
Do ##class(%ConfigStore.DescriptorManager).RebuildRegistry()
```

Confirm that the LLM descriptor is registered:

```objectscript
Set descriptor = ""
Set sc = ##class(%ConfigStore.DescriptorManager).GetDescriptorClass("AI","LLM","",.descriptor)
Do $SYSTEM.Status.DisplayError(sc)
Write !,"Descriptor: ",descriptor,!
```

Expected output:

```text
Descriptor: %AI.ConfigStore.LLMDescriptor
```

### 12. Configure AWS Bedrock and the MCP tools

Run the setup method using a valid AWS Bedrock API key:

```objectscript
Set sc = ##class(AutoSchema.Setup).Init("YOUR_BEDROCK_API_KEY")
Do $SYSTEM.Status.DisplayError(sc)
```

Replace `YOUR_BEDROCK_API_KEY` privately in the terminal.

Never include the real Bedrock API key in:

- `README.md`
- `.env.example`
- ObjectScript source
- Python source
- Git commits
- screenshots
- support messages
- public terminal output

A successful setup displays:

```text
AWS Bedrock Claude & Config Store initialised successfully!
```

The current setup creates:

```text
AI.LLM.claude_single
AI.MCP.schema_tools
```

The model configuration uses:

```text
Provider: bedrock_converse
Region: eu-west-2
```

The configured model identifier is:

```text
eu.anthropic.claude-sonnet-5-5
```

Model availability depends on the AWS account, region, and enabled Bedrock model access.

#### Existing Wallet credential

If setup reports that `SingleKeyAuth.claude` already exists, delete only the existing Wallet credential:

```objectscript
ZN "%SYS"
Set sc = ##class(%Wallet.KeyValue).Delete("SingleKeyAuth.claude")
Do $SYSTEM.Status.DisplayError(sc)
ZN "USER"
```

Run setup again:

```objectscript
Set sc = ##class(AutoSchema.Setup).Init("YOUR_BEDROCK_API_KEY")
Do $SYSTEM.Status.DisplayError(sc)
```

## Testing

The following tests call the agent helper directly. They verify the validation, model, MCP tool, safety, and persistence logic.

They do not yet demonstrate processing through a running Interoperability production.

### Test 1: strictly valid payload

This payload already matches the target schema and does not require an AI call:

```objectscript
Write ##class(AutoSchema.AgentProcess).RunAgent("{""OrderID"":""DEMO_VALID_001"",""CustomerEmail"":""valid@example.com"",""OrderTotalCents"":14999,""Currency"":""USD""}")
```

Expected status:

```text
VALIDATED
```

Expected saved values:

```text
OrderID: DEMO_VALID_001
CustomerEmail: valid@example.com
OrderTotalCents: 14999
Currency: USD
Status: VALIDATED
```

### Test 2: auto-healed payload

This payload uses alternative field names and provides the amount in dollars:

```objectscript
Write ##class(AutoSchema.AgentProcess).RunAgent("{""client_ref"":""DEMO_HEAL_001"",""buyer_contact"":""heal@example.com"",""total_amount"":129.99,""currency"":""USD""}")
```

Expected status:

```text
AUTO_HEALED
```

Expected saved values:

```text
OrderID: DEMO_HEAL_001
CustomerEmail: heal@example.com
OrderTotalCents: 12999
Currency: USD
Status: AUTO_HEALED
```

The agent should:

1. Call `get_target_schema()`.
2. Map `client_ref` to `OrderID`.
3. Map `buyer_contact` to `CustomerEmail`.
4. Call `convert_dollars_to_cents()`.
5. Convert `129.99` dollars to `12999` cents.
6. Return a confidence score.
7. Pass the healed payload through strict deterministic validation.
8. Save the repaired payload in IRIS.

### Test 3: quarantined payload

This payload is missing the required customer email:

```objectscript
Write ##class(AutoSchema.AgentProcess).RunAgent("{""order_id"":""DEMO_QUAR_001"",""customer_name"":""Demo Customer"",""total_amount"":49.99,""currency"":""USD""}")
```

Expected status:

```text
QUARANTINED
```

Expected saved values:

```text
OrderID: DEMO_QUAR_001
CustomerEmail: UNKNOWN
OrderTotalCents: 4999
Currency: USD
Status: QUARANTINED
```

The agent must not invent a customer email. Fields that can be mapped safely should still be retained.

### Test 4: rejected malformed JSON

The following input intentionally contains invalid JSON:

```objectscript
Write ##class(AutoSchema.AgentProcess).RunAgent("{""OrderID"":""DEMO_REJECT_001""")
```

Expected status:

```text
REJECTED
```

Expected reasoning:

```text
Invalid JSON syntax
```

Malformed JSON is rejected before any model call.

## Viewing saved records

Open the IRIS System Management Portal:

```text
http://localhost:9092/csp/sys/UtilHome.csp
```

Select the `USER` namespace and go to:

```text
System Explorer > SQL
```

Run:

```sql
SELECT
    ID,
    OrderID,
    CustomerEmail,
    OrderTotalCents,
    Currency,
    Status,
    AgentReasoning,
    RawPayload
FROM AutoSchema.OrderRecord
ORDER BY ID DESC
```

The query displays:

- mapped order fields
- final decision status
- agent explanation
- confidence score
- original payload
- converted amount in cents

## MCP transport workaround

The model configuration is loaded from the IRIS AI Hub Config Store through:

```python
init_chat_model(llm_config_name, conn)
```

The schema MCP server is currently started explicitly from Embedded Python using:

```python
StdioServerParameters
stdio_client
ClientSession
load_mcp_tools
```

This works around a stdio compatibility issue encountered in Embedded Python. The MCP client attempted to call `fileno()` on IRIS's redirected output stream:

```text
AttributeError: 'iris.Stdout' object has no attribute 'fileno'
```

The workaround supplies a real stderr log file when starting the MCP subprocess:

```text
/tmp/autoschema-mcp-stderr.log
```

The MCP tools remain active and callable by the agent.

The `AI.MCP.schema_tools` Config Store entry is created by the setup class for AI Hub configuration completeness, but the current runtime launches `schema_mcp_server.py` explicitly because of this transport issue.

## Troubleshooting

### View the MCP error log

From Windows Command Prompt:

```cmd
docker exec iris-ai-hub cat /tmp/autoschema-mcp-stderr.log
```

An empty log can indicate that no MCP subprocess errors have occurred.

### `CLASS DOES NOT EXIST`

Example:

```text
<CLASS DOES NOT EXIST> *AutoSchema.AgentProcess
```

Import and compile the classes:

```objectscript
Do $SYSTEM.OBJ.LoadDir("/opt/irisapp/src/AutoSchema","ck")
```

### `No descriptor found for AI.LLM`

Run:

```objectscript
Do ##class(%ConfigStore.DescriptorManager).RebuildRegistry()
```

Then rerun `AutoSchema.Setup.Init(...)`.

### `Object to Load not found` for `AI.LLM.claude_single`

The model configuration has not been created successfully.

Run:

```objectscript
Set sc = ##class(AutoSchema.Setup).Init("YOUR_BEDROCK_API_KEY")
Do $SYSTEM.Status.DisplayError(sc)
```

### Wallet key already exists

Example:

```text
ID key not unique for extent '%Wallet.LocalStorage'
```

Delete only the existing Wallet key:

```objectscript
ZN "%SYS"
Set sc = ##class(%Wallet.KeyValue).Delete("SingleKeyAuth.claude")
Do $SYSTEM.Status.DisplayError(sc)
ZN "USER"
```

Then rerun setup.

### `Access Denied` from `iris.connect()`

Confirm that:

1. `IRIS_PASSWORD` exists in the container.
2. The value in `.env` matches the current IRIS `_SYSTEM` password.
3. The container was started after the `.env` file was created.
4. The `_SYSTEM` password was changed from `SYS` in SMP.

Check only whether the variable exists:

```cmd
docker exec iris-ai-hub python3 -c "import os; print('IRIS_PASSWORD set:', bool(os.getenv('IRIS_PASSWORD')))"
```

Do not print the password value.

### `No module named langchain`

Install:

```cmd
docker exec -u root iris-ai-hub python3 -m pip install --target /usr/irissys/mgr/python langchain langchain-aws
```

### `No module named langchain_intersystems`

Install the EAP wheel:

```cmd
docker exec -u root iris-ai-hub python3 -m pip install --target /usr/irissys/mgr/python /opt/irisapp/src/python/langchain_intersystems-0.0.1-py3-none-any.whl
```

### Technical quarantine versus business quarantine

A technical failure is stored as `QUARANTINED` with reasoning beginning:

```text
AI Hub Agent Error:
```

A normal business quarantine contains an agent explanation, such as:

```text
CustomerEmail is missing.
```

Technical quarantines should not be presented as successful AI decisions.

## Updating Python code

Python files are mounted into the container from:

```text
src\python\
```

Changes to the following files normally do not require ObjectScript recompilation:

```text
autoschema_agent.py
schema_mcp_server.py
```

Save the file and rerun the test.

`AgentProcess.cls` reloads `autoschema_agent` during development so changes are picked up by the current session.

## Updating ObjectScript classes

Changes to `.cls` files require recompilation:

```objectscript
Do $SYSTEM.OBJ.LoadDir("/opt/irisapp/src/AutoSchema","ck")
```

Use this after modifying:

```text
AgentProcess.cls
OrderRecord.cls
PayloadMsg.cls
Setup.cls
```

## Leaving the IRIS terminal

```objectscript
Halt
```

## Stopping and restarting the container

Stop without removing the container:

```cmd
docker compose stop
```

Restart the same container:

```cmd
docker compose start
```

Check its status:

```cmd
docker compose ps
```

Avoid recreating or deleting the container during development unless the setup steps can be repeated.

## Rebuild warning

The current development setup stores several items in the running container:

- imported IRIS classes
- compiled ObjectScript routines
- saved `AutoSchema.OrderRecord` records
- AI Hub Config Store entries
- Wallet credentials
- manually installed Python packages

The following commands may remove that state:

```cmd
docker compose down
docker compose up -d --force-recreate
docker rm iris-ai-hub
```

After recreating the container, repeat the setup in this order:

1. Start the container.
2. Confirm `IRIS_PASSWORD` is present.
3. Sign in to SMP using `_SYSTEM` and `SYS`.
4. Change the `_SYSTEM` password to match `.env`.
5. Install `langchain` and `langchain-aws`.
6. Install the `langchain_intersystems` wheel.
7. Import and compile the AutoSchema classes.
8. Rebuild the Config Store descriptor registry.
9. Run `AutoSchema.Setup.Init(...)`.
10. Run the test payloads.

## Security

- Never commit `.env`.
- Never commit an AWS Bedrock API key.
- Never hard-code the `_SYSTEM` password in Python.
- Never print secret values during environment checks.
- Never publish screenshots containing credentials.
- Rotate any credential exposed in source code, terminal output, chat messages, or screenshots.
- Keep `.env.example` limited to placeholders.
- Obtain the EAP wheel through the official InterSystems portal.
- Use synthetic order data in demonstrations.
- Do not use customer, patient, NHS, production, or other confidential data.

## Current development limitations

The current setup has the following limitations:

1. Python packages are installed manually in the running container.
2. IRIS data is not persisted across container recreation.
3. Wallet and Config Store setup is performed manually.
4. The MCP stdio transport uses a runtime workaround.
5. Test payloads currently call `RunAgent()` directly.
6. A running Interoperability production has not yet been configured.
7. An end-to-end Interoperability message trace has not yet been demonstrated.
8. Python dependency versions are not yet pinned.
9. Automated tests have not yet been added.

For a reproducible competition release, the project should add:

- a custom `Dockerfile`
- pinned Python dependency versions
- automated ObjectScript import and compilation
- automated Config Store registry initialisation
- durable IRIS database storage
- secure credential injection
- startup health checks
- automated test payloads
- a configured IRIS Interoperability production
- a Business Service or test service that sends `AutoSchema.PayloadMsg`
- an end-to-end message trace
- a demonstration video

## License

This project is licensed under the MIT License. See LICENSE.