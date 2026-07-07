"""
Backward-compatibility shim — all logic lives in app/core/security.py.
Do NOT add new code here; import from app.core.security instead.
"""
from app.core.security import SecurityHeadersMiddleware  # noqa: F401
