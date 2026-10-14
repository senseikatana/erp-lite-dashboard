"""Purchase order workflows: receiving and the quality control gate.

Inventory is only ever increased by a Quality approval, never by the receipt
itself. That is the whole reason the QC gate exists: goods sit in
``QC_PENDING`` and are invisible to stock until a Quality user accepts them.

Approval is idempotent. Re-approving a line that already passed is a no-op,
so a double-clicked button cannot inflate inventory.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.item import Item
from app.models.purchasing import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    QualityStatus,
)
from app.models.user import Role, User
from app.schemas.purchasing import (
    PurchaseOrderCreate,
    QualityDecisionRequest,
    ReceiptRequest,
)
from app.services import activity


class WorkflowError(ValueError):
    """Raised when an operation is not valid for the current state."""


# Roles permitted to drive each transition.
ROLE_PERMISSIONS: dict[PurchaseOrderStatus, set[Role]] = {
    PurchaseOrderStatus.OPEN: {Role.ADMIN, Role.BUYER},
    PurchaseOrderStatus.RECEIVED: {Role.ADMIN, Role.LOGISTICS},
    PurchaseOrderStatus.QC_PENDING: {Role.ADMIN, Role.QUALITY},
    PurchaseOrderStatus.QC_APPROVED: {Role.ADMIN},
    PurchaseOrderStatus.REJECTED: {Role.ADMIN, Role.BUYER},
    PurchaseOrderStatus.CLOSED: {Role.ADMIN},
}

# Statuses from which a Quality decision is accepted.
QC_DECISION_STATES = {PurchaseOrderStatus.QC_PENDING, PurchaseOrderStatus.RECEIVED}


def assert_allowed(status: PurchaseOrderStatus, user: User) -> None:
    """Raise when the actor's role may not drive a transition to ``status``."""
    permitted = ROLE_PERMISSIONS.get(status, set())
    if user.role not in permitted:
        allowed = ", ".join(sorted(r.value for r in permitted))
        raise WorkflowError(
            f"Role '{user.role.value}' cannot set status {status.value}. Allowed: {allowed}"
        )


def next_number(db: Session, company_code: str, year: int, prefix: str = "PO") -> str:
    """Next sequential purchase order number for a company and year."""
    count = db.scalar(
        select(func.count())
        .select_from(PurchaseOrder)
        .where(PurchaseOrder.company_code == company_code)
        .where(func.strftime("%Y", PurchaseOrder.order_date) == str(year))
    )
    return f"{prefix}-{year}-{(count or 0) + 1:04d}"


def create_order(
    db: Session, company_code: str, actor: User, payload: PurchaseOrderCreate
) -> PurchaseOrder:
    assert_allowed(PurchaseOrderStatus.OPEN, actor)

    order = PurchaseOrder(
        company_code=company_code,
        number=next_number(db, company_code, date.today().year),
        vendor_id=payload.vendor_id,
        order_date=date.today(),
        expected_date=payload.expected_date,
        status=PurchaseOrderStatus.OPEN,
    )
    for line in payload.lines:
        order.lines.append(
            PurchaseOrderLine(
                item_id=line.item_id,
                quantity=line.quantity,
                unit_cost=line.unit_cost,
            )
        )

    order.recalculate_total()
    db.add(order)
    db.flush()

    activity.record(
        db,
        company_code=company_code,
        actor=actor,
        entity="purchase_order",
        action="created",
        entity_id=order.id,
        summary=f"Created purchase order {order.number}",
        payload={"total": str(order.total), "lines": len(order.lines)},
    )
    return order


def receive(
    db: Session, company_code: str, actor: User, order: PurchaseOrder, payload: ReceiptRequest
) -> PurchaseOrder:
    """Book goods receipt against an order.

    Lines omitted from the payload are received in full, which keeps the
    common "receive everything" case to a single click.
    """
    if order.status not in {PurchaseOrderStatus.OPEN, PurchaseOrderStatus.RECEIVED}:
        raise WorkflowError(f"Cannot receive goods on an order in status {order.status.value}")

    assert_allowed(PurchaseOrderStatus.RECEIVED, actor)

    requested = {line.line_id: line.quantity_received for line in (payload.lines or [])}

    for line in order.lines:
        quantity = requested.get(line.id, Decimal(line.quantity))
        line.qty_received = quantity
        line.qc_status = QualityStatus.PENDING

    order.status = PurchaseOrderStatus.RECEIVED
    db.flush()

    # Quality is a separate gate. When the company requires it, receiving moves
    # the order straight to QC_PENDING so it shows up on Quality's queue.
    from app.models.company import Company

    company = db.get(Company, company_code)
    if company is None or company.quality_check_required:
        order.status = PurchaseOrderStatus.QC_PENDING
        db.flush()

    activity.record(
        db,
        company_code=company_code,
        actor=actor,
        entity="purchase_order",
        action="received",
        entity_id=order.id,
        summary=f"Goods received on {order.number}",
        payload={
            "lines": {str(k): str(v) for k, v in requested.items()},
            "reference": payload.reference,
            "next_status": order.status.value,
        },
    )
    return order


def decide_quality(
    db: Session,
    company_code: str,
    actor: User,
    order: PurchaseOrder,
    payload: QualityDecisionRequest,
) -> PurchaseOrder:
    """Apply a Quality decision and, on approval, post the stock movement.

    Rejection returns the order to OPEN without touching inventory, which is
    the behaviour the vendor needs to see to rework or resupply.
    """
    if order.status not in QC_DECISION_STATES:
        raise WorkflowError(
            f"Quality can only decide on orders in QC_PENDING or RECEIVED, not {order.status.value}"
        )

    assert_allowed(PurchaseOrderStatus.QC_PENDING, actor)

    overrides = {line.line_id: line.status for line in (payload.lines or [])}

    stock_movements: list[dict[str, str]] = []
    rejected_lines: list[int] = []

    for line in order.lines:
        decision = overrides.get(line.id) or (
            QualityStatus.PASSED if payload.passed else QualityStatus.FAILED
        )

        if decision != QualityStatus.PASSED:
            rejected_lines.append(line.id)
            line.qc_status = decision
            continue

        # Post stock only once per line. `stock_posted` is the guard that stops
        # a repeated approval from inflating inventory.
        if not line.stock_posted:
            item = db.get(Item, line.item_id)
            if item is not None:
                item.stock = Decimal(item.stock) + Decimal(line.quantity)
                line.stock_posted = True
                stock_movements.append({"item": item.code, "qty": str(line.quantity)})

        line.qc_status = QualityStatus.PASSED

    # An approval only sticks when every line passed.
    all_passed = not rejected_lines
    order.status = PurchaseOrderStatus.QC_APPROVED if all_passed else PurchaseOrderStatus.OPEN

    db.flush()

    action = "qc_approved" if all_passed else "qc_rejected"
    summary = (
        f"Quality approved {order.number}"
        if all_passed
        else f"Quality rejected {order.number}"
    )

    activity.record(
        db,
        company_code=company_code,
        actor=actor,
        entity="purchase_order",
        action=action,
        entity_id=order.id,
        summary=summary,
        payload={
            "note": payload.note,
            "stock_movements": stock_movements,
            "rejected_lines": rejected_lines,
            "at": datetime.now(UTC).isoformat(),
        },
    )
    return order