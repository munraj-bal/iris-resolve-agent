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

/// Optional affected application or product, such as TrakCare.
Property Application As %String(MAXLEN = 200);

/// Optional customer or site identifier.
Property Site As %String(MAXLEN = 200);

/// Optional InterSystems IRIS namespace.
Property IRISNamespace As %String(MAXLEN = 100);

/// Optional episode, appointment, order, message, or transaction identifier.
Property AffectedIdentifier As %String(MAXLEN = 500);

/// Optional expected interface or message type, such as HL7 SIU_S15.
Property ExpectedInterface As %String(MAXLEN = 500);

/// Optional relevant timestamp or investigation time range.
Property RelevantTime As %String(MAXLEN = 500);

/// Converts the request into JSON for the Python solver.
Method ToJSON() As %String
{
    Set ticket = {
        "ticket_id": (..TicketID),
        "title": (..Title),
        "description": (..Description),
        "ccr_id": (..CCRID),
        "application": (..Application),
        "site": (..Site),
        "iris_namespace": (..IRISNamespace),
        "affected_identifier": (..AffectedIdentifier),
        "expected_interface": (..ExpectedInterface),
        "relevant_time": (..RelevantTime),
        "additional_evidence": (..AdditionalEvidence),
        "environment": (..Environment)
    }

    Return ticket.%ToJSON()
}

}
