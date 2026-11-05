Class SupportAgent.TicketRequest Extends Ens.Request
{

/// Complete JSON payload submitted by the CLI.
Property RawTicketJSON As %String(MAXLEN = "");

/// Optional iService ticket identifier.
Property TicketID As %String(MAXLEN = 100);

/// User-supplied ticket title.
Property Title As %String(MAXLEN = 1000);

/// User-supplied ticket description.
Property Description As %String(MAXLEN = "");

/// Optional CCR identifier supplied as context only.
Property CCRID As %String(MAXLEN = 100);

/// Optional affected application or product.
Property Application As %String(MAXLEN = 200);

/// Optional customer or site identifier.
Property Site As %String(MAXLEN = 200);

/// Optional InterSystems IRIS namespace.
Property IRISNamespace As %String(MAXLEN = 100);

/// Optional episode, appointment, order, message, or transaction identifier.
Property AffectedIdentifier As %String(MAXLEN = 500);

/// Optional expected interface or message type.
Property ExpectedInterface As %String(MAXLEN = 500);

/// Optional relevant timestamp or investigation time range.
Property RelevantTime As %String(MAXLEN = 500);

/// Optional manually supplied technical evidence.
Property AdditionalEvidence As %String(MAXLEN = "");

/// Optional affected environment.
Property Environment As %String(MAXLEN = 100);

/// Converts the request into JSON when RawTicketJSON was not supplied.
Method ToJSON() As %String
{
    If ..RawTicketJSON '= "" {
        Return ..RawTicketJSON
    }

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