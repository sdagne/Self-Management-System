"""
Pydantic request/response models for the Queue Management System API.
"""
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field

from app.db.database import ServiceType, TicketStatus


# ─── Request Models ──────────────────────────────────────────────────────────────

class TicketCreateRequest(BaseModel):
    """Request to create a new ticket."""
    id_number: str = Field(..., description="Citizen ID number")
    full_name: str = Field(..., min_length=2, max_length=100)
    service_type: ServiceType
    phone_number: Optional[str] = None
    appointment_date: Optional[str] = None   # Format: YYYY-MM-DD
    appointment_time: Optional[str] = None   # Format: HH:MM
    special_instructions: Optional[str] = None


class TicketVerifyRequest(BaseModel):
    """Request to verify ticket at counter."""
    ticket_number: str
    id_number: str


class TicketAssignRequest(BaseModel):
    """Request to assign a waiting ticket to a counter."""
    ticket_number: str


class CounterCreateRequest(BaseModel):
    """Request to create a counter."""
    counter_number: int
    counter_name: str
    service_types: List[ServiceType]
    staff_name: Optional[str] = None


class CounterUpdateRequest(BaseModel):
    """Request to update counter status."""
    is_active: Optional[bool] = None
    staff_name: Optional[str] = None


# ─── Response Models ─────────────────────────────────────────────────────────────

class TicketResponse(BaseModel):
    """Ticket response."""
    id: int
    ticket_number: str
    full_name: str
    service_type: ServiceType
    status: TicketStatus
    counter_number: Optional[int] = None
    created_at: datetime
    expires_at: datetime
    estimated_wait_minutes: Optional[int] = None
    queue_position: Optional[int] = None
    qr_code: Optional[str] = None

    class Config:
        from_attributes = True


class CounterResponse(BaseModel):
    """Counter response."""
    id: int
    counter_number: int
    counter_name: str
    service_types: str
    is_active: bool
    current_ticket_id: Optional[int] = None
    staff_name: Optional[str] = None

    class Config:
        from_attributes = True


class QueueStatusResponse(BaseModel):
    """Queue status for display."""
    now_serving: List[dict]
    waiting_count: int
    total_served_today: int
    average_wait_minutes: Optional[int] = None


class StatisticsResponse(BaseModel):
    """System statistics."""
    total_tickets_today: int
    total_served_today: int
    total_waiting: int
    total_expired: int
    active_counters: int
    average_service_time_minutes: float
    peak_hour: Optional[int] = None
