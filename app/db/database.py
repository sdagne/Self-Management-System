"""
Database configuration, connection pooling, and SQLAlchemy models.
"""

import logging
import enum
from datetime import datetime

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

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Connection Pool ─────────────────────────────────────────────────────────────
_db_url = settings.database_url.replace("postgres://", "postgresql://", 1)
_is_sqlite = "sqlite" in _db_url

if _is_sqlite:
    engine = create_engine(
        _db_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    engine = create_engine(
        _db_url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=1800,
        pool_pre_ping=True,
        echo=False,
        connect_args={
            "connect_timeout": 10,
            "options": "-c statement_timeout=30000",
            "application_name": "queue-management-api",
        },
    )

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        logger.debug("New database connection established")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── Enums ───────────────────────────────────────────────────────────────────────


class TicketStatus(str, enum.Enum):
    WAITING = "waiting"
    CALLED = "called"
    SERVING = "serving"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ServiceType(str, enum.Enum):
    KEBELE_ID = "kebele_id"
    BIRTH_CERTIFICATE = "birth_certificate"
    FAYDA_ID = "fayda_id"
    NATIONAL_ID = "national_id"
    LAND_CONSTRUCTION_PERMIT = "land_construction_permit"
    LAND_MAPS = "land_maps"
    LAND_REGISTRATION = "land_registration"
    PASSPORT_RENEWAL = "passport_renewal"
    VISA_SERVICES = "visa_services"
    YELLOW_CARD = "yellow_card"
    TRAVEL_DOCUMENTS = "travel_documents"
    BUSINESS_LICENSE = "business_license"
    BUSINESS_REGISTRATION = "business_registration"
    IMPORT_EXPORT = "import_export"
    DRIVER_LICENSE_RENEWAL = "driver_license_renewal"
    DRIVER_LICENSE_NEW = "driver_license_new"
    VEHICLE_REGISTRATION = "vehicle_registration"
    ETHIO_TELECOM = "ethio_telecom"
    SIM_REGISTRATION = "sim_registration"
    COMMERCIAL_BANK = "commercial_bank"
    FINANCIAL_SERVICES = "financial_services"
    ETHIO_POST = "ethio_post"
    MAIL_SERVICES = "mail_services"
    DOCUMENT_LEGALIZATION = "document_legalization"
    TAX_SERVICE = "tax_service"
    EDUCATION_SERVICES = "education_services"
    HEALTH_SERVICES = "health_services"
    IMMIGRATION = "immigration"
    OTHER = "other"


# ─── ORM Models ─────────────────────────────────────────────────────────────────


class Citizen(Base):
    __tablename__ = "citizens"

    id = Column(Integer, primary_key=True, index=True)
    id_number_hash = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_blacklisted = Column(Boolean, default=False)
    blacklist_reason = Column(String, nullable=True)
    telegram_chat_id = Column(String, nullable=True, unique=True, index=True)
    telegram_notifications_enabled = Column(Boolean, default=True)


class Ticket(Base):
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
    telegram_chat_id = Column(String, nullable=True, index=True)
    telegram_notification_sent = Column(Boolean, default=False)
    telegram_reminder_scheduled = Column(Boolean, default=False)
    appointment_date = Column(String, nullable=True)
    appointment_time = Column(String, nullable=True)


class Counter(Base):
    __tablename__ = "counters"

    id = Column(Integer, primary_key=True, index=True)
    counter_number = Column(Integer, unique=True, nullable=False)
    counter_name = Column(String, nullable=False)
    service_types = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    current_ticket_id = Column(Integer, nullable=True)
    staff_name = Column(String, nullable=True)


class AuditLog(Base):
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


# ─── Helpers ─────────────────────────────────────────────────────────────────────


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI dependency: yields a database session, always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
