"""Administrative maintenance endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import delete, select

from app.api.deps import Administrator, CurrentCompany, DbSession
from app.models import (
    ActivityEvent,
    Customer,
    DemandLine,
    Item,
    PurchaseOrder,
    PurchaseOrderLine,
    SalesOrder,
    SalesOrderLine,
    ShipmentRoute,
    Vendor,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/purge")
def purge_company_data(
    db: DbSession, company: CurrentCompany, _: Administrator
) -> dict[str, object]:
    """Delete every business record of the active company.

    Users, companies and grants survive so the operator stays signed in and the
    installation can be seeded again. Deletion order follows the foreign keys:
    lines first, then orders, then the master data they reference.
    """
    code = company.code

    sales_orders = select(SalesOrder.id).where(SalesOrder.company_code == code)
    purchase_orders = select(PurchaseOrder.id).where(PurchaseOrder.company_code == code)

    statements = [
        ("sales_order_lines", delete(SalesOrderLine).where(SalesOrderLine.order_id.in_(sales_orders))),
        (
            "purchase_order_lines",
            delete(PurchaseOrderLine).where(PurchaseOrderLine.order_id.in_(purchase_orders)),
        ),
        ("demand_lines", delete(DemandLine).where(DemandLine.company_code == code)),
        ("activity_events", delete(ActivityEvent).where(ActivityEvent.company_code == code)),
        ("routes", delete(ShipmentRoute).where(ShipmentRoute.company_code == code)),
        ("sales_orders", delete(SalesOrder).where(SalesOrder.company_code == code)),
        ("purchase_orders", delete(PurchaseOrder).where(PurchaseOrder.company_code == code)),
        ("items", delete(Item).where(Item.company_code == code)),
        ("customers", delete(Customer).where(Customer.company_code == code)),
        ("vendors", delete(Vendor).where(Vendor.company_code == code)),
    ]

    deleted: dict[str, int] = {}
    for name, statement in statements:
        deleted[name] = db.execute(statement).rowcount or 0

    db.commit()
    return {"company_code": code, "deleted": deleted}
