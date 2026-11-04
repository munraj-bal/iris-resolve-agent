Class SupportAgent.ResolutionProcess Extends Ens.BusinessProcess
{

Method OnRequest(
    pRequest As SupportAgent.TicketRequest,
    Output pResponse As SupportAgent.ResolutionResponse
) As %Status
{
    Set pResponse = ##class(SupportAgent.ResolutionResponse).%New()
    Set pResponse.TicketID = pRequest.TicketID
    Set pResponse.ResolutionJSON = ##class(SupportAgent.ResolutionProcess).SolveTicket(pRequest.ToJSON())

    Quit $$$OK
}

ClassMethod SolveTicket(
    rawTicketJSON As %String
) As %String [ Language = python ]
{
    import importlib
    import sys

    python_path = "/opt/irisapp/src/python"

    if python_path not in sys.path:
        sys.path.insert(0, python_path)

    import solver

    # Reload during development so mounted Python changes are picked up.
    importlib.reload(solver)

    return solver.process_ticket(rawTicketJSON)
}

}