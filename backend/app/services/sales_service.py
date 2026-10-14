"""Sales order workflows.

The transition graph is validated here, not in the request handler and never
in the client. A role may attempt an action; the service decides whether the
current state allows it.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.sales import SalesOrder, SalesOrderLine, SalesOrderStatus
from app.models.user import Role, User
from app.schemas.sales import SalesOrderCreate, StatusChange
from app.services import activity

# Allowed workflow transitions. Any move not listed here is rejected.
ALLOWED_TRANSITIONS: dict[SalesOrderStatus, set[SalesOrderStatus]] = {
    SalesOrderStatus.OPEN: {SalesOrderStatus.PICKING, SalesOrderStatus.CANCELLED},
    SalesOrderStatus.PICKING: {SalesOrderStatus.SHIPPED, SalesOrderStatus.OPEN},
    SalesOrderStatus.SHIPPED: {SalesOrderStatus.INVOICED},
    SalesOrderStatus.INVOICED: set(),
    SalesOrderStatus.CANCELLED: set(),
}

# Roles permitted to move an order into each state.
# Purchasing is deliberately absent: buyers create orders, logistics fulfils them.
ROLE_PERMISSIONS: dict[SalesOrderStatus, set[Role]] = {
    SalesOrderStatus.OPEN: {Role.ADMIN},
    SalesOrderStatus.PICKING: {Role.ADMIN, Role.LOGISTICS},
    SalesOrderStatus.SHIPPED: {Role.ADMIN, Role.LOGISTICS},
    SalesOrderStatus.INVOICED: {Role.ADMIN},
    SalesOrderStatus.CANCELLED: {Role.ADMIN},
}


class TransitionError(ValueError):
    """Raised when a status change is not allowed."""


def can_transition(order: SalesOrder, target: SalesOrderStatus, user: User) -> tuple[bool, str]:
    """Check a transition against both the workflow graph and the actor role.

    Returns ``(allowed, reason)``. The reason is returned rather than raised
    so the endpoint can produce a specific HTTP error.
    """
    if target not in ALLOWED_TRANSITIONS.get(order.status, set()):
        return False, f"Cannot move an order from {order.status.value} to {target.value}"

    if user.role not in ROLE_PERMISSIONS.get(target, set()):
        allowed_roles = ", ".join(sorted(r.value for r in ROLE_PERMISSIONS.get(target, set())))
        return False, (
            f"Role '{user.role.value}' cannot set status {target.value}. "
            f"Allowed: {allowed_roles}"
        )

    return True, ""


def next_number(db: Session, company_code: str, year: int, prefix: str = "SO") -> str:
    """Build the next sequential order number for a company and year.

    Scoped to the company so two companies issuing orders on the same day do
    not collide on the number.
    """
    count = db.scalar(
        select(func.count())
        .select_from(SalesOrder)
        .where(SalesOrder.company_code == company_code)
        .where(func.strftime("%Y", SalesOrder.order_date) == str(year))
    )
    return f"{prefix}-{year}-{(count or 0) + 1:04d}"


def create_order(
    db: Session, company_code: str, actor: User, payload: SalesOrderCreate
) -> SalesOrder:
    """Create a sales order with its lines and log the event."""
    order = SalesOrder(
        company_code=company_code,
        number=next_number(db, company_code, date.today().year),
        customer_id=payload.customer_id,
        order_date=date.today(),
        delivery_date=payload.delivery_date,
        status=SalesOrderStatus.OPEN,
        notes=payload.notes,
    )

    for line in payload.lines:
        order.lines.append(
            SalesOrderLine(
                item_id=line.item_id,
                quantity=line.quantity,
                unit_price=line.unit_price,
            )
        )

    order.recalculate_total()
    db.add(order)
    db.flush()

    activity.record(
        db,
        company_code=company_code,
        actor=actor,
        entity="sales_order",
        action="created",
        entity_id=order.id,
        summary=f"Created sales order {order.number}",
        payload={"total": str(order.total), "lines": len(order.lines)},
    )
    return order


def change_status(
    db: Session, company_code: str, actor: User, order: SalesOrder, change: StatusChange
) -> SalesOrder:
    """Move an order to a new status, applying the side effects of that state.

    Picking and shipping update the line counters as well as the header,
    because those counters are what order accuracy is computed from.
    """
    target = change.status
    allowed, reason = can_transition(order, target, actor)
    if not allowed:
        raise TransitionError(reason)

    previous = order.status
    order.status = target

    if target == SalesOrderStatus.PICKING:
        for line in order.lines:
            if Decimal(line.qty_picked) < Decimal(line.quantity):
                line.qty_picked = line.quantity
    elif target == SalesOrderStatus.SHIPPED:
        for line in order.lines:
            line.qty_shipped = line.quantity
    elif target == SalesOrderStatus.OPEN and previous == SalesOrderStatus.PICKING:
        # Reopened for rework: reset the pick progress.
        for line in order.lines:
            line.qty_picked = Decimal("0")

    db.flush()

    activity.record(
        db,
        company_code=company_code,
        actor=actor,
        entity="sales_order",
        action="status_changed",
        entity_id=order.id,
        summary=f"{previous.value} -> {target.value}",
        payload={
            "from": previous.value,
            "to": target.value,
            "reason": change.reason,
            "at": datetime.now(UTC).isoformat(),
        },
    )
    return order