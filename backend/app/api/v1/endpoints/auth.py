"""Authentication endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import Administrator, CurrentUser, DbSession
from app.core.config import settings
from app.core.security import create_access_token
from app.models.company import Company
from app.models.user import Role, User, UserCompanyAccess
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    Token,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.schemas.common import Message
from app.services import activity

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_token(user: User, company_code: str) -> Token:
    token = create_access_token(user.username, company_code=company_code, role=user.role.value)
    return Token(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserRead.model_validate(user),
        active_company=company_code,
    )


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: DbSession) -> Token:
    """Exchange credentials for a bearer token.

    A wrong username and a wrong password produce the same error so the
    endpoint cannot be used to enumerate accounts.
    """
    user = db.scalar(select(User).where(User.username == payload.username))

    if user is None or not user.check_password(payload.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account is deactivated",
        )

    granted = [company.code for company in user.companies]
    default = settings.default_company
    company_code = (
        default if default in granted else (granted[0] if granted else default)
    )
    return _issue_token(user, company_code)


@router.get("/me", response_model=UserRead)
def read_current_user(user: CurrentUser) -> User:
    return user


@router.post("/change-password", response_model=Message)
def change_password(payload: ChangePasswordRequest, db: DbSession, user: CurrentUser) -> Message:
    """Change the caller's own password.

    The current password is required even though the caller already holds a
    valid token: a stolen token should not be enough to lock out the owner.
    """
    if not user.check_password(payload.current_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")

    user.set_password(payload.new_password)
    db.commit()
    return Message(message="Password updated")


# --- Administration ---


@router.get("/users", response_model=list[UserRead])
def list_users(db: DbSession, user: Administrator) -> list[User]:
    """List all users. Administrators only."""
    return list(db.scalars(select(User).order_by(User.username)).all())


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: DbSession, user: Administrator) -> User:
    """Create a user account. Administrators only."""

    if db.scalar(select(User).where(User.username == payload.username)):
        raise HTTPException(status_code=409, detail="Username already exists")

    new_user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
    )
    new_user.set_password(payload.password)
    db.add(new_user)
    db.flush()

    for code in payload.company_codes:
        if db.get(Company, code) is None:
            raise HTTPException(status_code=404, detail=f"Unknown company '{code}'")
        db.add(UserCompanyAccess(user_id=new_user.id, company_code=code))

    db.commit()

    codes = payload.company_codes
    default_company = codes[0] if codes else settings.default_company
    activity.record(
        db,
        company_code=default_company,
        actor=user,
        entity="user",
        action="created",
        entity_id=new_user.id,
        summary=f"Created user {new_user.username} ({new_user.role.value})",
    )
    db.commit()

    return new_user


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int, payload: UserUpdate, db: DbSession, user: Administrator
) -> User:
    """Update a user. Administrators only."""

    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")

    # Guard against an administrator disabling or demoting themselves, which
    # can leave the installation with no way back in.
    losing_access = payload.is_active is False or payload.role not in (None, Role.ADMIN)
    if target.id == user.id and losing_access:
        raise HTTPException(
            status_code=400,
            detail="You cannot remove your own administrator access",
        )

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "password" and value:
            target.set_password(value)
        elif field in ("full_name", "email", "role", "is_active"):
            setattr(target, field, value)

    db.commit()
    db.refresh(target)
    return target