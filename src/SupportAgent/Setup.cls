Class SupportAgent.Setup
{

ClassMethod Init(apiKey As %String) As %Status
{
    New $NAMESPACE

    Set $NAMESPACE = "%SYS"

    // Create security resources for the IRIS Wallet.
    Do ##class(Security.Resources).Create("%MyUseResource")
    Do ##class(Security.Resources).Create("%MyEditResource")

    // Create the Wallet collection for AWS credentials.
    Do ##class(%Wallet.Collection).Create(
        "SingleKeyAuth",
        {
            "UseResource": "%MyUseResource",
            "EditResource": "%MyEditResource"
        }
    )

    Set secret = {
        "Usage": "CUSTOM",
        "Secret": {
            "apiKey": (apiKey)
        }
    }

    Set sc = ##class(%Wallet.KeyValue).Create(
        "SingleKeyAuth.claude",
        secret
    )

    If $SYSTEM.Status.IsError(sc) {
        Do $SYSTEM.Status.DisplayError(sc)
        Quit sc
    }

    // Switch to USER and create the IRIS AI Hub configurations.
    Set $NAMESPACE = "USER"

    Do ##class(%ConfigStore.Configuration).Delete(
        "AI.LLM.claude_single"
    )

    // Remove the old AutoSchema MCP configuration if it exists.
    Do ##class(%ConfigStore.Configuration).Delete(
        "AI.MCP.schema_tools"
    )

    // Remove the current IRIS Resolve configuration if it exists.
    Do ##class(%ConfigStore.Configuration).Delete(
        "AI.MCP.ticket_tools"
    )

    // Create the AWS Bedrock model configuration.
    Set bedrockConfig = {
        "model_provider": "bedrock_converse",
        "model": "eu.anthropic.claude-sonnet-5-5",
        "region_name": "eu-west-2",
        "bedrock_api_key":
            "secret://SingleKeyAuth.claude#apiKey"
    }

    Set sc = ##class(%ConfigStore.Configuration).Create(
        "AI",
        "LLM",
        "",
        "claude_single",
        bedrockConfig
    )

    If $SYSTEM.Status.IsError(sc) {
        Do $SYSTEM.Status.DisplayError(sc)
        Quit sc
    }

    // Create the read-only ticket and CCR MCP configuration.
    Set mcpConfig = {
        "command": "python3",
        "args": [
            "/opt/irisapp/src/python/ticket_mcp_server.py"
        ],
        "transport": "stdio"
    }

    Set sc = ##class(%ConfigStore.Configuration).Create(
        "AI",
        "MCP",
        "",
        "ticket_tools",
        mcpConfig
    )

    If $SYSTEM.Status.IsError(sc) {
        Do $SYSTEM.Status.DisplayError(sc)
        Quit sc
    }

    Write !,
        "IRIS Resolve Bedrock and Config Store initialised successfully!",
        !

    Quit $$$OK
}

}