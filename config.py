"""
Backward-compatibility shim — all logic lives in app/config.py.
Do NOT add new code here; import from app.config instead.
"""
from app.config import Settings, settings  # noqa: F401
