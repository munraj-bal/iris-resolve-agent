Class SupportAgent.TicketRequest Extends Ens.Request
{

/// Optional iService ticket identifier.
Property TicketID As %String(MAXLEN = 100);

/// User-supplied iService ticket title.
Property Title As %String(MAXLEN = 1000) [ Required ];

/// User-supplied iService ticket description.
Property Description As %String(MAXLEN = "") [ Required ];

/// Optional CCR identifier supplied as context only.
Property CCRID As %String(MAXLEN = 100);

/// Optional manually supplied logs, traces, SQL results, Find GUID output,
/// configuration details, error messages, or investigation notes.
Property AdditionalEvidence As %String(MAXLEN = "");

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
        "additional_evidence": (..AdditionalEvidence),
        "environment": (..Environment)
    }

    Return ticket.%ToJSON()
}

}
