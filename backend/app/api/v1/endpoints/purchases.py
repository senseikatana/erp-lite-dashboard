"""Purchase order, receipt and quality control endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentCompany, CurrentUser, DbSession, PageParams, paginate
from app.models.purchasing import PurchaseOrder, PurchaseOrderStatus
from app.schemas.common import Page, PageMeta
from app.schemas.purchasing import (
    PurchaseOrderCreate,
    PurchaseOrderRead,
    QualityDecisionRequest,
    ReceiptRequest,
)
from app.services import purchasing_service

router = APIRouter(prefix="/purchases/orders", tags=["purchases"])


def _load(db, company_code: str, order_id: int) -> PurchaseOrder:
    order = db.scalar(
        select(PurchaseOrder).where(
            PurchaseOrder.id == order_id,
            PurchaseOrder.company_code == company_code,
        )
    )
    if order is None:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return order


@router.get("", response_model=Page[PurchaseOrderRead])
def list_orders(
    db: DbSession,
    company: CurrentCompany,
    page: PageParams,
    status_filter: list[PurchaseOrderStatus] | None = Query(default=None, alias="status"),
) -> Page[PurchaseOrderRead]:
    """List purchase orders, optionally filtered by status."""
    query = select(PurchaseOrder).where(PurchaseOrder.company_code == company.code)

    if status_filter:
        query = query.where(PurchaseOrder.status.in_(status_filter))

    query = query.order_by(PurchaseOrder.order_date.desc(), PurchaseOrder.id.desc())

    rows, total = paginate(db, query, page)
    return Page[PurchaseOrderRead](
        items=[PurchaseOrderRead.model_validate(row) for row in rows],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )


@router.get("/awaiting-quality", response_model=Page[PurchaseOrderRead])
def awaiting_quality(
    db: DbSession, company: CurrentCompany, page: PageParams
) -> Page[PurchaseOrderRead]:
    """Quality queue: orders received but not yet approved."""
    query = (
        select(PurchaseOrder)
        .where(PurchaseOrder.company_code == company.code)
        .where(PurchaseOrder.status == PurchaseOrderStatus.QC_PENDING)
        .order_by(PurchaseOrder.expected_date.asc())
    )
    rows, total = paginate(db, query, page)
    return Page[PurchaseOrderRead](
        items=[PurchaseOrderRead.model_validate(row) for row in rows],
        meta=PageMeta(total=total, limit=page.limit, offset=page.offset),
    )


@router.get("/{order_id}", response_model=PurchaseOrderRead)
def read_order(order_id: int, db: DbSession, company: CurrentCompany) -> PurchaseOrder:
    return _load(db, company.code, order_id)


@router.post("", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: PurchaseOrderCreate, db: DbSession, user: CurrentUser, company: CurrentCompany
) -> PurchaseOrder:
    """Raise a purchase order.

    Restricted to buyers and administrators; the service raises
    ``WorkflowError`` otherwise.
    """
    try:
        order = purchasing_service.create_order(db, company.code, user, payload)
    except purchasing_service.WorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/receive", response_model=PurchaseOrderRead)
def receive_goods(
    order_id: int,
    payload: ReceiptRequest,
    db: DbSession,
    user: CurrentUser,
    company: CurrentCompany,
) -> PurchaseOrder:
    """Book a goods receipt.

    Receiving does not increase stock. When the company requires a quality
    check the order moves to QC_PENDING and waits for a Quality decision.
    """
    order = _load(db, company.code, order_id)

    try:
        purchasing_service.receive(db, company.code, user, order, payload)
    except purchasing_service.WorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    db.refresh(order)
    return order


@router.post("/{order_id}/quality", response_model=PurchaseOrderRead)
def quality_decision(
    order_id: int,
    payload: QualityDecisionRequest,
    db: DbSession,
    user: CurrentUser,
    company: CurrentCompany,
) -> PurchaseOrder:
    """Approve or reject received goods.

    Approval posts the received quantities to item stock exactly once. A
    rejection returns the order to OPEN without touching inventory.
    """
    order = _load(db, company.code, order_id)

    try:
        purchasing_service.decide_quality(db, company.code, user, order, payload)
    except purchasing_service.WorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    db.commit()
    db.refresh(order)
    return order