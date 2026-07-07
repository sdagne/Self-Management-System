"""
Backward-compatibility shim — all logic lives in app/utils/helpers.py.
Do NOT add new code here; import from app.utils.helpers instead.
"""

from app.utils.helpers import (  # noqa: F401
    hash_id_number,
    generate_ticket_number,
    generate_qr_code,
    calculate_expiry_time,
    is_ticket_expired,
    estimate_wait_time,
    format_ticket_for_printing,
    detect_suspicious_activity,
    validate_id_format,
)
