from mcp.server.fastmcp import FastMCP
import json

mcp = FastMCP("AutoSchemaTools")

@mcp.tool()
def get_target_schema() -> str:
    """Returns the strict target SQL schema and field conversion rules for AutoSchema.OrderRecord."""
    schema = {
        "OrderID": "String (Required). Map from order_id, client_ref, id, reference, etc.",
        "CustomerEmail": "String (Required). Must contain '@'. Map from buyer_contact, email, user_email",
        "OrderTotalCents": "Integer (Required). Must be in cents! If input is in dollars / float (for example 129.99), multiply by 100 -> 12999.",
        "Currency": "3-letter uppercase ISO string (Required), for example, USD, GBP, EUR."
    }
    return json.dumps(schema)

@mcp.tool()
def convert_dollars_to_cents(dollar_amount: float) -> int:
    """Safely converts a decimal dollar amount into integer cents."""
    return int(round(float(dollar_amount) * 100))

if __name__ == "__main__":
    mcp.run(transport="stdio")