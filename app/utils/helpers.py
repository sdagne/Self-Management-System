"""
Utility / helper functions for Self Management System.
"""

import base64
import hashlib
import hmac
from datetime import datetime, timedelta
from io import BytesIO

import qrcode

from app.config import settings


def hash_id_number(id_number: str) -> str:
    """
    Hash ID number for privacy using HMAC-SHA-256 with the SECRET_KEY.
    Prevents rainbow-table attacks.
    """
    return hmac.new(settings.secret_key.encode(), id_number.encode(), hashlib.sha256).hexdigest()


def generate_ticket_number(service_type: str, sequence: int) -> str:
    """
    Generate a unique ticket number.
    Format: [SERVICE_PREFIX]-[SEQUENCE_PADDED]  e.g. IM-045
    """
    prefixes = {
        "birth_certificate": "BC",
        "tax_service": "TX",
        "immigration": "IM",
        "business_license": "BL",
        "passport_renewal": "PR",
        "document_legalization": "DL",
        "driver_license_renewal": "DL",
        "driver_license_new": "DL",
        "vehicle_registration": "VR",
        "kebele_id": "KI",
        "fayda_id": "FI",
        "national_id": "NI",
        "land_registration": "LR",
        "visa_services": "VS",
        "other": "OT",
    }
    prefix = prefixes.get(service_type, "GN")
    return f"{prefix}-{sequence:03d}"


def generate_qr_code(ticket_data: dict) -> str:
    """
    Generate a QR code for the given ticket data.
    Returns a base64-encoded PNG image string.
    """
    qr_data = (
        f"TICKET:{ticket_data['ticket_number']}"
        f"|NAME:{ticket_data['full_name']}"
        f"|SERVICE:{ticket_data['service_type']}"
        f"|TIME:{ticket_data['created_at']}"
    )
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()


def calculate_expiry_time() -> datetime:
    """Return the ticket expiry timestamp (now + configured hours)."""
    return datetime.utcnow() + timedelta(hours=settings.ticket_expiry_hours)


def is_ticket_expired(expires_at: datetime) -> bool:
    """Return True if the ticket has passed its expiry time."""
    return datetime.utcnow() > expires_at


def estimate_wait_time(queue_position: int, avg_service_time_minutes: float = 5.0) -> int:
    """Estimate wait time in minutes based on queue position."""
    return int(queue_position * avg_service_time_minutes)


def format_ticket_for_printing(ticket_data: dict) -> str:
    """Format ticket data as a string suitable for a thermal printer."""
    return f"""
{'='*40}
    SELF MANAGEMENT SYSTEM
    Ethiopia - Queue Standard
{'='*40}

Ticket Number: {ticket_data['ticket_number']}
Name: {ticket_data['full_name']}
Service: {ticket_data['service_type'].replace('_', ' ').title()}

Issued:  {ticket_data['created_at'].strftime('%Y-%m-%d %H:%M')}
Expires: {ticket_data['expires_at'].strftime('%Y-%m-%d %H:%M')}

Queue Position:  {ticket_data.get('queue_position', 'N/A')}
Estimated Wait:  {ticket_data.get('estimated_wait_minutes', 'N/A')} minutes

{'='*40}
IMPORTANT:
- Keep this ticket safe
- Must present ID at counter
- Valid for {settings.ticket_expiry_hours} hours only
- Non-transferable
{'='*40}

Thank you for your patience!
"""


def detect_suspicious_activity(citizen_id: int, db_session) -> bool:
    """
    Detect potential fraud or abuse.
    Returns True if the citizen's activity looks suspicious.
    """
    from app.db.database import Ticket, TicketStatus
    from datetime import datetime, timedelta

    recent_time = datetime.utcnow() - timedelta(hours=1)
    recent_active = (
        db_session.query(Ticket)
        .filter(
            Ticket.citizen_id == citizen_id,
            Ticket.created_at >= recent_time,
            Ticket.status.in_([TicketStatus.WAITING, TicketStatus.CALLED, TicketStatus.SERVING]),
        )
        .count()
    )

    if recent_active >= 5:
        return True

    failed = (
        db_session.query(Ticket)
        .filter(
            Ticket.citizen_id == citizen_id,
            Ticket.status.in_([TicketStatus.CANCELLED, TicketStatus.EXPIRED]),
        )
        .count()
    )

    if failed >= 10:
        return True

    return False


def validate_id_format(id_number: str, id_type: str = "kebele") -> bool:
    """Basic validation for an ID number string."""
    if not id_number or len(id_number) < 5:
        return False
    return True
