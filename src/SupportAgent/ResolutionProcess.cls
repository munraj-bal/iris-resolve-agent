Class SupportAgent.ResolutionProcess Extends Ens.BusinessProcess
{

/// Receives a ticket from the Business Service and returns the AI result.
Method OnRequest(
    pRequest As SupportAgent.TicketRequest,
    Output pResponse As SupportAgent.ResolutionResponse
) As %Status
{
    If '$IsObject(pRequest) {
        Quit $SYSTEM.Status.Error(
            5001,
            "IRIS Resolve Process received an invalid request object."
        )
    }

    If pRequest.RawTicketJSON = "" {
        Quit $SYSTEM.Status.Error(
            5001,
            "IRIS Resolve Process received an empty ticket payload."
        )
    }

    Set pResponse = ##class(SupportAgent.ResolutionResponse).%New()

    If '$IsObject(pResponse) {
        Quit $SYSTEM.Status.Error(
            5001,
            "IRIS Resolve Process could not create the response object."
        )
    }

    Set pResponse.ResolutionJSON = ..SolveTicket(
        pRequest.RawTicketJSON
    )

    Quit $SYSTEM.Status.OK()
}

/// Invokes the Python solver through Embedded Python.
ClassMethod SolveTicket(
    rawTicketJSON As %String
) As %String [ Language = python ]
{
    import sys

    python_path = "/opt/irisapp/src/python"

    if python_path not in sys.path:
        sys.path.insert(0, python_path)

    import solver

    return solver.process_ticket(rawTicketJSON)
}

}