"""Sales order workflow and role enforcement tests."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models import Item, Role


@pytest.fixture
def catalogue(db):
    """One customer and two items to build orders from."""
    from app.models import Customer

    customer = Customer(company_code="TEST_CO", code="C001", name="Acme Client")
    db.add(customer)
    db.flush()

    items = [
        Item(
            company_code="TEST_CO",
            code="ART-1",
            description="Widget",
            unit_cost=Decimal("1.00"),
            unit_price=Decimal("2.00"),
            stock=Decimal("1000"),
        ),
        Item(
            company_code="TEST_CO",
            code="ART-2",
            description="Gadget",
            unit_cost=Decimal("3.00"),
            unit_price=Decimal("5.00"),
            stock=Decimal("1000"),
        ),
    ]
    db.add_all(items)
    db.commit()

    return {"customer": customer, "items": items}


def _create_order(client, header, customer_id):
    response = client.post(
        "/api/v1/sales/orders",
        headers=header,
        json={
            "customer_id": customer_id,
            "lines": [{"item_id": 1, "quantity": 10, "unit_price": "2.00"}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_order_total_is_computed_from_lines(client, auth, seeded, catalogue):
    header = auth(Role.ADMIN)
    order = _create_order(client, header, catalogue["customer"].id)
    assert order["total"] == 20.0


def test_happy_path_reaches_invoiced(client, auth, seeded, catalogue):
    header = auth(Role.ADMIN)
    order = _create_order(client, header, catalogue["customer"].id)
    order_id = order["id"]

    for status in ("PICKING", "SHIPPED", "INVOICED"):
        response = client.patch(
            f"/api/v1/sales/orders/{order_id}/status",
            headers=header,
            json={"status": status},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status


def test_skipping_a_step_is_rejected(client, auth, seeded, catalogue):
    """OPEN -> SHIPPED skips PICKING and must not be allowed."""
    header = auth(Role.ADMIN)
    order = _create_order(client, header, catalogue["customer"].id)

    response = client.patch(
        f"/api/v1/sales/orders/{order['id']}/status",
        headers=header,
        json={"status": "SHIPPED"},
    )
    assert response.status_code == 409


def test_buyer_cannot_start_picking(client, auth, seeded, catalogue):
    """Purchasing may raise orders but must not fulfil them."""
    header = auth(Role.BUYER)
    order = _create_order(client, header, catalogue["customer"].id)

    response = client.patch(
        f"/api/v1/sales/orders/{order['id']}/status",
        headers=header,
        json={"status": "PICKING"},
    )
    assert response.status_code == 409
    assert "buyer" in response.json()["detail"]


def test_logistics_cannot_invoice(client, auth, seeded, catalogue):
    header = auth(Role.LOGISTICS)
    order = _create_order(client, header, catalogue["customer"].id)

    client.patch(
        f"/api/v1/sales/orders/{order['id']}/status", headers=header, json={"status": "PICKING"}
    )
    client.patch(
        f"/api/v1/sales/orders/{order['id']}/status", headers=header, json={"status": "SHIPPED"}
    )

    response = client.patch(
        f"/api/v1/sales/orders/{order['id']}/status",
        headers=header,
        json={"status": "INVOICED"},
    )
    assert response.status_code == 409


def test_picking_sets_line_progress(client, auth, seeded, catalogue):
    header = auth(Role.LOGISTICS)
    order = _create_order(client, auth(Role.ADMIN), catalogue["customer"].id)

    client.patch(
        f"/api/v1/sales/orders/{order['id']}/status", headers=header, json={"status": "PICKING"}
    )

    detail = client.get(f"/api/v1/sales/orders/{order['id']}", headers=header).json()
    assert detail["lines"][0]["qty_picked"] == 10.0


def test_status_change_is_recorded_in_the_activity_log(client, auth, seeded, catalogue):
    header = auth(Role.ADMIN)
    order = _create_order(client, header, catalogue["customer"].id)

    client.patch(
        f"/api/v1/sales/orders/{order['id']}/status", headers=header, json={"status": "PICKING"}
    )

    events = client.get("/api/v1/activity?entity=sales_order", headers=header).json()
    actions = [event["action"] for event in events["items"]]

    assert "created" in actions
    assert "status_changed" in actions

    change = next(e for e in events["items"] if e["action"] == "status_changed")
    assert change["payload"]["to"] == "PICKING"
    assert change["actor_username"] == "admin"


def test_order_in_another_company_is_not_readable(client, auth, seeded, catalogue, db):
    """Knowing an ID from another tenant must not leak the record."""
    from app.models import Company, Customer, SalesOrder

    other = Company(code="OTHER_CO", name="Other")
    db.add(other)
    db.flush()

    hidden_customer = Customer(company_code="OTHER_CO", code="C999", name="Hidden")
    db.add(hidden_customer)
    db.flush()

    hidden_order = SalesOrder(
        company_code="OTHER_CO",
        number="SO-2024-9999",
        customer_id=hidden_customer.id,
        status="OPEN",
    )
    hidden_order.lines.append(
        __import__("app.models", fromlist=["SalesOrderLine"]).SalesOrderLine(
            item_id=catalogue["items"][0].id, quantity=1, unit_price=Decimal("2.00")
        )
    )
    db.add(hidden_order)
    db.commit()

    response = client.get(
        f"/api/v1/sales/orders/{hidden_order.id}?company=OTHER_CO", headers=auth(Role.ADMIN)
    )
    assert response.status_code == 200  # admin has access

    # A user with no grant for OTHER_CO gets 403 from the dependency before
    # the row is ever read.
    denied = client.get(
        f"/api/v1/sales/orders/{hidden_order.id}?company=OTHER_CO", headers=auth(Role.LOGISTICS)
    )
    assert denied.status_code == 403


def test_order_requires_at_least_one_line(client, auth, seeded, catalogue):
    response = client.post(
        "/api/v1/sales/orders",
        headers=auth(Role.ADMIN),
        json={"customer_id": catalogue["customer"].id, "lines": []},
    )
    assert response.status_code == 422