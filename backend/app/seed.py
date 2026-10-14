"""Seed the database with a demonstrable multi-company dataset.

Run with::

    python -m app.seed

The seed creates:

* two registered companies,
* one user per role, plus a per-role administrator,
* customers, vendors and items,
* sales and purchase orders spread over the last few weeks, and
* a **synthetic activity history** so the dashboard has something to measure.

About the synthetic history
---------------------------
The KPI service computes order accuracy, picks per hour, dock-to-stock and
inventory turnover from the activity log. A freshly created database has no
events, so every KPI would render as "no data" -- which is the honest state
of an empty installation.

To make the dashboard demonstrable, this seed backfills a plausible event
history. Those rows are generated, not measured. They are marked with the
actor name ``seed`` and a ``synthetic: true`` flag in the payload so they can
be told apart from real activity and stripped out later::

    python -m app.seed --reset-synthetic

Once real users start working, real measurements replace them.
"""

from __future__ import annotations

import argparse
import logging
import random
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, select

from app.core.database import Base, SessionLocal, engine
from app.models import (
    ActivityEvent,
    Company,
    Customer,
    DemandAction,
    DemandLine,
    DemandSource,
    Item,
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseOrderStatus,
    QualityStatus,
    Role,
    SalesOrder,
    SalesOrderLine,
    SalesOrderStatus,
    ShipmentRoute,
    User,
    UserCompanyAccess,
    Vendor,
)

logger = logging.getLogger("erp_lite.seed")

SEED_ACTOR = "seed"

DEMO_PASSWORD = "demo1234"

COMPANIES = [
    {
        "code": "DEMO_SL",
        "name": "Demo Logística S.L.",
        "currency": "EUR",
        "locale": "es_ES",
        "default_language": "es",
        "quality_check_required": True,
    },
    {
        "code": "ACME_SA",
        "name": "Acme Manufacturing S.A.",
        "currency": "EUR",
        "locale": "es_ES",
        "default_language": "es",
        "quality_check_required": False,
    },
]

# One account per role so every permission path can be exercised.
USERS = [
    {"username": "admin", "role": Role.ADMIN, "full_name": "Ada Admin", "companies": ["DEMO_SL", "ACME_SA"]},
    {"username": "buyer", "role": Role.BUYER, "full_name": "Bruno Buyer", "companies": ["DEMO_SL"]},
    {
        "username": "logistics",
        "role": Role.LOGISTICS,
        "full_name": "Lena Logistics",
        "companies": ["DEMO_SL"],
    },
    {"username": "quality", "role": Role.QUALITY, "full_name": "Quim Quality", "companies": ["DEMO_SL"]},
]

CUSTOMERS = [
    {"code": "C001", "name": "Supermercados Nordeste", "city": "Barcelona", "postal_code": "08001",
         "email": "compras@snordeste.example"},
    {"code": "C002", "name": "Distribuciones Girona", "city": "Girona", "postal_code": "17001",
         "email": "info@dgi.example"},
    {"code": "C003", "name": "Alimentación Lleida", "city": "Lleida", "postal_code": "25001"},
    {"code": "C004", "name": "Cadena Retail Costa", "city": "Tarragona", "postal_code": "43001"},
]

VENDORS = [
    {"code": "P001", "name": "Packaging Ibérica", "lead_time_days": 5, "quality_rating": 4.5},
    {"code": "P002", "name": "Metalúrgica Tarragona", "lead_time_days": 12, "quality_rating": 4.0},
    {"code": "P003", "name": "Plásticos del Vallès", "lead_time_days": 7, "quality_rating": 4.8},
    {"code": "P004", "name": "Cartonajes del Ebro", "lead_time_days": 9, "quality_rating": 4.2},
]

ITEMS = [
    {"code": "ART-001", "description": "Carton box 40x30x20", "unit": "EA", "unit_cost": "0.45",
         "unit_price": "0.85", "stock": "1200", "min_stock": "300", "location": "A-01", "category": "Packaging"},
    {"code": "ART-002", "description": "Shrink film 50cm", "unit": "ROLL", "unit_cost": "8.20",
         "unit_price": "14.50", "stock": "45", "min_stock": "20", "location": "B-03", "category": "Packaging"},
    {"code": "ART-003", "description": "Euro pallet wood", "unit": "EA", "unit_cost": "12.00",
         "unit_price": "20.00", "stock": "80", "min_stock": "50", "location": "C-01", "category": "Logistics"},
    {"code": "ART-004", "description": "Adhesive label 100x50", "unit": "THOUS", "unit_cost": "6.50",
         "unit_price": "12.00", "stock": "15", "min_stock": "10", "location": "A-02", "category": "Labelling"},
    {"code": "ART-005", "description": "Plastic corner guard", "unit": "EA", "unit_cost": "0.15",
         "unit_price": "0.35", "stock": "2400", "min_stock": "500", "location": "D-02", "category": "Packaging"},
    {"code": "ART-006", "description": "Strapping band 12mm", "unit": "ROLL", "unit_cost": "3.40",
         "unit_price": "6.90", "stock": "18", "min_stock": "40", "location": "D-01", "category": "Packaging"},
    {"code": "ART-007", "description": "Pallet wrap 500m", "unit": "ROLL", "unit_cost": "9.10",
         "unit_price": "16.00", "stock": "60", "min_stock": "25", "location": "B-01", "category": "Packaging"},
]


def create_companies(db) -> None:
    for spec in COMPANIES:
        if db.get(Company, spec["code"]) is None:
            db.add(Company(**spec))
    db.commit()


def create_users(db) -> None:
    for spec in USERS:
        user = db.scalar(select(User).where(User.username == spec["username"]))
        if user is None:
            user = User(
                username=spec["username"],
                email=f"{spec['username']}@erp-lite.example",
                full_name=spec["full_name"],
                role=spec["role"],
            )
            user.set_password(DEMO_PASSWORD)
            db.add(user)
            db.flush()

        # `user.companies` resolves through the secondary table and yields
        # Company rows, so the grant check compares on the company code.
        existing = {company.code for company in user.companies}
        for code in spec["companies"]:
            if code not in existing:
                db.add(UserCompanyAccess(user_id=user.id, company_code=code))

    db.commit()


def create_master_data(db, company_code: str) -> None:
    if db.scalar(select(Customer).where(Customer.company_code == company_code)):
        return

    for spec in CUSTOMERS:
        db.add(Customer(company_code=company_code, **spec))
    for spec in VENDORS:
        db.add(Vendor(company_code=company_code, **spec))
    for spec in ITEMS:
        db.add(Item(company_code=company_code, **spec))

    db.commit()


def _synthetic_event(
    db,
    company_code: str,
    entity: str,
    action: str,
    occurred_at: datetime,
    *,
    entity_id: int | None = None,
    summary: str | None = None,
    payload: dict | None = None,
) -> None:
    """Append a clearly-labelled generated event."""
    body = {"synthetic": True}
    body.update(payload or {})
    db.add(
        ActivityEvent(
            company_code=company_code,
            actor_id=None,
            actor_username=SEED_ACTOR,
            entity=entity,
            entity_id=entity_id,
            action=action,
            summary=summary,
            payload=body,
            occurred_at=occurred_at,
        )
    )


def create_orders(db, company_code: str, days: int = 30) -> None:
    """Create orders with a backfilled activity history.

    Sales orders are spread across ``days`` so the dashboard trend has shape.
    Purchase orders are left deliberately in a few different workflow states
    so every screen has something to show.
    """
    if db.scalar(select(SalesOrder).where(SalesOrder.company_code == company_code)):
        return

    rng = random.Random(f"{company_code}-seed")
    customers = db.scalars(select(Customer).where(Customer.company_code == company_code)).all()
    vendors = db.scalars(select(Vendor).where(Vendor.company_code == company_code)).all()
    items = db.scalars(select(Item).where(Item.company_code == company_code)).all()

    if not customers or not items:
        return

    now = datetime.now(UTC)

    # --- Historical sales orders ---
    for index in range(1, 31):
        order_day = now - timedelta(days=index)
        customer = rng.choice(customers)
        line_count = rng.randint(1, 3)

        order = SalesOrder(
            company_code=company_code,
            number=f"SO-{order_day.year}-{index:04d}",
            customer_id=customer.id,
            order_date=order_day.date(),
            delivery_date=(order_day + timedelta(days=rng.randint(1, 5))).date(),
            status=SalesOrderStatus.OPEN,
        )

        for item in rng.sample(items, min(line_count, len(items))):
            quantity = rng.choice([50, 100, 200, 500, 1000])
            order.lines.append(
                SalesOrderLine(
                    item_id=item.id,
                    quantity=quantity,
                    unit_price=item.unit_price,
                )
            )
        order.recalculate_total()

        # Older orders have progressed further through the workflow.
        if index <= 20:
            status_sequence = [SalesOrderStatus.SHIPPED, SalesOrderStatus.INVOICED]
        elif index <= 26:
            status_sequence = [SalesOrderStatus.PICKING]
        else:
            status_sequence = []

        db.add(order)
        db.flush()

        _synthetic_event(
            db, company_code, "sales_order", "created", order_day,
            entity_id=order.id, summary=f"Created sales order {order.number}",
        )

        previous = SalesOrderStatus.OPEN
        cursor = order_day
        for target in status_sequence:
            cursor += timedelta(hours=rng.uniform(0.5, 6))

            for line in order.lines:
                if target in (SalesOrderStatus.PICKING,):
                    line.qty_picked = line.quantity
                if target in (SalesOrderStatus.SHIPPED, SalesOrderStatus.INVOICED):
                    line.qty_shipped = line.quantity

            _synthetic_event(
                db, company_code, "sales_order", "status_changed", cursor,
                entity_id=order.id,
                summary=f"{previous.value} -> {target.value}",
                payload={"from": previous.value, "to": target.value},
            )
            order.status = target
            previous = target

    db.commit()

    # --- Purchase orders, spread across workflow states ---
    if vendors:
        po_states = [
            PurchaseOrderStatus.OPEN,
            PurchaseOrderStatus.QC_PENDING,
            PurchaseOrderStatus.QC_APPROVED,
            PurchaseOrderStatus.OPEN,
        ]
        for index, po_status in enumerate(po_states, start=1):
            vendor = vendors[index % len(vendors)]
            order_day = now - timedelta(days=index * 2)
            expected = order_day + timedelta(days=vendor.lead_time_days)

            po = PurchaseOrder(
                company_code=company_code,
                number=f"PO-{order_day.year}-{index:04d}",
                vendor_id=vendor.id,
                order_date=order_day.date(),
                expected_date=expected.date(),
                status=PurchaseOrderStatus.OPEN,
            )
            for item in rng.sample(items, 2):
                po.lines.append(
                    PurchaseOrderLine(
                        item_id=item.id,
                        quantity=rng.choice([100, 250, 500]),
                        unit_cost=item.unit_cost,
                    )
                )
            po.recalculate_total()

            db.add(po)
            db.flush()

            _synthetic_event(
                db, company_code, "purchase_order", "created", order_day,
                entity_id=po.id, summary=f"Created purchase order {po.number}",
            )

            if po_status in (PurchaseOrderStatus.QC_PENDING, PurchaseOrderStatus.QC_APPROVED):
                received_at = order_day + timedelta(days=vendor.lead_time_days, hours=2)
                for line in po.lines:
                    line.qty_received = line.quantity
                    line.qc_status = QualityStatus.PASSED if po_status == PurchaseOrderStatus.QC_APPROVED else QualityStatus.PENDING
                    line.stock_posted = po_status == PurchaseOrderStatus.QC_APPROVED

                po.status = po_status
                _synthetic_event(
                    db, company_code, "purchase_order", "received", received_at,
                    entity_id=po.id, summary=f"Goods received on {po.number}",
                    payload={"next_status": PurchaseOrderStatus.QC_PENDING.value},
                )

                if po_status == PurchaseOrderStatus.QC_APPROVED:
                    approved_at = received_at + timedelta(hours=rng.uniform(1.5, 9.0))
                    _synthetic_event(
                        db, company_code, "purchase_order", "qc_approved", approved_at,
                        entity_id=po.id, summary=f"Quality approved {po.number}",
                        payload={"stock_movements": []},
                    )

        db.commit()

    # --- Demand worksheet ---
    below_minimum = db.scalars(
        select(Item).where(Item.company_code == company_code, Item.stock < Item.min_stock * 1.5)
    ).all()

    for item in below_minimum:
        db.add(
            DemandLine(
                company_code=company_code,
                item_id=item.id,
                required_date=(now + timedelta(days=7)).date(),
                quantity_needed=max(item.min_stock * 2 - item.stock, 0),
                source=DemandSource.MIN_STOCK,
                action=DemandAction.PENDING,
            )
        )

    db.commit()


def create_routes(db, company_code: str) -> None:
    if db.scalar(select(ShipmentRoute).where(ShipmentRoute.company_code == company_code)):
        return

    from app.models.routing import RouteStatus

    today = date.today()
    specs = [
        ("RT-001", "SEUR", today, RouteStatus.PLANNED, 4),
        ("RT-002", "DHL", today, RouteStatus.IN_TRANSIT, 3),
        ("RT-003", "In-house", today + timedelta(days=1), RouteStatus.PLANNED, 6),
        ("RT-004", "SEUR", today + timedelta(days=1), RouteStatus.PLANNED, 2),
    ]

    for code, carrier, day, status, stops in specs:
        db.add(
            ShipmentRoute(
                company_code=company_code,
                code=code,
                carrier=carrier,
                date=day,
                status=status,
                stops=stops,
            )
        )
    db.commit()


def reset_synthetic_activity() -> int:
    """Delete generated activity rows, leaving real ones untouched."""
    with SessionLocal() as db:
        result = db.execute(
            delete(ActivityEvent).where(ActivityEvent.actor_username == SEED_ACTOR)
        )
        db.commit()
        return result.rowcount or 0


def seed_all(reset: bool = False) -> None:
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        create_companies(db)
        create_users(db)
        for spec in COMPANIES:
            code = spec["code"]
            create_master_data(db, code)
            create_orders(db, code)
            create_routes(db, code)

    if reset:
        removed = reset_synthetic_activity()
        logger.info("Removed %s synthetic activity events", removed)

    with SessionLocal() as db:
        counts = {
            "companies": db.query(Company).count(),
            "users": db.query(User).count(),
            "customers": db.query(Customer).count(),
            "items": db.query(Item).count(),
            "sales_orders": db.query(SalesOrder).count(),
            "purchase_orders": db.query(PurchaseOrder).count(),
            "activity_events": db.query(ActivityEvent).count(),
        }

    print("\nSeed complete")
    for key, value in counts.items():
        print(f"  {key:<18} {value}")
    print(f"\nSign in with any of: {', '.join(u['username'] for u in USERS)}")
    print(f"Password for all seeded accounts: {DEMO_PASSWORD}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the ERP-Lite database")
    parser.add_argument(
        "--reset-synthetic",
        action="store_true",
        help="Remove generated activity events after seeding",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    seed_all(reset=args.reset_synthetic)


if __name__ == "__main__":
    main()