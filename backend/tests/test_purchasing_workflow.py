"""Purchase order, receipt and quality control tests.

The regression that matters here is stock being posted twice by a repeated
Quality approval.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.models import Item, Role, Vendor


@pytest.fixture
def purchasing_setup(db):
    vendor = Vendor(company_code="TEST_CO", code="P001", name="Supplier")
    db.add(vendor)
    db.flush()

    item = Item(
        company_code="TEST_CO",
        code="ART-1",
        description="Widget",
        unit_cost=Decimal("2.00"),
        unit_price=Decimal("4.00"),
        stock=Decimal("0"),
        min_stock=Decimal("0"),
    )
    db.add(item)
    db.commit()

    return {"vendor": vendor, "item": item}


def _raise_order(client, header, vendor_id, item_id, quantity=100):
    response = client.post(
        "/api/v1/purchases/orders",
        headers=header,
        json={
            "vendor_id": vendor_id,
            "lines": [{"item_id": item_id, "quantity": quantity, "unit_cost": "2.00"}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_receipt_does_not_increase_stock(client, auth, seeded, purchasing_setup):
    """Goods are invisible to inventory until Quality accepts them."""
    buyer = auth(Role.BUYER)
    logistics = auth(Role.LOGISTICS)

    order = _raise_order(
        client, buyer, purchasing_setup["vendor"].id, purchasing_setup["item"].id
    )

    response = client.post(
        f"/api/v1/purchases/orders/{order['id']}/receive", headers=logistics, json={}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "QC_PENDING"

    item = client.get(
        f"/api/v1/warehouse/items/{purchasing_setup['item'].id}", headers=logistics
    ).json()
    assert item["stock"] == 0.0


def test_quality_approval_posts_stock(client, auth, seeded, purchasing_setup):
    buyer = auth(Role.BUYER)
    logistics = auth(Role.LOGISTICS)
    quality = auth(Role.QUALITY)

    order = _raise_order(
        client, buyer, purchasing_setup["vendor"].id, purchasing_setup["item"].id
    )
    client.post(f"/api/v1/purchases/orders/{order['id']}/receive", headers=logistics, json={})
    client.post(
        f"/api/v1/purchases/orders/{order['id']}/quality",
        headers=quality,
        json={"passed": True},
    )

    item = client.get(
        f"/api/v1/warehouse/items/{purchasing_setup['item'].id}", headers=logistics
    ).json()
    assert item["stock"] == 100.0


def test_repeat_approval_does_not_inflate_stock(client, auth, seeded, purchasing_setup):
    """The original prototype added stock on every click.

    A double-approved receipt must leave inventory untouched.
    """
    buyer = auth(Role.BUYER)
    logistics = auth(Role.LOGISTICS)
    quality = auth(Role.QUALITY)

    order = _raise_order(
        client, buyer, purchasing_setup["vendor"].id, purchasing_setup["item"].id
    )
    client.post(f"/api/v1/purchases/orders/{order['id']}/receive", headers=logistics, json={})

    for _ in range(3):
        client.post(
            f"/api/v1/purchases/orders/{order['id']}/quality",
            headers=quality,
            json={"passed": True},
        )

    item = client.get(
        f"/api/v1/warehouse/items/{purchasing_setup['item'].id}", headers=logistics
    ).json()
    assert item["stock"] == 100.0


def test_logistics_cannot_approve_quality(client, auth, seeded, purchasing_setup):
    """Receiving and inspecting are separate duties."""
    buyer = auth(Role.BUYER)
    logistics = auth(Role.LOGISTICS)

    order = _raise_order(
        client, buyer, purchasing_setup["vendor"].id, purchasing_setup["item"].id
    )
    client.post(f"/api/v1/purchases/orders/{order['id']}/receive", headers=logistics, json={})

    response = client.post(
        f"/api/v1/purchases/orders/{order['id']}/quality",
        headers=logistics,
        json={"passed": True},
    )
    assert response.status_code == 409


def test_rejection_leaves_stock_untouched(client, auth, seeded, purchasing_setup):
    buyer = auth(Role.BUYER)
    logistics = auth(Role.LOGISTICS)
    quality = auth(Role.QUALITY)

    order = _raise_order(
        client, buyer, purchasing_setup["vendor"].id, purchasing_setup["item"].id
    )
    client.post(f"/api/v1/purchases/orders/{order['id']}/receive", headers=logistics, json={})

    response = client.post(
        f"/api/v1/purchases/orders/{order['id']}/quality",
        headers=quality,
        json={"passed": False, "note": "Damaged pallet"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "OPEN"

    item = client.get(
        f"/api/v1/warehouse/items/{purchasing_setup['item'].id}", headers=logistics
    ).json()
    assert item["stock"] == 0.0


def test_quality_queue_lists_pending_orders(client, auth, seeded, purchasing_setup):
    buyer = auth(Role.BUYER)
    logistics = auth(Role.LOGISTICS)
    quality = auth(Role.QUALITY)

    order = _raise_order(
        client, buyer, purchasing_setup["vendor"].id, purchasing_setup["item"].id
    )
    client.post(f"/api/v1/purchases/orders/{order['id']}/receive", headers=logistics, json={})

    queue = client.get("/api/v1/purchases/orders/awaiting-quality", headers=quality).json()
    assert queue["meta"]["total"] == 1
    assert queue["items"][0]["number"] == order["number"]


def test_receiving_an_already_approved_order_is_rejected(
    client, auth, seeded, purchasing_setup
):
    buyer = auth(Role.BUYER)
    logistics = auth(Role.LOGISTICS)
    quality = auth(Role.QUALITY)

    order = _raise_order(
        client, buyer, purchasing_setup["vendor"].id, purchasing_setup["item"].id
    )
    client.post(f"/api/v1/purchases/orders/{order['id']}/receive", headers=logistics, json={})
    client.post(
        f"/api/v1/purchases/orders/{order['id']}/quality",
        headers=quality,
        json={"passed": True},
    )

    response = client.post(
        f"/api/v1/purchases/orders/{order['id']}/receive", headers=logistics, json={}
    )
    assert response.status_code == 409


def test_stock_adjustment_is_logged(client, auth, seeded, purchasing_setup):
    logistics = auth(Role.LOGISTICS)

    response = client.post(
        f"/api/v1/warehouse/items/{purchasing_setup['item'].id}/adjust",
        headers=logistics,
        json={"quantity": "25", "reason": "Stock recount"},
    )
    assert response.status_code == 200
    assert response.json()["stock"] == 25.0

    events = client.get("/api/v1/activity?entity=item", headers=logistics).json()
    adjustment = events["items"][0]
    assert adjustment["action"] == "stock_adjusted"
    assert adjustment["payload"]["reason"] == "Stock recount"


def test_adjustment_below_zero_is_rejected(client, auth, seeded, purchasing_setup):
    response = client.post(
        f"/api/v1/warehouse/items/{purchasing_setup['item'].id}/adjust",
        headers=auth(Role.LOGISTICS),
        json={"quantity": "-5", "reason": "Correction"},
    )
    assert response.status_code == 400