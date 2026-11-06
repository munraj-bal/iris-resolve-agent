Class SupportAgent.TicketService Extends Ens.BusinessService
{

Method OnProcessInput(
    pInput As SupportAgent.TicketRequest,
    Output pOutput As SupportAgent.ResolutionResponse
) As %Status
{
    If '$IsObject(pInput) {
        Quit $SYSTEM.Status.Error(
            5001,
            "IRIS Resolve Ticket Service received an invalid request object."
        )
    }

    Quit ..SendRequestSync(
        "IRIS Resolve Process",
        pInput,
        .pOutput
    )
}

ClassMethod Submit(
    rawTicketJSON As %String
) As %String
{
    Set sc = ##class(Ens.Director).CreateBusinessService(
        "IRIS Resolve Ticket Service",
        .service
    )

    If $SYSTEM.Status.IsError(sc) {
        Quit ..ErrorJSON(
            $SYSTEM.Status.GetErrorText(sc)
        )
    }

    If '$IsObject(service) {
        Quit ..ErrorJSON(
            "IRIS Resolve could not obtain the running Business Service."
        )
    }

    Set request = ##class(SupportAgent.TicketRequest).%New()

    If '$IsObject(request) {
        Quit ..ErrorJSON(
            "IRIS Resolve could not create the request object."
        )
    }

    Set request.RawTicketJSON = rawTicketJSON

    Set sc = service.ProcessInput(
        request,
        .response
    )

    If $SYSTEM.Status.IsError(sc) {
        Quit ..ErrorJSON(
            $SYSTEM.Status.GetErrorText(sc)
        )
    }

    If '$IsObject(response) {
        Quit ..ErrorJSON(
            "The Interoperability workflow returned no response object."
        )
    }

    Quit response.ResolutionJSON
}

ClassMethod ErrorJSON(
    message As %String
) As %String
{
    Set error = {
        "status": "TECHNICAL_ERROR",
        "decision": "NEEDS_INVESTIGATION",
        "reasoning": (message),
        "requires_human_approval": true,
        "automatic_changes_performed": false
    }

    Quit error.%ToJSON()
}

}