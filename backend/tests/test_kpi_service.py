"""KPI computation tests.

The behaviour under test is not only that numbers come out, but that they are
absent when they cannot be measured. A KPI rendered as zero asserts that work
did not happen, which is a worse lie than showing nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from app.models import ActivityEvent, Item, Role
from app.services import kpi_service

KPI_KEYS = {"order_accuracy", "picks_per_hour", "dock_to_stock", "inventory_turnover"}


def _event(db, occurred_at, action, payload=None, entity_id=None):
    db.add(
        ActivityEvent(
            company_code="TEST_CO",
            actor_username="tester",
            entity="sales_order" if action == "status_changed" else "purchase_order",
            entity_id=entity_id,
            action=action,
            occurred_at=occurred_at,
            payload=payload or {},
        )
    )


def test_every_kpi_is_returned_for_a_fresh_company(db, seeded):
    kpis = kpi_service.compute_all(db, "TEST_CO")
    assert {kpi.key for kpi in kpis} == KPI_KEYS


def test_kpis_are_null_when_nothing_has_been_recorded(db, seeded):
    """An empty installation reports no data, not zeros."""
    kpis = {kpi.key: kpi for kpi in kpi_service.compute_all(db, "TEST_CO")}

    assert kpis["order_accuracy"].value is None
    assert kpis["picks_per_hour"].value is None
    assert kpis["dock_to_stock"].value is None
    assert kpis["inventory_turnover"].value is None


def test_picks_per_hour_uses_the_activity_span(db, seeded):
    """Three picks in two hours is 1.5/h, not 3 divided by a month of hours."""
    now = datetime.now(UTC)

    _event(db, now - timedelta(hours=2), "status_changed", {"to": "PICKING"})
    _event(db, now - timedelta(hours=1), "status_changed", {"to": "PICKING"})
    _event(db, now, "status_changed", {"to": "PICKING"})
    db.commit()

    kpi = kpi_service.picks_per_hour(db, "TEST_CO")
    assert kpi.value == 1.5


def test_dock_to_stock_measures_receipt_to_approval(db, seeded):
    now = datetime.now(UTC)

    _event(db, now - timedelta(days=1), "received", entity_id=42)
    _event(db, now - timedelta(days=1, hours=-5), "qc_approved", entity_id=42)
    db.commit()

    kpi = kpi_service.dock_to_stock_hours(db, "TEST_CO")
    assert kpi.value == 5.0


def test_dock_to_stock_ignores_approvals_without_a_receipt(db, seeded):
    """An approval with no matching receipt is not a measurable cycle."""
    now = datetime.now(UTC)
    _event(db, now, "qc_approved", entity_id=99)
    db.commit()

    assert kpi_service.dock_to_stock_hours(db, "TEST_CO").value is None


def test_inventory_turnover_is_null_when_inventory_is_empty(db, seeded):
    assert kpi_service.inventory_turnover(db, "TEST_CO").value is None


def test_alerts_flag_stock_below_minimum(db, seeded):
    db.add(
        Item(
            company_code="TEST_CO",
            code="ART-LOW",
            description="Low stock item",
            unit_cost=Decimal("1.00"),
            unit_price=Decimal("2.00"),
            stock=Decimal("5"),
            min_stock=Decimal("10"),
        )
    )
    db.commit()

    alerts = kpi_service.alerts(db, "TEST_CO")
    assert any(alert["code"] == "ART-LOW" for alert in alerts)


def test_dashboard_endpoint_returns_computed_kpis(client, auth, seeded):
    header = auth(Role.ADMIN)
    response = client.get("/api/v1/dashboard/summary", headers=header)

    assert response.status_code == 200
    body = response.json()

    assert body["company_code"] == "TEST_CO"
    assert {kpi["key"] for kpi in body["kpis"]} == KPI_KEYS
    assert isinstance(body["inventory_value"], (int, float))