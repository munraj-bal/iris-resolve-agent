# AutoSchema AI Agent

AutoSchema is an InterSystems IRIS Interoperability agent that validates incoming order JSON, repairs compatible schema differences with an AI agent, quarantines incomplete payloads, rejects invalid payloads, and stores each decision in IRIS with an explanation.

## Decision paths

AutoSchema supports four outcomes:

| Status | Description |
|---|---|
| `VALIDATED` | The payload already matches the strict target schema. |
| `AUTO_HEALED` | The AI agent safely mapped and converted the payload. |
| `QUARANTINED` | Required information is missing, ambiguous, or unsafe to infer. |
| `REJECTED` | The payload is malformed or contains an instruction-injection attempt. |

## Prerequisites

Install the following before starting:

- Docker Desktop using Linux containers
- Git
- InterSystems IRIS Community with AI Hub
- An AWS Bedrock API key
- Access to the required Amazon Bedrock model
- The `langchain_intersystems` wheel from the InterSystems AI Hub Early Access portal

## 1. Clone the repository

```cmd
git clone YOUR_REPOSITORY_URL
cd iris-autoschema-agent
```

Replace `YOUR_REPOSITORY_URL` with the URL of this repository.

## 2. Download the IRIS AI Hub Docker image

Download the x64 Community Docker image from the InterSystems AI Hub Early Access portal.

This project was developed using:

```text
iris-community-2027.1.0AI.109.0-docker.tar.gz
```

Save the archive somewhere outside the Git repository, for example:

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

## 3. Download the InterSystems LangChain wheel

Download the following wheel from the InterSystems AI Hub Early Access portal:

```text
langchain_intersystems-0.0.1-py3-none-any.whl
```

Place the wheel in:

```text
src\python\langchain_intersystems-0.0.1-py3-none-any.whl
```

The expected project structure is:

```text
iris-autoschema-agent\
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
├── src\
│   ├── AutoSchema\
│   │   ├── AgentProcess.cls
│   │   ├── OrderRecord.cls
│   │   ├── PayloadMsg.cls
│   │   └── setup.cls
│   └── python\
│       ├── autoschema_agent.py
│       ├── schema_mcp_server.py
│       └── langchain_intersystems-0.0.1-py3-none-any.whl
└── test_payloads\
```

## 4. Configure the local IRIS password

Create a file named `.env` in the same directory as `docker-compose.yml`.

```env
IRIS_PASSWORD=replace_with_your_actual_IRIS_password
```

Replace the placeholder with the password that will be assigned to the local IRIS `_SYSTEM` account.

For example:

```env
IRIS_PASSWORD=your_private_local_password
```

Do not use the following literal placeholder as the password:

```env
IRIS_PASSWORD=YOUR_CURRENT_IRIS_PASSWORD
```

The password must not be committed to Git.

Add this entry to `.gitignore`:

```gitignore
.env
```

Create a safe `.env.example` file that can be committed:

```env
IRIS_PASSWORD=replace_with_your_local_IRIS_password
```

The actual `.env` file must remain private.

## 5. Configure Docker Compose

Use the following `docker-compose.yml`:

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
| `9091` | `1972` | IRIS database connection |
| `9092` | `52773` | System Management Portal |

## 6. Start the container

From the repository directory, run:

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

Confirm that `IRIS_PASSWORD` was supplied to the container without displaying its value:

```cmd
docker exec iris-ai-hub python3 -c "import os; print('IRIS_PASSWORD set:', bool(os.getenv('IRIS_PASSWORD')))"
```

Expected output:

```text
IRIS_PASSWORD set: True
```

## 7. Set the IRIS `_SYSTEM` password

Open the System Management Portal:

```text
http://localhost:9092/csp/sys/UtilHome.csp
```

For a new container, sign in using:

```text
Username: _SYSTEM
Password: SYS
```

IRIS should request a password change.

Set the new `_SYSTEM` password to the exact same value stored in:

```text
.env
```

The `.env` variable does not automatically change the IRIS user account password. The `_SYSTEM` password in IRIS and the `IRIS_PASSWORD` value in `.env` must match.

Do not include the real password in documentation, screenshots, source code, or Git commits.

## 8. Install the Python dependencies

Run the following command from Windows Command Prompt:

```cmd
docker exec -u root iris-ai-hub python3 -m pip install --target /usr/irissys/mgr/python langchain langchain-aws
```

Install the InterSystems LangChain integration wheel:

```cmd
docker exec -u root iris-ai-hub python3 -m pip install --target /usr/irissys/mgr/python /opt/irisapp/src/python/langchain_intersystems-0.0.1-py3-none-any.whl
```

The warning about running `pip` as root is expected in this development container.

Warnings that a target directory already exists can occur when dependencies overlap. These warnings do not necessarily indicate that the installation failed. Check for the final `Successfully installed` message.

## 9. Open the IRIS terminal

Run:

```cmd
docker exec -it iris-ai-hub iris session iris
```

The terminal should open in the `USER` namespace:

```text
USER>
```

If the prompt is in a different namespace, switch to `USER`:

```objectscript
ZN "USER"
```

## 10. Import and compile the project classes

At the `USER>` prompt, run:

```objectscript
Do $SYSTEM.OBJ.LoadDir("/opt/irisapp/src/AutoSchema","ck")
```

The output should finish with:

```text
Load finished successfully.
```

Confirm that the agent class exists:

```objectscript
Write ##class(%Dictionary.ClassDefinition).%ExistsId("AutoSchema.AgentProcess")
```

Expected output:

```text
1
```

## 11. Rebuild the AI Hub Config Store registry

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

## 12. Configure AWS Bedrock and the MCP tools

Run the setup method with a valid AWS Bedrock API key:

```objectscript
Set sc = ##class(AutoSchema.Setup).Init("YOUR_BEDROCK_API_KEY")
Do $SYSTEM.Status.DisplayError(sc)
```

Replace `YOUR_BEDROCK_API_KEY` privately in the terminal.

Never include the real Bedrock API key in:

- `README.md`
- `.env.example`
- ObjectScript source files
- Python source files
- Git commits
- screenshots
- support messages
- public terminal output

A successful setup displays:

```text
AWS Bedrock Claude & Config Store initialised successfully!
```

### Existing Wallet credential

If setup reports that `SingleKeyAuth.claude` already exists, delete only the existing Wallet credential:

```objectscript
ZN "%SYS"
Set sc = ##class(%Wallet.KeyValue).Delete("SingleKeyAuth.claude")
Do $SYSTEM.Status.DisplayError(sc)
ZN "USER"
```

Run setup again using the replacement Bedrock API key:

```objectscript
Set sc = ##class(AutoSchema.Setup).Init("YOUR_BEDROCK_API_KEY")
Do $SYSTEM.Status.DisplayError(sc)
```

## 13. Run the test payloads

### Strictly valid payload

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

### Auto-healed payload

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

1. Map `client_ref` to `OrderID`.
2. Map `buyer_contact` to `CustomerEmail`.
3. Call `convert_dollars_to_cents()`.
4. Convert `129.99` dollars to `12999` cents.
5. Provide an explanation and confidence score.
6. Save the repaired payload in IRIS.

### Quarantined payload

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

The agent must not invent a customer email. Safely mapped fields should still be retained.

### Rejected malformed JSON

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

## 14. View saved records in IRIS

Open the System Management Portal:

```text
http://localhost:9092/csp/sys/UtilHome.csp
```

Select the `USER` namespace and go to:

```text
System Explorer → SQL
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

- the mapped order fields
- the final decision status
- the agent's explanation
- the original payload
- the converted amount in cents

## 15. Updating Python code

Python files are mounted into the container from:

```text
src\python\
```

Changes to `autoschema_agent.py` or `schema_mcp_server.py` normally do not require ObjectScript recompilation.

Save the Python file and rerun the test.

## 16. Updating ObjectScript classes

Changes to `.cls` files require recompilation:

```objectscript
Do $SYSTEM.OBJ.LoadDir("/opt/irisapp/src/AutoSchema","ck")
```

Use this after modifying:

```text
AgentProcess.cls
OrderRecord.cls
PayloadMsg.cls
setup.cls
```

## 17. Leaving the IRIS terminal

Run:

```objectscript
Halt
```

## 18. Stopping the container

To stop the container without removing it:

```cmd
docker compose stop
```

To restart it:

```cmd
docker compose start
```

Avoid recreating or deleting the container during development unless the setup steps can be repeated.

## Rebuild warning

The current development setup stores several items inside the running container:

- imported IRIS classes
- ObjectScript compiled routines
- saved `AutoSchema.OrderRecord` records
- AI Hub Config Store entries
- Wallet credentials
- manually installed Python packages

These commands can remove that state:

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

## Security notes

- Never commit `.env`.
- Never commit an AWS Bedrock API key.
- Never hard-code the `_SYSTEM` password in Python.
- Never publish a screenshot containing credentials.
- Rotate any credential that has been exposed in terminal output, chat messages, source code, or screenshots.
- Keep `.env.example` limited to placeholders.
- Use synthetic order data for demonstrations.
- Do not use customer, patient, production, NHS, or other confidential data.

## Current development limitation

The current setup uses manual package installation and does not persist IRIS data across container recreation.

For a reproducible release, the project should add:

- a custom `Dockerfile`
- pinned Python dependency versions
- automated ObjectScript class import
- automated Config Store descriptor registration
- durable IRIS database storage
- secure credential injection
- startup health checks
- automated test payloads

This will allow another developer or competition judge to start the application without manually rebuilding the environment.