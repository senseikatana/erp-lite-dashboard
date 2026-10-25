"""Admin purge endpoint tests."""

from __future__ import annotations

from datetime import date

from app.models import (
    ActivityEvent,
    Company,
    Customer,
    DemandLine,
    DemandSource,
    Item,
    PurchaseOrder,
    PurchaseOrderLine,
    Role,
    SalesOrder,
    SalesOrderLine,
    ShipmentRoute,
    User,
    Vendor,
)

PURGE = "/api/v1/admin/purge?company=TEST_CO"


def _populate(db) -> None:
    """Create one row of every business table for TEST_CO, plus a second tenant."""
    db.add(Company(code="OTHER_CO", name="Other Company"))
    db.flush()
    db.add(Item(company_code="OTHER_CO", code="OTH-1", description="Other item"))

    customer = Customer(company_code="TEST_CO", code="C1", name="Customer One")
    vendor = Vendor(company_code="TEST_CO", code="V1", name="Vendor One")
    item = Item(company_code="TEST_CO", code="I1", description="Item One")
    db.add_all([customer, vendor, item])
    db.flush()

    sales = SalesOrder(company_code="TEST_CO", number="SO-1", customer_id=customer.id)
    purchase = PurchaseOrder(company_code="TEST_CO", number="PO-1", vendor_id=vendor.id)
    db.add_all([sales, purchase])
    db.flush()

    db.add_all(
        [
            SalesOrderLine(order_id=sales.id, item_id=item.id, quantity=2, unit_price=10),
            PurchaseOrderLine(order_id=purchase.id, item_id=item.id, quantity=1, unit_cost=5),
            DemandLine(
                company_code="TEST_CO",
                item_id=item.id,
                required_date=date.today(),
                quantity_needed=1,
                source=DemandSource.MIN_STOCK,
            ),
            ActivityEvent(
                company_code="TEST_CO",
                actor_username="tester",
                entity="item",
                action="adjusted",
            ),
            ShipmentRoute(
                company_code="TEST_CO",
                code="R1",
                carrier="DHL",
                date=date.today(),
                stops=2,
            ),
        ]
    )
    db.commit()


def test_purge_requires_admin(client, auth, seeded):
    response = client.post(PURGE, headers=auth(Role.BUYER))
    assert response.status_code == 403


def test_purge_clears_only_the_active_company(client, auth, seeded, db):
    _populate(db)

    response = client.post(PURGE, headers=auth(Role.ADMIN))
    assert response.status_code == 200, response.text

    deleted = response.json()["deleted"]
    assert deleted == {
        "sales_order_lines": 1,
        "purchase_order_lines": 1,
        "demand_lines": 1,
        "activity_events": 1,
        "routes": 1,
        "sales_orders": 1,
        "purchase_orders": 1,
        "items": 1,
        "customers": 1,
        "vendors": 1,
    }

    # Accounts and the other tenant survive; only TEST_CO's business data goes.
    assert db.query(User).count() == 4
    assert db.query(Company).count() == 2
    assert db.query(Item).filter(Item.company_code == "OTHER_CO").count() == 1


def test_purge_leaves_empty_lists(client, auth, seeded, db):
    _populate(db)
    assert client.post(PURGE, headers=auth(Role.ADMIN)).status_code == 200

    headers = auth(Role.ADMIN)
    assert client.get("/api/v1/sales/orders", headers=headers).json()["items"] == []
    assert client.get("/api/v1/purchases/orders", headers=headers).json()["items"] == []
    assert client.get("/api/v1/warehouse/items", headers=headers).json()["items"] == []
    assert client.get("/api/v1/demand", headers=headers).json()["items"] == []
    assert client.get("/api/v1/routes", headers=headers).json()["items"] == []
    assert client.get("/api/v1/dashboard/activity", headers=headers).json() == []
