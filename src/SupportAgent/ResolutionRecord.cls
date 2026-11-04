Class SupportAgent.ResolutionRecord Extends %Persistent
{

/// Optional iService ticket identifier.
Property TicketID As %String(MAXLEN = 100);

/// User-supplied ticket title.
Property Title As %String(MAXLEN = 1000) [ Required ];

/// User-supplied ticket description.
Property Description As %String(MAXLEN = "") [ Required ];

/// Optional associated CCR identifier.
Property CCRID As %String(MAXLEN = 100);

/// Optional affected environment.
Property Environment As %String(MAXLEN = 100);

/// Final validated decision.
Property Decision As %String(MAXLEN = 100) [ Required ];

/// Deterministically calculated confidence from 0.00 to 1.00.
Property Confidence As %Numeric(SCALE = 2);

/// Evidence-supported likely cause.
Property RootCause As %String(MAXLEN = 5000);

/// Recommended actions encoded as a JSON array.
Property RecommendedActionsJSON As %String(MAXLEN = "");

/// Missing information encoded as a JSON array.
Property MissingInformationJSON As %String(MAXLEN = "");

/// Risks encoded as a JSON array.
Property RisksJSON As %String(MAXLEN = "");

/// Evidence returned by read-only MCP tools.
Property EvidenceJSON As %String(MAXLEN = "");

/// Individual deterministic confidence factors.
Property ConfidenceFactorsJSON As %String(MAXLEN = "");

/// Complete original ticket request.
Property RawTicketJSON As %String(MAXLEN = "");

/// Complete validated solver response.
Property ResolutionJSON As %String(MAXLEN = "");

/// Human-readable explanation of the decision.
Property AgentReasoning As %String(MAXLEN = 5000);

/// Indicates whether human approval is required.
Property RequiresHumanApproval As %Boolean [ InitialExpression = 1 ];

/// Indicates which CCR provider was used.
Property CCRProvider As %String(MAXLEN = 100);

/// Record creation timestamp.
Property CreatedAt As %TimeStamp
    [ InitialExpression = {$ZDATETIME($HOROLOG,3)} ];

Index TicketIDIndex On TicketID;

Index CCRIDIndex On CCRID;

Index DecisionIndex On Decision;

}