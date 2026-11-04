Class AutoSchema.AgentProcess Extends Ens.BusinessProcess
{

Method OnRequest(
    pRequest As AutoSchema.PayloadMsg,
    Output pResponse As Ens.StringResponse
) As %Status
{
    Set pResponse = ##class(Ens.StringResponse).%New()
    Set pResponse.StringValue = ##class(AutoSchema.AgentProcess).RunAgent(pRequest.RawJSON)
    Quit $$$OK
}

ClassMethod RunAgent(rawJSON As %String) As %String [ Language = python ]
{
    import sys
    import importlib

    python_path = "/opt/irisapp/src/python"
    if python_path not in sys.path:
        sys.path.insert(0, python_path)

    import autoschema_agent

    # Useful during development so edits are picked up in this session.
    importlib.reload(autoschema_agent)

    return autoschema_agent.process_payload(rawJSON)
}

}