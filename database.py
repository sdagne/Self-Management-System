"""
Database configuration and models
"""

import logging
from sqlalchemy import (
    create_engine,
    event,
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Enum as SQLEnum,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool, StaticPool
from datetime import datetime
import enum
from config import settings
from sqlalchemy import Column, String, Boolean

logger = logging.getLogger(__name__)

# ─── Connection Pool Configuration ────────────────────────────────────────────
# Tuned for production workloads. Adjust based on:
#   - PostgreSQL max_connections (default 100)
#   - Number of API worker processes (typically 4–8 with gunicorn)
#   - Rule of thumb: pool_size = max_connections / num_workers - 2 (buffer)

_db_url = settings.database_url.replace("postgres://", "postgresql://", 1)
_is_sqlite = "sqlite" in _db_url

if _is_sqlite:
    # SQLite: use StaticPool for test/dev — no real pooling needed
    engine = create_engine(
        _db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        _db_url,
        # ── Pool sizing ─────────────────────────────────────────────────────
        poolclass=QueuePool,
        pool_size=10,  # Persistent connections kept open per worker process
        max_overflow=20,  # Extra connections allowed when pool is exhausted (burst)
        pool_timeout=30,  # Seconds to wait for a connection before raising PoolTimeout
        # ── Connection health ────────────────────────────────────────────────
        pool_recycle=1800,  # Recycle connections after 30 min (prevents stale/dropped conns)
        pool_pre_ping=True,  # Issue a lightweight SELECT 1 before using a connection
        # Automatically reconnects if the DB restarted
        # ── Logging / echo ───────────────────────────────────────────────────
        echo=False,  # Set True temporarily to log all SQL (never in production)
        # ── Connect args ─────────────────────────────────────────────────────
        connect_args={
            "connect_timeout": 10,  # TCP connect timeout (seconds)
            "options": "-c statement_timeout=30000",  # Kill queries running > 30s
            "application_name": "queue-management-api",  # Visible in pg_stat_activity
        },
    )

    # ── Pool event listeners ─────────────────────────────────────────────────
    @event.listens_for(engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        """Run after a new DBAPI connection is established."""
        logger.debug("New database connection established")

    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        """Run each time a connection is retrieved from the pool."""
        pass  # Hook available for custom metrics/tracing

    @event.listens_for(engine, "checkin")
    def on_checkin(dbapi_connection, connection_record):
        """Run each time a connection is returned to the pool."""
        pass  # Hook available for custom metrics/tracing


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Enums
class TicketStatus(str, enum.Enum):
    WAITING = "waiting"
    CALLED = "called"
    SERVING = "serving"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ServiceType(str, enum.Enum):
    # Civil Registration & Identification
    KEBELE_ID = "kebele_id"
    BIRTH_CERTIFICATE = "birth_certificate"
    FAYDA_ID = "fayda_id"
    NATIONAL_ID = "national_id"  # Kept for backward compatibility

    # Land & Property
    LAND_CONSTRUCTION_PERMIT = "land_construction_permit"
    LAND_MAPS = "land_maps"
    LAND_REGISTRATION = "land_registration"

    # Travel & Immigration
    PASSPORT_RENEWAL = "passport_renewal"
    VISA_SERVICES = "visa_services"
    YELLOW_CARD = "yellow_card"
    TRAVEL_DOCUMENTS = "travel_documents"

    # Business & Commercial
    BUSINESS_LICENSE = "business_license"
    BUSINESS_REGISTRATION = "business_registration"
    IMPORT_EXPORT = "import_export"

    # Driving Services
    DRIVER_LICENSE_RENEWAL = "driver_license_renewal"
    DRIVER_LICENSE_NEW = "driver_license_new"
    VEHICLE_REGISTRATION = "vehicle_registration"

    # Telecommunications
    ETHIO_TELECOM = "ethio_telecom"
    SIM_REGISTRATION = "sim_registration"

    # Banking & Financial
    COMMERCIAL_BANK = "commercial_bank"
    FINANCIAL_SERVICES = "financial_services"

    # Postal Services
    ETHIO_POST = "ethio_post"
    MAIL_SERVICES = "mail_services"

    # Other Services
    DOCUMENT_LEGALIZATION = "document_legalization"
    TAX_SERVICE = "tax_service"
    EDUCATION_SERVICES = "education_services"
    HEALTH_SERVICES = "health_services"
    IMMIGRATION = "immigration"
    OTHER = "other"


# Database Models
class Citizen(Base):
    """Citizen/User information"""

    __tablename__ = "citizens"

    id = Column(Integer, primary_key=True, index=True)
    id_number_hash = Column(String, unique=True, index=True, nullable=False)  # Hashed for privacy
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_blacklisted = Column(Boolean, default=False)
    blacklist_reason = Column(String, nullable=True)
    # Telegram fields
    telegram_chat_id = Column(String, nullable=True, unique=True, index=True)
    telegram_notifications_enabled = Column(Boolean, default=True)


class Ticket(Base):
    """Ticket information"""

    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    ticket_number = Column(String, unique=True, index=True, nullable=False)
    citizen_id = Column(Integer, nullable=False)
    id_number_hash = Column(String, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    service_type = Column(SQLEnum(ServiceType), nullable=False)
    status = Column(SQLEnum(TicketStatus), default=TicketStatus.WAITING)
    counter_number = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    called_at = Column(DateTime, nullable=True)
    served_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)

    qr_code = Column(String, nullable=True)
    # Telegram fields
    telegram_chat_id = Column(String, nullable=True, index=True)
    telegram_notification_sent = Column(Boolean, default=False)
    telegram_reminder_scheduled = Column(Boolean, default=False)
    appointment_date = Column(String, nullable=True)  # Format: YYYY-MM-DD
    appointment_time = Column(String, nullable=True)  # Format: HH:MM


class Counter(Base):
    """Service counter information"""

    __tablename__ = "counters"

    id = Column(Integer, primary_key=True, index=True)
    counter_number = Column(Integer, unique=True, nullable=False)
    counter_name = Column(String, nullable=False)
    service_types = Column(String, nullable=False)  # Comma-separated service types
    is_active = Column(Boolean, default=True)
    current_ticket_id = Column(Integer, nullable=True)
    staff_name = Column(String, nullable=True)


class AuditLog(Base):
    """Audit trail for security and fraud detection"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String, nullable=False)
    citizen_id = Column(Integer, nullable=True)
    ticket_id = Column(Integer, nullable=True)
    counter_id = Column(Integer, nullable=True)
    details = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_suspicious = Column(Boolean, default=False)


# Database initialization
def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
