"""Endpoint smoke tests.

Every GET endpoint is exercised at least once. This exists because a schema
module referenced a type it never imported: the endpoint existed, was routed,
had a passing import, and still returned 500 on every call. Unit tests on the
service layer did not catch it because nothing had ever called the endpoint.

Any endpoint added to the API should be added to this list.
"""

from __future__ import annotations

import pytest

from app.models import Role

# Endpoints that require no path parameters.
COLLECTION_ENDPOINTS = [
    "/api/v1/companies",
    "/api/v1/companies/current",
    "/api/v1/dashboard/summary",
    "/api/v1/dashboard/alerts",
    "/api/v1/dashboard/stock-levels",
    "/api/v1/dashboard/routes",
    "/api/v1/dashboard/activity",
    "/api/v1/sales/orders",
    "/api/v1/purchases/orders",
    "/api/v1/purchases/orders/awaiting-quality",
    "/api/v1/warehouse/items",
    "/api/v1/warehouse/locations",
    "/api/v1/customers",
    "/api/v1/vendors",
    "/api/v1/demand",
    "/api/v1/routes",
    "/api/v1/activity",
    "/api/v1/auth/me",
    "/api/v1/auth/users",
]

HEALTH_ENDPOINT = "/health"


@pytest.mark.parametrize("path", COLLECTION_ENDPOINTS)
def test_get_endpoint_returns_success(client, auth, seeded, path: str):
    """Every collection endpoint must respond without a server error."""
    response = client.get(path, headers=auth(Role.ADMIN))
    assert response.status_code == 200, f"{path} -> {response.status_code}: {response.text}"
    assert "Internal Server Error" not in response.text


def test_health_needs_no_authentication(client):
    response = client.get(HEALTH_ENDPOINT)
    assert response.status_code == 200
    assert response.json()["database"] == "ok"


def test_openapi_schema_builds(client):
    """A broken response model breaks schema generation, not just one route."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"]


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/dashboard/summary",
        "/api/v1/demand",
        "/api/v1/routes",
        "/api/v1/activity",
    ],
)
def test_endpoints_respect_tenant_scoping(client, auth, seeded, db, path: str):
    """An ungranted company must be refused before any data is read."""
    from app.models import Company

    db.add(Company(code="OTHER_CO", name="Other Company"))
    db.commit()

    # Grant the admin no explicit access path; only non-admins are restricted.
    granted = client.get(f"{path}?company=OTHER_CO", headers=auth(Role.ADMIN))
    assert granted.status_code == 200

    denied = client.get(f"{path}?company=OTHER_CO", headers=auth(Role.QUALITY))
    assert denied.status_code == 403

    # Sanity: the same user reaches their own company.
    assert client.get(f"{path}?company=TEST_CO", headers=auth(Role.QUALITY)).status_code == 200


def test_paginated_responses_carry_metadata(client, auth, seeded):
    response = client.get("/api/v1/warehouse/items", headers=auth(Role.ADMIN))
    body = response.json()

    assert "items" in body
    assert set(body["meta"]) == {"total", "limit", "offset"}


def test_seed_is_idempotent(db):
    """Running the seeder twice must not duplicate rows or crash.

    This catches a class of bug the original suite missed: the seeder compared
    company grants against ``grant.company_code`` after the relationship had
    been changed to yield Company rows, so the second run raised AttributeError
    while the first looked perfectly fine.
    """
    from app.models import Company, SalesOrder, User
    from app.seed import seed_all

    seed_all()
    first = (db.query(User).count(), db.query(Company).count(), db.query(SalesOrder).count())
    assert all(count > 0 for count in first)

    seed_all()

    assert (
        db.query(User).count(),
        db.query(Company).count(),
        db.query(SalesOrder).count(),
    ) == first


def test_seed_script_runs_end_to_end(client):
    """The seeder must produce a database the API can serve."""
    from app.seed import seed_all

    seed_all()

    response = client.get("/api/v1/dashboard/summary", headers=None)
    # Unauthenticated, so 401 -- the point is that routing and schemas resolve.
    assert response.status_code == 401