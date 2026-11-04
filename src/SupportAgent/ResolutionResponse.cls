Class SupportAgent.ResolutionResponse Extends Ens.Response
{

/// Identifier of the processed ticket.
Property TicketID As %String(MAXLEN = 100);

/// Final validated decision.
Property Decision As %String(MAXLEN = 100);

/// Deterministically calculated confidence from 0.00 to 1.00.
Property Confidence As %Numeric(SCALE = 2);

/// Identifier of the saved SupportAgent.ResolutionRecord.
Property RecordID As %Integer;

/// Complete structured resolution returned by the solver.
Property ResolutionJSON As %String(MAXLEN = "");

}