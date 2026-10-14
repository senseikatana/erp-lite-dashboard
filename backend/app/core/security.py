"""Password hashing and JWT token handling."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# bcrypt truncates silently at 72 bytes; argon2 has no such limit.
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plaintext password with Argon2."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against an Argon2 hash.

    Returns False instead of raising so callers cannot distinguish a missing
    user from a wrong password.
    """
    if not hashed_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # Malformed hash in the database: treat as a failed login.
        return False


def create_access_token(
    subject: str,
    *,
    company_code: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Issue a signed JWT for a user session.

    The active company and role are embedded so the token is self-describing,
    which keeps the auth dependency free of extra database round-trips.
    """
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "company": company_code,
        "role": role,
        "exp": expire,
        "iat": datetime.now(UTC),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT.

    Raises ``jwt.PyJWTError`` on an invalid signature or an expired token.
    """
    return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])