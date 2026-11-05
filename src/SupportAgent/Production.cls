Class SupportAgent.Production Extends Ens.Production
{

XData ProductionDefinition
{
<Production Name="SupportAgent.Production">
    <Item
        Name="IRIS Resolve Ticket Service"
        Category="IRIS Resolve"
        ClassName="SupportAgent.TicketService"
        PoolSize="1"
        Enabled="true"
        Foreground="false"
    />
    <Item
        Name="IRIS Resolve Process"
        Category="IRIS Resolve"
        ClassName="SupportAgent.ResolutionProcess"
        PoolSize="1"
        Enabled="true"
        Foreground="false"
    />
</Production>
}

}