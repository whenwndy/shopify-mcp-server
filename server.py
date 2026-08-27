import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastmcp import FastMCP
from pydantic import Field

# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------

_DATA_PATH = Path(__file__).parent / "data" / "shopify.json"
_db: dict = json.loads(_DATA_PATH.read_text())


def _match(record: dict, field: str, value: str) -> bool:
    """Case-insensitive substring match on a field."""
    return value.lower() in str(record.get(field, "")).lower()


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    name="shopify-mock",
    version="1.0.0",
    instructions=(
        "Mock Shopify store for Posh Peanuts premium kids clothing. Query products, "
        "collections, customers, orders, inventory, discount codes, abandoned checkouts, "
        "refunds, and store analytics."
    ),
)

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@mcp.tool()
def get_products(
    id: Optional[str] = Field(default=None, description="Filter by product ID, e.g. prod_001"),
    title: Optional[str] = Field(default=None, description="Filter by product title (partial match)"),
    product_type: Optional[str] = Field(default=None, description="Filter by product type: onesie/romper/pajama_set/dress/top/bottom/bodysuit/accessory/gift_set"),
    status: Optional[str] = Field(default=None, description="Filter by status: active/draft/archived"),
    tag: Optional[str] = Field(default=None, description="Filter by tag — checks the tags array (partial match)"),
    collection: Optional[str] = Field(default=None, description="Filter by collection name — checks the collections array (partial match)"),
    vendor: Optional[str] = Field(default=None, description="Filter by vendor name (partial match)"),
) -> list[dict]:
    """List products. Optionally filter by ID, title, product type, status, tag, collection, or vendor."""
    results = _db["products"]
    if id:
        results = [r for r in results if r["id"].lower() == id.lower()]
    if title:
        results = [r for r in results if _match(r, "title", title)]
    if product_type:
        results = [r for r in results if _match(r, "product_type", product_type)]
    if status:
        results = [r for r in results if _match(r, "status", status)]
    if tag:
        results = [r for r in results if any(tag.lower() in t.lower() for t in r.get("tags", []))]
    if collection:
        results = [r for r in results if any(collection.lower() in c.lower() for c in r.get("collections", []))]
    if vendor:
        results = [r for r in results if _match(r, "vendor", vendor)]
    return results


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------

@mcp.tool()
def get_collections(
    id: Optional[str] = Field(default=None, description="Filter by collection ID, e.g. col_001"),
    title: Optional[str] = Field(default=None, description="Filter by collection title (partial match)"),
    published: Optional[bool] = Field(default=None, description="Filter by published status (true/false)"),
) -> list[dict]:
    """List collections. Optionally filter by ID, title, or published status."""
    results = _db["collections"]
    if id:
        results = [r for r in results if r["id"].lower() == id.lower()]
    if title:
        results = [r for r in results if _match(r, "title", title)]
    if published is not None:
        results = [r for r in results if r.get("published") == published]
    return results


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------

@mcp.tool()
def get_customers(
    id: Optional[str] = Field(default=None, description="Filter by customer ID, e.g. cust_001"),
    email: Optional[str] = Field(default=None, description="Filter by email address (partial match)"),
    last_name: Optional[str] = Field(default=None, description="Filter by last name (partial match)"),
    tag: Optional[str] = Field(default=None, description="Filter by customer tag — checks the tags array (partial match)"),
    accepts_marketing: Optional[bool] = Field(default=None, description="Filter by marketing opt-in status (true/false)"),
) -> list[dict]:
    """List customers. Optionally filter by ID, email, last name, tag, or marketing preference."""
    results = _db["customers"]
    if id:
        results = [r for r in results if r["id"].lower() == id.lower()]
    if email:
        results = [r for r in results if _match(r, "email", email)]
    if last_name:
        results = [r for r in results if _match(r, "last_name", last_name)]
    if tag:
        results = [r for r in results if any(tag.lower() in t.lower() for t in r.get("tags", []))]
    if accepts_marketing is not None:
        results = [r for r in results if r.get("accepts_marketing") == accepts_marketing]
    return results


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

@mcp.tool()
def get_orders(
    id: Optional[str] = Field(default=None, description="Filter by order ID, e.g. ord_001"),
    order_number: Optional[int] = Field(default=None, description="Filter by order number, e.g. 1001"),
    customer_id: Optional[str] = Field(default=None, description="Filter by customer ID"),
    customer_email: Optional[str] = Field(default=None, description="Filter by customer email (partial match)"),
    financial_status: Optional[str] = Field(default=None, description="Filter by financial status: paid/pending/refunded/partially_refunded"),
    fulfillment_status: Optional[str] = Field(default=None, description="Filter by fulfillment status: fulfilled/unfulfilled/partial"),
    start_date: Optional[str] = Field(default=None, description="Filter orders created on or after this ISO date, e.g. 2026-08-01"),
    end_date: Optional[str] = Field(default=None, description="Filter orders created on or before this ISO date, e.g. 2026-08-27"),
) -> list[dict]:
    """List orders. Optionally filter by ID, order number, customer, status, or date range."""
    results = _db["orders"]
    if id:
        results = [r for r in results if r["id"].lower() == id.lower()]
    if order_number is not None:
        results = [r for r in results if r["order_number"] == order_number]
    if customer_id:
        results = [r for r in results if r["customer_id"].lower() == customer_id.lower()]
    if customer_email:
        results = [r for r in results if _match(r, "customer_email", customer_email)]
    if financial_status:
        results = [r for r in results if _match(r, "financial_status", financial_status)]
    if fulfillment_status:
        results = [r for r in results if _match(r, "fulfillment_status", fulfillment_status)]
    if start_date:
        results = [r for r in results if r["created_at"] >= start_date]
    if end_date:
        # Append end-of-day sentinel so date-only strings include the full day
        end_sentinel = end_date if "T" in end_date else end_date + "T23:59:59Z"
        results = [r for r in results if r["created_at"] <= end_sentinel]
    return results


# ---------------------------------------------------------------------------
# Draft Orders
# ---------------------------------------------------------------------------

@mcp.tool()
def get_draft_orders(
    id: Optional[str] = Field(default=None, description="Filter by draft order ID, e.g. draft_001"),
    customer_id: Optional[str] = Field(default=None, description="Filter by customer ID"),
    status: Optional[str] = Field(default=None, description="Filter by status: open/invoice_sent"),
) -> list[dict]:
    """List draft orders. Optionally filter by ID, customer, or status."""
    results = _db["draft_orders"]
    if id:
        results = [r for r in results if r["id"].lower() == id.lower()]
    if customer_id:
        results = [r for r in results if r["customer_id"].lower() == customer_id.lower()]
    if status:
        results = [r for r in results if _match(r, "status", status)]
    return results


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------

@mcp.tool()
def get_inventory(
    product_id: Optional[str] = Field(default=None, description="Filter by product ID, e.g. prod_001"),
    product_title: Optional[str] = Field(default=None, description="Filter by product title (partial match)"),
    sku: Optional[str] = Field(default=None, description="Filter by SKU (partial match)"),
    low_stock: bool = Field(default=False, description="If true, return only variants where available <= 5"),
) -> list[dict]:
    """List inventory levels per variant. Filter by product, SKU, or flag low-stock items (available <= 5)."""
    results = _db["inventory_levels"]
    if product_id:
        results = [r for r in results if r["product_id"].lower() == product_id.lower()]
    if product_title:
        results = [r for r in results if _match(r, "product_title", product_title)]
    if sku:
        results = [r for r in results if _match(r, "sku", sku)]
    if low_stock:
        results = [r for r in results if r["available"] <= 5]
    return results


# ---------------------------------------------------------------------------
# Discount Codes
# ---------------------------------------------------------------------------

@mcp.tool()
def get_discount_codes(
    id: Optional[str] = Field(default=None, description="Filter by discount ID, e.g. disc_001"),
    code: Optional[str] = Field(default=None, description="Filter by discount code (partial match)"),
    status: Optional[str] = Field(default=None, description="Filter by status: active/expired/scheduled"),
    type: Optional[str] = Field(default=None, description="Filter by type: percentage/fixed_amount/free_shipping"),
) -> list[dict]:
    """List discount codes. Optionally filter by ID, code, status, or type."""
    results = _db["discount_codes"]
    if id:
        results = [r for r in results if r["id"].lower() == id.lower()]
    if code:
        results = [r for r in results if _match(r, "code", code)]
    if status:
        results = [r for r in results if _match(r, "status", status)]
    if type:
        results = [r for r in results if _match(r, "type", type)]
    return results


# ---------------------------------------------------------------------------
# Abandoned Checkouts
# ---------------------------------------------------------------------------

@mcp.tool()
def get_abandoned_checkouts(
    start_date: Optional[str] = Field(default=None, description="Filter checkouts abandoned on or after this ISO date, e.g. 2026-08-20"),
    end_date: Optional[str] = Field(default=None, description="Filter checkouts abandoned on or before this ISO date, e.g. 2026-08-27"),
    email_sent: Optional[bool] = Field(default=None, description="Filter by whether a recovery email was sent (true/false)"),
) -> list[dict]:
    """List abandoned checkouts. Optionally filter by date range or recovery email status."""
    results = _db["abandoned_checkouts"]
    if start_date:
        results = [r for r in results if r["abandoned_at"] >= start_date]
    if end_date:
        end_sentinel = end_date if "T" in end_date else end_date + "T23:59:59Z"
        results = [r for r in results if r["abandoned_at"] <= end_sentinel]
    if email_sent is not None:
        results = [r for r in results if r.get("email_sent") == email_sent]
    return results


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------

@mcp.tool()
def get_refunds(
    id: Optional[str] = Field(default=None, description="Filter by refund ID, e.g. ref_001"),
    order_id: Optional[str] = Field(default=None, description="Filter by originating order ID, e.g. ord_010"),
    reason: Optional[str] = Field(default=None, description="Filter by reason: size_exchange/defective/changed_mind/gift_return (partial match)"),
) -> list[dict]:
    """List refunds. Optionally filter by refund ID, order ID, or reason."""
    results = _db["refunds"]
    if id:
        results = [r for r in results if r["id"].lower() == id.lower()]
    if order_id:
        results = [r for r in results if r["order_id"].lower() == order_id.lower()]
    if reason:
        results = [r for r in results if _match(r, "reason", reason)]
    return results


# ---------------------------------------------------------------------------
# Analytics Summary
# ---------------------------------------------------------------------------

@mcp.tool()
def get_analytics_summary() -> dict:
    """Return the store analytics summary for the last 30 days (revenue, orders, top products, channels, etc.)."""
    return _db["analytics_summary"]


# ---------------------------------------------------------------------------
# Write: Create Discount Code
# ---------------------------------------------------------------------------

@mcp.tool()
def create_discount_code(
    code: str = Field(description="The discount code string, e.g. FALL20"),
    type: str = Field(description="Discount type: percentage / fixed_amount / free_shipping"),
    value: float = Field(description="Discount value — percent (e.g. 20 for 20%) or dollar amount (e.g. 10 for $10 off); use 0 for free_shipping"),
    usage_limit: Optional[int] = Field(default=None, description="Maximum number of times the code can be used (null = unlimited)"),
    starts_at: Optional[str] = Field(default=None, description="ISO datetime when the discount activates, e.g. 2026-09-01T00:00:00Z"),
    ends_at: Optional[str] = Field(default=None, description="ISO datetime when the discount expires, e.g. 2026-10-31T23:59:59Z"),
    minimum_order_usd: float = Field(default=0.00, description="Minimum order subtotal in USD required to use the code"),
    applies_to: str = Field(default="all", description="Scope: all / specific_collections / specific_products"),
) -> dict:
    """Create a new discount code and add it to the store."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    new_id = f"disc_{str(uuid.uuid4())[:8]}"
    status = "active"
    if starts_at and starts_at > now:
        status = "scheduled"
    new_code = {
        "id": new_id,
        "code": code.upper(),
        "type": type,
        "value": value,
        "usage_count": 0,
        "usage_limit": usage_limit,
        "starts_at": starts_at or now,
        "ends_at": ends_at,
        "status": status,
        "applies_to": applies_to,
        "minimum_order_usd": minimum_order_usd,
    }
    _db["discount_codes"].append(new_code)
    return new_code


# ---------------------------------------------------------------------------
# Write: Update Order
# ---------------------------------------------------------------------------

@mcp.tool()
def update_order(
    id: str = Field(description="Order ID to update, e.g. ord_001"),
    note: Optional[str] = Field(default=None, description="New note to set on the order (replaces existing note)"),
    tags: Optional[str] = Field(default=None, description="Comma-separated tags to set on the order, e.g. 'vip,gift,priority'"),
) -> dict:
    """Update the note or tags on an existing order. Returns the updated order."""
    for order in _db["orders"]:
        if order["id"].lower() == id.lower():
            if note is not None:
                order["note"] = note
            if tags is not None:
                order["tags"] = [t.strip() for t in tags.split(",") if t.strip()]
            order["updated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
            return order
    return {"error": f"Order '{id}' not found."}


# ---------------------------------------------------------------------------
# Write: Create Draft Order
# ---------------------------------------------------------------------------

@mcp.tool()
def create_draft_order(
    customer_id: str = Field(description="Customer ID for this draft order, e.g. cust_006"),
    line_items_json: str = Field(description='JSON string of line items, e.g. [{"product_id":"prod_001","variant_id":"var_001_1","title":"Newborn Welcome Gift Set","quantity":2,"price_usd":58.00}]'),
    note: Optional[str] = Field(default=None, description="Internal note for this draft order"),
) -> dict:
    """Create a new draft order (e.g. for wholesale or custom requests). Returns the created draft order."""
    # Look up customer name
    customer_name = customer_id
    for cust in _db["customers"]:
        if cust["id"].lower() == customer_id.lower():
            customer_name = f"{cust['first_name']} {cust['last_name']}"
            break

    try:
        line_items = json.loads(line_items_json)
    except json.JSONDecodeError as exc:
        return {"error": f"Invalid line_items_json: {exc}"}

    # Compute totals
    subtotal = sum(item.get("price_usd", 0) * item.get("quantity", 1) for item in line_items)
    for item in line_items:
        item["total_usd"] = round(item.get("price_usd", 0) * item.get("quantity", 1), 2)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    draft_count = len(_db["draft_orders"]) + 1
    new_id = f"draft_{str(uuid.uuid4())[:8]}"
    new_draft = {
        "id": new_id,
        "name": f"#D-{500 + draft_count}",
        "customer_id": customer_id,
        "customer_name": customer_name,
        "status": "open",
        "created_at": now,
        "line_items": line_items,
        "subtotal_usd": round(subtotal, 2),
        "total_usd": round(subtotal, 2),
        "note": note or "",
    }
    _db["draft_orders"].append(new_draft)
    return new_draft


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
