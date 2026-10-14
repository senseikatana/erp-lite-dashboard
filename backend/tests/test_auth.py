"""Authentication and authorisation tests.

These cover the security boundary: tenant isolation and role enforcement.
"""

from __future__ import annotations

from app.models import Company, Role, User, UserCompanyAccess
from tests.conftest import TEST_PASSWORD


def test_login_returns_token_and_user(client, seeded):
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": TEST_PASSWORD}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["role"] == "admin"
    assert body["active_company"] == "TEST_CO"


def test_login_rejects_wrong_password(client, seeded):
    response = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_login_does_not_leak_unknown_usernames(client, seeded):
    """An unknown user and a wrong password must be indistinguishable."""
    unknown = client.post(
        "/api/v1/auth/login", json={"username": "nobody", "password": "whatever"}
    )
    wrong = client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "whatever"}
    )
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]


def test_deactivated_user_cannot_use_a_valid_token(client, seeded, auth, db):
    """A token issued before deactivation must stop working."""
    header = auth(Role.ADMIN)
    assert client.get("/api/v1/auth/me", headers=header).status_code == 200

    db.query(User).filter(User.username == "admin").one().is_active = False
    db.commit()

    assert client.get("/api/v1/auth/me", headers=header).status_code == 401


def test_requests_without_a_token_are_rejected(client, seeded):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_user_cannot_read_another_companys_data(client, seeded, auth, db):
    """Tenant isolation: a non-admin without a grant gets 403, not data."""
    other = Company(code="OTHER_CO", name="Other Company")
    db.add(other)
    db.commit()

    response = client.get(
        "/api/v1/warehouse/items?company=OTHER_CO", headers=auth(Role.LOGISTICS)
    )
    assert response.status_code == 403


def test_admin_reaches_a_company_without_an_explicit_grant(client, seeded, auth, db):
    db.add(Company(code="OTHER_CO", name="Other Company"))
    db.commit()

    response = client.get("/api/v1/warehouse/items?company=OTHER_CO", headers=auth(Role.ADMIN))
    assert response.status_code == 200


def test_unknown_company_returns_404(client, seeded, auth):
    response = client.get("/api/v1/warehouse/items?company=NOPE", headers=auth(Role.ADMIN))
    assert response.status_code == 404


def test_grant_is_required_for_non_admin(client, seeded, auth, db):
    """Removing the last grant locks a non-admin out of that company."""
    db.query(UserCompanyAccess).delete()
    db.commit()

    response = client.get(
        "/api/v1/companies/current?company=TEST_CO", headers=auth(Role.BUYER)
    )
    assert response.status_code == 403