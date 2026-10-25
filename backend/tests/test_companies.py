"""Company listing tests."""

from __future__ import annotations

from app.models import Role


def test_admin_lists_every_company(client, auth, seeded):
    response = client.get("/api/v1/companies", headers=auth(Role.ADMIN))
    assert response.status_code == 200
    assert [company["code"] for company in response.json()] == ["TEST_CO"]


def test_non_admin_lists_only_granted_companies(client, auth, seeded):
    response = client.get("/api/v1/companies", headers=auth(Role.BUYER))
    assert response.status_code == 200, response.text
    assert [company["code"] for company in response.json()] == ["TEST_CO"]
