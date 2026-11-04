Class AutoSchema.OrderRecord Extends %Persistent
{
    Property OrderID As %String [ Required ];
    Property CustomerEmail As %String [ Required ];
    Property OrderTotalCents As %Integer [ Required ];
    Property Currency As %String(MAXLEN = 3) [ Required ];
    Property Status As %String; // "VALIDATED", "AUTO_HEALED", "QUARANTINED", "REJECTED"
    Property AgentReasoning As %String(MAXLEN = 2000);
    Property RawPayload As %String(MAXLEN = 5000);

}
