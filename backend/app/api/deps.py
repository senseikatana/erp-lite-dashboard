"""Shared FastAPI dependencies: authentication, tenancy and pagination."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.company import Company
from app.models.user import Role, User

# The token URL is declared so FastAPI can render the interactive
# /docs "Authorize" button.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")

DbSession = Annotated[Session, Depends(get_db)]
Credentials = Annotated[str, Depends(oauth2_scheme)]


def get_current_user(db: DbSession, token: Credentials) -> User:
    """Resolve the authenticated user from the bearer token."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        username = payload.get("sub")
    except jwt.PyJWTError:
        raise credentials_error from None

    if not username:
        raise credentials_error

    user = db.query(User).filter(User.username == username).one_or_none()

    # A deactivated account is rejected even if its token has not expired.
    if user is None or not user.is_active:
        raise credentials_error

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_company(
    db: DbSession,
    user: CurrentUser,
    company_code: Annotated[str | None, Query(alias="company")] = None,
) -> Company:
    """Resolve and authorise the company this request operates on.

    This is the tenant boundary. Every endpoint that touches business data
    depends on it, so an unfiltered query cannot reach the data layer.

    Raises 404 when the company is unknown and 403 when the user has no grant,
    which keeps the response identical for "does not exist" and "exists but you
    may not see it" from an outsider's point of view.
    """
    granted = [company.code for company in user.companies]
    # Prefer the configured default so the landing company is deterministic.
    # Relationship ordering is not guaranteed, and opening the dashboard on a
    # different tenant each time is confusing.
    default = settings.default_company
    code = company_code or (default if default in granted else (granted[0] if granted else default))

    company = db.get(Company, code)
    if company is None:
        raise HTTPException(status_code=404, detail=f"Unknown company '{code}'")

    if not user.can_access(code):
        raise HTTPException(
            status_code=403,
            detail=f"User '{user.username}' has no access to company '{code}'",
        )

    return company


CurrentCompany = Annotated[Company, Depends(get_current_company)]


def require_roles(*roles: Role) -> Callable[..., User]:
    """Dependency factory enforcing that the caller holds one of ``roles``.

    This is the server-side half of authorisation. The frontend hides
    navigation entries the user cannot use, but that is presentation only: this
    dependency is what actually rejects the request.

    Use it on any endpoint that does not move a record through a workflow.
    Workflow endpoints additionally validate the transition graph in their
    service, because a role being allowed to perform an action does not mean
    the action is legal from the current state.
    """

    def _dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            allowed = ", ".join(sorted(r.value for r in roles))
            raise HTTPException(
                status_code=403,
                detail=f"Role '{user.role.value}' is not permitted. Allowed roles: {allowed}",
            )
        return user

    return _dependency


# Shared aliases so the same rule reads the same way at every call site.
Administrator = Annotated[User, Depends(require_roles(Role.ADMIN))]


class Pagination:
    """Limit/offset pagination resolved from query parameters."""

    def __init__(
        self,
        limit: Annotated[int, Query(ge=1, le=500)] = 50,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> None:
        self.limit = limit
        self.offset = offset


PageParams = Annotated[Pagination, Depends(Pagination)]


def paginate(db: Session, query, page: Pagination):
    """Apply limit/offset to a SQLAlchemy 2.0 select and return a page.

    Returns ``(rows, total)`` so the endpoint can build the response envelope.
    The count runs as a separate aggregate query rather than windowing the
    main one, so an expensive page is still paginated correctly.
    """
    from sqlalchemy import func

    total = db.execute(query.order_by(None).with_only_columns(func.count())).scalar()
    rows = db.execute(query.limit(page.limit).offset(page.offset)).scalars().all()
    return list(rows), int(total or 0)