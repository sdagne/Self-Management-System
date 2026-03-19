"""
Utility functions for Queue Management System
"""
import hashlib
import hmac
import qrcode
from io import BytesIO
import base64
from datetime import datetime, timedelta
from typing import Optional
from config import settings


def hash_id_number(id_number: str) -> str:
    """
    Hash ID number for privacy and security
    Uses HMAC-SHA-256 with SECRET_KEY to prevent rainbow table attacks
    """
    return hmac.new(settings.secret_key.encode(), id_number.encode(), hashlib.sha256).hexdigest()


def generate_ticket_number(service_type: str, sequence: int) -> str:
    """
    Generate unique ticket number
    Format: [SERVICE_PREFIX]-[SEQUENCE]
    Example: IM-045 for Immigration service #45
    """
    prefixes = {
        "birth_certificate": "BC",
        "tax_service": "TX",
        "immigration": "IM",
        "business_license": "BL",
        "passport_renewal": "PR",
        "document_legalization": "DL",
        "other": "OT"
    }

    prefix = prefixes.get(service_type, "GN")
    return f"{prefix}-{sequence:03d}"


def generate_qr_code(ticket_data: dict) -> str:
    """
    Generate QR code for ticket
    Returns base64 encoded image
    """
    # Create QR code data string
    qr_data = f"TICKET:{ticket_data['ticket_number']}|NAME:{ticket_data['full_name']}|SERVICE:{ticket_data['service_type']}|TIME:{ticket_data['created_at']}"

    # Generate QR code
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_data)
    qr.make(fit=True)

    # Create image
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    return img_str


def calculate_expiry_time() -> datetime:
    """
    Calculate ticket expiry time
    Default: Current time + configured hours
    """
    return datetime.utcnow() + timedelta(hours=settings.ticket_expiry_hours)


def is_ticket_expired(expires_at: datetime) -> bool:
    """Check if ticket has expired"""
    return datetime.utcnow() > expires_at


def estimate_wait_time(queue_position: int, avg_service_time_minutes: float = 5.0) -> int:
    """
    Estimate wait time based on queue position
    Returns minutes
    """
    return int(queue_position * avg_service_time_minutes)


def format_ticket_for_printing(ticket_data: dict) -> str:
    """
    Format ticket data for thermal printer
    Returns formatted string
    """
    ticket_text = f"""
{'='*40}
   QUEUE MANAGEMENT SYSTEM
   Ethiopia - Queue Standard
{'='*40}

Ticket Number: {ticket_data['ticket_number']}
Name: {ticket_data['full_name']}
Service: {ticket_data['service_type'].replace('_', ' ').title()}

Issued: {ticket_data['created_at'].strftime('%Y-%m-%d %H:%M')}
Expires: {ticket_data['expires_at'].strftime('%Y-%m-%d %H:%M')}

Queue Position: {ticket_data.get('queue_position', 'N/A')}
Estimated Wait: {ticket_data.get('estimated_wait_minutes', 'N/A')} minutes

{'='*40}
IMPORTANT:
- Keep this ticket safe
- Must present ID at counter
- Valid for 2 hours only
- Non-transferable
{'='*40}

Thank you for your patience!
    """
    return ticket_text


def detect_suspicious_activity(citizen_id: int, db_session) -> bool:
    """
    Detect potential fraud or suspicious activity
    Returns True if suspicious
    """
    from database import Ticket, TicketStatus
    from datetime import datetime, timedelta

    # Check: Multiple ACTIVE tickets in short time (more lenient for testing)
    recent_time = datetime.utcnow() - timedelta(hours=1)
    recent_active_tickets = db_session.query(Ticket).filter(
        Ticket.citizen_id == citizen_id,
        Ticket.created_at >= recent_time,
        Ticket.status.in_([TicketStatus.WAITING, TicketStatus.CALLED, TicketStatus.SERVING])
    ).count()

    # More lenient threshold: 5+ active tickets in an hour
    if recent_active_tickets >= 5:
        return True

    # Check: Excessive failed tickets over longer period
    failed_tickets = db_session.query(Ticket).filter(
        Ticket.citizen_id == citizen_id,
        Ticket.status.in_([TicketStatus.CANCELLED, TicketStatus.EXPIRED])
    ).count()

    # More lenient threshold: 10+ failed tickets
    if failed_tickets >= 10:
        return True

    return False


def validate_id_format(id_number: str, id_type: str = "kebele") -> bool:
    """
    Validate ID number format
    Basic validation - can be enhanced for specific ID types
    """
    if not id_number or len(id_number) < 5:
        return False

    # Add specific validation logic for different ID types
    # This is a placeholder
    return True

