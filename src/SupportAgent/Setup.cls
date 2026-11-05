Class SupportAgent.Setup
{

ClassMethod Init(apiKey As %String) As %Status
{
    New $NAMESPACE

    Set $NAMESPACE = "%SYS"

    // Create security resources for the IRIS Wallet.
    Do ##class(Security.Resources).Create("%MyUseResource")
    Do ##class(Security.Resources).Create("%MyEditResource")

    // Create the Wallet collection for the Bedrock credential.
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

    Set $NAMESPACE = "USER"

    Do ##class(%ConfigStore.DescriptorManager).RebuildRegistry()

    // Replace the existing model configuration.
    Do ##class(%ConfigStore.Configuration).Delete(
        "AI.LLM.claude_single"
    )

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

    Write !,
        "IRIS Resolve Bedrock model initialised successfully!",
        !

    Quit $SYSTEM.Status.OK()
}

}