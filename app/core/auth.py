"""
Authentication & authorisation for Queue Management System.

Supports two modes:
  1. Static API Tokens  — for kiosk / counter hardware (no expiry, set in .env)
  2. JWT Bearer Tokens  — for staff portals and admin tools (short-lived, signed)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from starlette import status

from app.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


# ─── JWT helpers ────────────────────────────────────────────────────────────────

def create_access_token(role: str, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT for the given role.
    Tokens expire after settings.access_token_expire_minutes by default.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload = {
        "sub": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> Optional[str]:
    """
    Validate a JWT and return the role (sub claim).
    Returns None on any validation failure instead of raising.
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload.get("sub")
    except JWTError:
        return None


# ─── Dependency ─────────────────────────────────────────────────────────────────

def get_current_role(
    credentials: HTTPAuthorizationCredentials = Security(bearer_scheme),
) -> str:
    """
    Resolve the caller's role from a Bearer token.

    Resolution order:
      1. Try to decode as a signed JWT  — staff / portal sessions.
      2. Fall back to static API token map  — kiosk / counter hardware.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # 1. Try JWT first
    role = decode_access_token(token)
    if role:
        return role

    # 2. Fall back to static token map
    token_to_role = {v: k for k, v in settings.api_tokens.items()}
    role = token_to_role.get(token)
    if role:
        return role

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_role(required_roles: list[str]):
    """FastAPI dependency factory: only allow callers whose role is in required_roles."""
    def wrapper(role: str = Depends(get_current_role)):
        if role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden for this role",
            )
        return role
    return wrapper


# ─── Login endpoint helper ───────────────────────────────────────────────────────

def exchange_static_token_for_jwt(static_token: str) -> Optional[str]:
    """
    Allow existing hardware clients to exchange their static token for a
    short-lived JWT. Returns None if the static token is not recognised.
    """
    token_to_role = {v: k for k, v in settings.api_tokens.items()}
    role = token_to_role.get(static_token)
    if not role:
        return None
    return create_access_token(role)
