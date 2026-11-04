Class SupportAgent.TicketRequest Extends Ens.Request
{

/// Optional iService ticket identifier.
Property TicketID As %String(MAXLEN = 100);

/// User-supplied iService ticket title.
Property Title As %String(MAXLEN = 1000) [ Required ];

/// User-supplied iService ticket description.
Property Description As %String(MAXLEN = "") [ Required ];

/// Optional CCR identifier associated with the ticket.
Property CCRID As %String(MAXLEN = 100);

/// Optional affected environment, such as BASE, TEST, UAT, or LIVE.
Property Environment As %String(MAXLEN = 100);

/// Converts the request into JSON for the Python solver.
Method ToJSON() As %String
{
    Set ticket = {
        "ticket_id": (..TicketID),
        "title": (..Title),
        "description": (..Description),
        "ccr_id": (..CCRID),
        "environment": (..Environment)
    }

    Return ticket.%ToJSON()
}

}