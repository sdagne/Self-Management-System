"""
Backward-compatibility shim — all logic lives in app/core/auth.py.
Do NOT add new code here; import from app.core.auth instead.
"""

from app.core.auth import (  # noqa: F401
    bearer_scheme,
    create_access_token,
    decode_access_token,
    get_current_role,
    require_role,
    exchange_static_token_for_jwt,
)
