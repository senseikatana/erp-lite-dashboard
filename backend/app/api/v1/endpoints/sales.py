"""Sales order endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentCompany, CurrentUser, DbSession, PageParams, paginate
from app.models.sales import SalesOrder, SalesOrderStatus
from app.schemas.common import Message, Page, PageMeta
from app.schemas.sales import SalesOrderCreate, SalesOrderRead, StatusChange
from app.services import sales_service

router = APIRouter(prefix="/sales/orders", tags=["sales"])


def _load(db, company_code: str, order_id: int) -> SalesOrder:
    """Fetch an order scoped to a company.

    Scoping the lookup by company code is what stops a user who knows an ID
    from another tenant reading it.
    """
    order = db.scalar(
        select(SalesOrder).where(
            SalesOrder.id == order_id,
            SalesOrder.company_code == company_code,
        )
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Sales order not found")
    return order


@router.get("", response_model=Page[SalesOrderRead])
def list_orders(
    db: DbSession,
    company: CurrentCompany,
    page: PageParams,
    status_filter: list[SalesOrderStatus] | None = Query(default=None, alias="status"),
) -> Page[SalesOrderRead]:
    """List sales orders, optionally filtered by status."""
    query = select(SalesOrder).where(SalesOrder.company_code == company.code)

    if status_filter:
        query = query.where(SalesOrder.status.in_(status_filter))

    query = query.order_by(SalesOrder.order_date.desc(), SalesOrder.id.desc())

    rows, total = paginate(db, query, page)
    return Page[SalesOrderRead](
        items=[SalesOrderRead.model_validate(row) for row in rows],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )


@router.get("/{order_id}", response_model=SalesOrderRead)
def read_order(order_id: int, db: DbSession, company: CurrentCompany) -> SalesOrder:
    return _load(db, company.code, order_id)


@router.post("", response_model=SalesOrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: SalesOrderCreate, db: DbSession, user: CurrentUser, company: CurrentCompany
) -> SalesOrder:
    """Create a sales order."""
    if payload.customer_id <= 0:
        raise HTTPException(status_code=400, detail="customer_id is required")

    order = sales_service.create_order(db, company.code, user, payload)
    db.commit()
    db.refresh(order)
    return order


@router.patch("/{order_id}/status", response_model=SalesOrderRead)
def change_status(
    order_id: int,
    payload: StatusChange,
    db: DbSession,
    user: CurrentUser,
    company: CurrentCompany,
) -> SalesOrder:
    """Advance an order through its workflow.

    Both the transition graph and the caller's role are checked server-side. A
    rejected transition returns 409 with the reason.
    """
    order = _load(db, company.code, order_id)

    try:
        sales_service.change_status(db, company.code, user, order, payload)
    except sales_service.TransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    db.refresh(order)
    return order


@router.delete("/{order_id}", response_model=Message)
def cancel_order(
    order_id: int, db: DbSession, user: CurrentUser, company: CurrentCompany
) -> Message:
    """Cancel an order that has not been invoiced."""
    order = _load(db, company.code, order_id)

    if order.status in {SalesOrderStatus.INVOICED, SalesOrderStatus.CANCELLED}:
        raise HTTPException(
            status_code=409, detail=f"An order in status {order.status.value} cannot be cancelled"
        )

    payload = StatusChange(status=SalesOrderStatus.CANCELLED)
    try:
        sales_service.change_status(db, company.code, user, order, payload)
    except sales_service.TransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    return Message(message=f"Order {order.number} cancelled")