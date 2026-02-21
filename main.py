"""
Main FastAPI application for Queue Management System
Ethiopia - Queue Management Standard
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List

from database import get_db, init_db, Ticket, Citizen, Counter, AuditLog, TicketStatus, ServiceType
from models import (
    TicketCreateRequest, TicketResponse, TicketVerifyRequest,
    TicketAssignRequest,
    CounterCreateRequest, CounterResponse, CounterUpdateRequest,
    QueueStatusResponse, StatisticsResponse
)
from utils import (
    hash_id_number, generate_ticket_number, generate_qr_code,
    calculate_expiry_time, is_ticket_expired, estimate_wait_time,
    format_ticket_for_printing, detect_suspicious_activity
)
from config import settings
from auth import require_role
import os
from fastapi.staticfiles import StaticFiles

# Role-based access dependencies
counter_access = require_role(["counter", "admin"])
# Initialize FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Personalized Queue Management System"
)

# ================= CORS MIDDLEWARE =================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# ================= STATIC FILES =================
app.mount("/web", StaticFiles(directory="web_portals"), name="web")

# ================= ROUTES =================
# Serve main page at root /
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Queue Management System - Ethiopia",
        "version": settings.version,
        "status": "operational"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}
# --------------------------------------------------------

@app.get("/status")
async def server_status():
    """
    Endpoint for demo_dashboard.html to check if server is online
    """
    return {"server": "online"}

# ==================== KIOSK ENDPOINTS ====================

@app.post("/api/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    request: TicketCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new ticket at kiosk
    Enforces: One active ticket per citizen
    """
    # Hash ID for privacy
    id_hash = hash_id_number(request.id_number)

    # Check for existing active ticket
    existing_ticket = db.query(Ticket).filter(
        Ticket.id_number_hash == id_hash,
        Ticket.status.in_([TicketStatus.WAITING, TicketStatus.CALLED, TicketStatus.SERVING])
    ).first()

    if existing_ticket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have an active ticket: {existing_ticket.ticket_number}. Please wait to be served."
        )

    # Get or create citizen record
    citizen = db.query(Citizen).filter(Citizen.id_number_hash == id_hash).first()

    if not citizen:
        citizen = Citizen(
            id_number_hash=id_hash,
            full_name=request.full_name,
            phone_number=request.phone_number
        )
        db.add(citizen)
        db.commit()
        db.refresh(citizen)

    # Check if citizen is blacklisted
    if citizen.is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Reason: {citizen.blacklist_reason}"
        )

    # Detect suspicious activity
    if detect_suspicious_activity(citizen.id, db):
        # Log suspicious activity
        audit = AuditLog(
            action="SUSPICIOUS_TICKET_REQUEST",
            citizen_id=citizen.id,
            details=f"Multiple ticket requests detected for {request.full_name}",
            is_suspicious=True
        )
        db.add(audit)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many ticket requests. Please contact administration."
        )

    # Generate ticket number
    last_ticket = db.query(Ticket).order_by(Ticket.id.desc()).first()
    sequence = (last_ticket.id + 1) if last_ticket else 1
    ticket_number = generate_ticket_number(request.service_type.value, sequence)

    # Calculate queue position
    queue_position = db.query(Ticket).filter(
        Ticket.service_type == request.service_type,
        Ticket.status == TicketStatus.WAITING
    ).count() + 1

    # Create ticket
    new_ticket = Ticket(
        ticket_number=ticket_number,
        citizen_id=citizen.id,
        id_number_hash=id_hash,
        full_name=request.full_name,
        service_type=request.service_type,
        status=TicketStatus.WAITING,
        expires_at=calculate_expiry_time()
    )

    # Generate QR code
    ticket_data = {
        "ticket_number": ticket_number,
        "full_name": request.full_name,
        "service_type": request.service_type.value,
        "created_at": str(datetime.utcnow())
    }
    new_ticket.qr_code = generate_qr_code(ticket_data)

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    # Log action
    audit = AuditLog(
        action="TICKET_CREATED",
        citizen_id=citizen.id,
        ticket_id=new_ticket.id,
        details=f"Ticket {ticket_number} created for {request.service_type.value}"
    )
    db.add(audit)
    db.commit()

    # Prepare response
    response = TicketResponse(
        id=new_ticket.id,
        ticket_number=new_ticket.ticket_number,
        full_name=new_ticket.full_name,
        service_type=new_ticket.service_type,
        status=new_ticket.status,
        counter_number=new_ticket.counter_number,
        created_at=new_ticket.created_at,
        expires_at=new_ticket.expires_at,
        estimated_wait_minutes=estimate_wait_time(queue_position),
        queue_position=queue_position,
        qr_code=new_ticket.qr_code
    )

    return response


@app.get("/api/tickets/{ticket_number}", response_model=TicketResponse, dependencies=[Depends(counter_access)])
async def get_ticket_status(
    ticket_number: str,
    db: Session = Depends(get_db)
):
    """Get ticket status"""
    ticket = db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    # Check if expired
    if is_ticket_expired(ticket.expires_at) and ticket.status == TicketStatus.WAITING:
        ticket.status = TicketStatus.EXPIRED
        db.commit()

    # Calculate queue position
    queue_position = None
    if ticket.status == TicketStatus.WAITING:
        queue_position = db.query(Ticket).filter(
            Ticket.service_type == ticket.service_type,
            Ticket.status == TicketStatus.WAITING,
            Ticket.id < ticket.id
        ).count() + 1

    return TicketResponse(
        id=ticket.id,
        ticket_number=ticket.ticket_number,
        full_name=ticket.full_name,
        service_type=ticket.service_type,
        status=ticket.status,
        counter_number=ticket.counter_number,
        created_at=ticket.created_at,
        expires_at=ticket.expires_at,
        estimated_wait_minutes=estimate_wait_time(queue_position) if queue_position else None,
        queue_position=queue_position,
        qr_code=ticket.qr_code
    )


# ==================== COUNTER ENDPOINTS ====================

@app.post("/api/counters", response_model=CounterResponse)
async def create_counter(
    request: CounterCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new service counter"""
    # Check if counter number exists
    existing = db.query(Counter).filter(Counter.counter_number == request.counter_number).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Counter number already exists"
        )

    service_types_str = ",".join([st.value for st in request.service_types])

    counter = Counter(
        counter_number=request.counter_number,
        counter_name=request.counter_name,
        service_types=service_types_str,
        staff_name=request.staff_name
    )

    db.add(counter)
    db.commit()
    db.refresh(counter)

    return counter


@app.get("/api/counters", response_model=List[CounterResponse])
async def get_counters(db: Session = Depends(get_db)):
    """Get all counters"""
    counters = db.query(Counter).all()
    return counters


@app.post("/api/counters/{counter_id}/call-next")
async def call_next_ticket(
    counter_id: int,
    db: Session = Depends(get_db)
):
    """Call next ticket in queue for this counter"""
    counter = db.query(Counter).filter(Counter.id == counter_id).first()

    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counter not found"
        )

    if not counter.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Counter is not active"
        )

    # Get service types for this counter
    service_types = counter.service_types.split(",")

    # Find next waiting ticket
    next_ticket = db.query(Ticket).filter(
        Ticket.service_type.in_([ServiceType(st) for st in service_types]),
        Ticket.status == TicketStatus.WAITING,
        Ticket.expires_at > datetime.utcnow()
    ).order_by(Ticket.created_at).first()

    if not next_ticket:
        return {
            "message": "No tickets waiting",
            "counter_number": counter.counter_number
        }

    # Update ticket status
    next_ticket.status = TicketStatus.CALLED
    next_ticket.counter_number = counter.counter_number
    next_ticket.called_at = datetime.utcnow()

    # Update counter
    counter.current_ticket_id = next_ticket.id

    db.commit()

    # Log action
    audit = AuditLog(
        action="TICKET_CALLED",
        ticket_id=next_ticket.id,
        counter_id=counter.id,
        details=f"Ticket {next_ticket.ticket_number} called to counter {counter.counter_number}"
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Ticket called",
        "ticket_number": next_ticket.ticket_number,
        "counter_number": counter.counter_number,
        "full_name": next_ticket.full_name
    }


@app.post("/api/counters/{counter_id}/verify")
async def verify_ticket_at_counter(
    counter_id: int,
    request: TicketVerifyRequest,
    db: Session = Depends(get_db)
):
    """Verify citizen ID matches ticket at counter"""
    counter = db.query(Counter).filter(Counter.id == counter_id).first()

    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counter not found"
        )

    # Get ticket
    ticket = db.query(Ticket).filter(Ticket.ticket_number == request.ticket_number).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    # Verify ID matches
    id_hash = hash_id_number(request.id_number)

    if ticket.id_number_hash != id_hash:
        # Log mismatch
        audit = AuditLog(
            action="VERIFICATION_FAILED",
            ticket_id=ticket.id,
            counter_id=counter.id,
            details=f"ID mismatch for ticket {ticket.ticket_number}",
            is_suspicious=True
        )
        db.add(audit)
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ID does not match ticket. Verification failed."
        )

    # Update ticket to serving
    ticket.status = TicketStatus.SERVING
    ticket.served_at = datetime.utcnow()

    db.commit()

    # Log success
    audit = AuditLog(
        action="VERIFICATION_SUCCESS",
        ticket_id=ticket.id,
        counter_id=counter.id,
        details=f"Ticket {ticket.ticket_number} verified successfully"
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Verification successful",
        "ticket_number": ticket.ticket_number,
        "status": ticket.status
    }


@app.post("/api/counters/{counter_id}/complete")
async def complete_service(
    counter_id: int,
    ticket_number: str,
    db: Session = Depends(get_db)
):
    """Mark service as completed"""
    ticket = db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    ticket.status = TicketStatus.COMPLETED
    ticket.completed_at = datetime.utcnow()

    # Clear counter's current ticket
    counter = db.query(Counter).filter(Counter.id == counter_id).first()
    if counter:
        counter.current_ticket_id = None

    db.commit()

    return {
        "message": "Service completed",
        "ticket_number": ticket.ticket_number
    }


@app.post("/api/counters/{counter_id}/assign-ticket")
async def assign_ticket_to_counter(
    counter_id: int,
    request: TicketAssignRequest,
    db: Session = Depends(get_db)
):
    """Assign a waiting ticket to this counter"""
    counter = db.query(Counter).filter(Counter.id == counter_id).first()

    if not counter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Counter not found"
        )

    if not counter.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Counter is not active"
        )

    ticket = db.query(Ticket).filter(Ticket.ticket_number == request.ticket_number).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    if ticket.status != TicketStatus.WAITING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket is not waiting and cannot be assigned"
        )

    ticket.status = TicketStatus.CALLED
    ticket.counter_number = counter.counter_number
    ticket.called_at = datetime.utcnow()
    counter.current_ticket_id = ticket.id

    db.commit()

    audit = AuditLog(
        action="TICKET_ASSIGNED",
        ticket_id=ticket.id,
        counter_id=counter.id,
        details=f"Ticket {ticket.ticket_number} manually assigned to counter {counter.counter_number}"
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Ticket assigned",
        "ticket_number": ticket.ticket_number,
        "counter_number": counter.counter_number
    }


@app.post("/api/counters/assign-next")
async def assign_next_waiting_ticket(
    db: Session = Depends(get_db)
):
    """Assign the next waiting ticket to the next idle active counter"""
    counters = db.query(Counter).filter(Counter.is_active == True).order_by(Counter.counter_number).all()
    if not counters:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No counters configured"
        )

    waiting_ticket = db.query(Ticket).filter(
        Ticket.status == TicketStatus.WAITING,
        Ticket.expires_at > datetime.utcnow()
    ).order_by(Ticket.created_at).first()

    if not waiting_ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No waiting tickets to assign"
        )

    busy_counter_numbers = {
        row[0] for row in db.query(Ticket.counter_number)
            .filter(
                Ticket.counter_number.isnot(None),
                Ticket.status.in_([TicketStatus.CALLED, TicketStatus.SERVING])
            )
            .distinct()
            .all()
    }

    for counter in counters:
        if counter.counter_number in busy_counter_numbers:
            continue

        waiting_ticket.status = TicketStatus.CALLED
        waiting_ticket.counter_number = counter.counter_number
        waiting_ticket.called_at = datetime.utcnow()
        counter.current_ticket_id = waiting_ticket.id
        db.commit()

        audit = AuditLog(
            action="TICKET_ASSIGNED",
            ticket_id=waiting_ticket.id,
            counter_id=counter.id,
            details=f"Ticket {waiting_ticket.ticket_number} auto-assigned to counter {counter.counter_number}"
        )
        db.add(audit)
        db.commit()

        return {
            "message": "Ticket assigned",
            "ticket_number": waiting_ticket.ticket_number,
            "counter_number": counter.counter_number
        }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="All counters are currently busy"
    )


@app.post("/api/tickets/{ticket_number}/assign-next")
async def assign_ticket_to_next_available_counter(
    ticket_number: str,
    db: Session = Depends(get_db)
):
    ticket = db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    if ticket.status != TicketStatus.WAITING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ticket is not waiting and cannot be reassigned"
        )

    counters = db.query(Counter).filter(Counter.is_active == True).order_by(Counter.counter_number).all()

    if not counters:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No counters configured"
        )

    busy_counter_numbers = {
        row[0] for row in db.query(Ticket.counter_number)
            .filter(
                Ticket.counter_number.isnot(None),
                Ticket.status.in_([TicketStatus.CALLED, TicketStatus.SERVING])
            )
            .distinct()
            .all()
    }

    for counter in counters:
        if counter.counter_number in busy_counter_numbers:
            continue

        ticket.status = TicketStatus.CALLED
        ticket.counter_number = counter.counter_number
        ticket.called_at = datetime.utcnow()
        counter.current_ticket_id = ticket.id
        db.commit()

        audit = AuditLog(
            action="TICKET_ASSIGNED",
            ticket_id=ticket.id,
            counter_id=counter.id,
            details=f"Ticket {ticket.ticket_number} auto-assigned to counter {counter.counter_number}"
        )
        db.add(audit)
        db.commit()

        return {
            "message": "Ticket assigned",
            "ticket_number": ticket.ticket_number,
            "counter_number": counter.counter_number
        }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="All counters are currently busy"
    )


# ==================== TICKET MANAGEMENT ENDPOINTS ====================

@app.delete("/api/tickets/{ticket_number}/cancel")
async def cancel_ticket(
    ticket_number: str,
    id_number: str,
    db: Session = Depends(get_db)
):
    """
    Cancel an active ticket
    Requires ID verification to prevent unauthorized cancellation
    """
    # Get ticket
    ticket = db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    # Verify ID matches
    id_hash = hash_id_number(id_number)
    if ticket.id_number_hash != id_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ID does not match ticket. Cannot cancel."
        )

    # Check if ticket can be cancelled
    if ticket.status in [TicketStatus.COMPLETED, TicketStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel ticket with status: {ticket.status.value}"
        )

    # Cancel the ticket
    ticket.status = TicketStatus.CANCELLED
    ticket.completed_at = datetime.utcnow()

    db.commit()

    # Log action
    audit = AuditLog(
        action="TICKET_CANCELLED",
        ticket_id=ticket.id,
        citizen_id=ticket.citizen_id,
        details=f"Ticket {ticket_number} cancelled by user"
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Ticket cancelled successfully",
        "ticket_number": ticket.ticket_number,
        "status": ticket.status.value
    }


@app.delete("/api/tickets/cancel-by-id")
async def cancel_ticket_by_id(
    id_number: str,
    db: Session = Depends(get_db)
):
    """
    Cancel all active tickets for a given ID
    Useful when user has stuck ticket
    """
    # Hash ID
    id_hash = hash_id_number(id_number)

    # Find all active tickets for this ID
    active_tickets = db.query(Ticket).filter(
        Ticket.id_number_hash == id_hash,
        Ticket.status.in_([TicketStatus.WAITING, TicketStatus.CALLED, TicketStatus.SERVING])
    ).all()

    if not active_tickets:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active tickets found for this ID"
        )

    cancelled_tickets = []
    for ticket in active_tickets:
        ticket.status = TicketStatus.CANCELLED
        ticket.completed_at = datetime.utcnow()
        cancelled_tickets.append(ticket.ticket_number)

        # Log action
        audit = AuditLog(
            action="TICKET_CANCELLED_BY_ID",
            ticket_id=ticket.id,
            citizen_id=ticket.citizen_id,
            details=f"Ticket {ticket.ticket_number} cancelled via ID lookup"
        )
        db.add(audit)

    db.commit()

    return {
        "message": f"Cancelled {len(cancelled_tickets)} ticket(s)",
        "cancelled_tickets": cancelled_tickets
    }


@app.post("/api/tickets/{ticket_number}/expire")
async def force_expire_ticket(
    ticket_number: str,
    db: Session = Depends(get_db)
):
    """
    Force expire a ticket (admin function)
    Useful for stuck tickets or testing
    """
    ticket = db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found"
        )

    if ticket.status in [TicketStatus.COMPLETED, TicketStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot expire ticket with status: {ticket.status.value}"
        )

    ticket.status = TicketStatus.EXPIRED
    ticket.completed_at = datetime.utcnow()

    db.commit()

    # Log action
    audit = AuditLog(
        action="TICKET_FORCE_EXPIRED",
        ticket_id=ticket.id,
        details=f"Ticket {ticket_number} force expired by admin"
    )
    db.add(audit)
    db.commit()

    return {
        "message": "Ticket expired successfully",
        "ticket_number": ticket.ticket_number,
        "status": ticket.status.value
    }


@app.get("/api/tickets/active/{id_number}")
async def get_active_tickets_by_id(
    id_number: str,
    db: Session = Depends(get_db)
):
    """
    Get all active tickets for a given ID
    Useful for checking what tickets a user has
    """
    id_hash = hash_id_number(id_number)

    active_tickets = db.query(Ticket).filter(
        Ticket.id_number_hash == id_hash,
        Ticket.status.in_([TicketStatus.WAITING, TicketStatus.CALLED, TicketStatus.SERVING])
    ).all()

    if not active_tickets:
        return {
            "message": "No active tickets found",
            "tickets": []
        }

    tickets_data = [
        {
            "ticket_number": t.ticket_number,
            "service_type": t.service_type.value,
            "status": t.status.value,
            "created_at": t.created_at.isoformat(),
            "expires_at": t.expires_at.isoformat()
        }
        for t in active_tickets
    ]

    return {
        "message": f"Found {len(active_tickets)} active ticket(s)",
        "tickets": tickets_data
    }


# ==================== DISPLAY ENDPOINTS ====================

@app.get("/api/display/queue-status", response_model=QueueStatusResponse)
async def get_queue_status(db: Session = Depends(get_db)):
    """Get current queue status for display screen"""

    # Get currently serving tickets
    serving_tickets = db.query(Ticket).filter(
        Ticket.status.in_([TicketStatus.CALLED, TicketStatus.SERVING])
    ).all()

    now_serving = [
        {
            "ticket_number": t.ticket_number,
            "counter_number": t.counter_number,
            "status": t.status.value
        }
        for t in serving_tickets
    ]

    # Waiting count
    waiting_count = db.query(Ticket).filter(
        Ticket.status == TicketStatus.WAITING
    ).count()

    # Total served today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_served_today = db.query(Ticket).filter(
        Ticket.status == TicketStatus.COMPLETED,
        Ticket.completed_at >= today_start
    ).count()

    return QueueStatusResponse(
        now_serving=now_serving,
        waiting_count=waiting_count,
        total_served_today=total_served_today,
        average_wait_minutes=15  # Placeholder
    )


@app.get("/api/display/waiting-tickets")
async def get_waiting_tickets(db: Session = Depends(get_db)):
    """Get all waiting tickets with details for dashboard display"""

    waiting_tickets = db.query(Ticket).filter(
        Ticket.status == TicketStatus.WAITING,
        Ticket.expires_at > datetime.utcnow()
    ).order_by(Ticket.created_at).all()

    service_type_map = {
        ServiceType.KEBELE_ID: "Obtaining Kebele ID",
        ServiceType.BIRTH_CERTIFICATE: "Birth Registration Certificate",
        ServiceType.FAYDA_ID: "National ID (Fayda)",
        ServiceType.NATIONAL_ID: "National ID (Fayda)",

        # Land & Property
        ServiceType.LAND_CONSTRUCTION_PERMIT: "Construction Permits (Land)",
        ServiceType.LAND_MAPS: "Land Maps & Associated Matters",
        ServiceType.LAND_REGISTRATION: "Land Registration",

        # Travel & Immigration
        ServiceType.PASSPORT_RENEWAL: "Passport Services",
        ServiceType.VISA_SERVICES: "Visa Services",
        ServiceType.YELLOW_CARD: "Yellow Card",
        ServiceType.TRAVEL_DOCUMENTS: "Travel Documents",

        # Business & Commercial
        ServiceType.BUSINESS_LICENSE: "Business License (Trade License)",
        ServiceType.BUSINESS_REGISTRATION: "Business Registration",
        ServiceType.IMPORT_EXPORT: "Import/Export Services",

        # Driving Services
        ServiceType.DRIVER_LICENSE_RENEWAL: "Driver License Renewal",
        ServiceType.DRIVER_LICENSE_NEW: "New Driver License",
        ServiceType.VEHICLE_REGISTRATION: "Vehicle Registration",

        # Telecommunications
        ServiceType.ETHIO_TELECOM: "Ethio Telecom Services",
        ServiceType.SIM_REGISTRATION: "SIM Card Registration",

        # Banking & Financial
        ServiceType.COMMERCIAL_BANK: "Commercial Bank Services",
        ServiceType.FINANCIAL_SERVICES: "Other Financial Services",

        # Postal Services
        ServiceType.ETHIO_POST: "Ethio Post Services",
        ServiceType.MAIL_SERVICES: "Mail & Package Services",

        # Other Services
        ServiceType.DOCUMENT_LEGALIZATION: "Document Legalization",
        ServiceType.TAX_SERVICE: "Tax Services",
        ServiceType.EDUCATION_SERVICES: "Education Services",
        ServiceType.HEALTH_SERVICES: "Health Services",
        ServiceType.IMMIGRATION: "Immigration Services",
        ServiceType.OTHER: "Other Government Services",
    }

    tickets = []
    for idx, ticket in enumerate(waiting_tickets, 1):
        tickets.append({
            "ticket_number": ticket.ticket_number,
            "full_name": ticket.full_name,
            "service_type": service_type_map.get(ticket.service_type, ticket.service_type.value),
            "status": ticket.status.value,
            "created_at": ticket.created_at.isoformat(),
            "position": idx,
            "id_number_display": ticket.id_number_hash[:8] + "***"  # Partial display for privacy
        })

    return {
        "total_waiting": len(tickets),
        "tickets": tickets
    }


# ==================== STATISTICS ENDPOINTS ====================

@app.get("/api/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """Get system statistics"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_tickets_today = db.query(Ticket).filter(
        Ticket.created_at >= today_start
    ).count()

    total_served_today = db.query(Ticket).filter(
        Ticket.status == TicketStatus.COMPLETED,
        Ticket.completed_at >= today_start
    ).count()

    total_waiting = db.query(Ticket).filter(
        Ticket.status == TicketStatus.WAITING
    ).count()

    total_expired = db.query(Ticket).filter(
        Ticket.status == TicketStatus.EXPIRED,
        Ticket.created_at >= today_start
    ).count()

    active_counters = db.query(Counter).filter(
        Counter.is_active == True
    ).count()

    # Calculate average service time
    completed_tickets = db.query(Ticket).filter(
        Ticket.status == TicketStatus.COMPLETED,
        Ticket.completed_at >= today_start,
        Ticket.served_at.isnot(None)
    ).all()

    if completed_tickets:
        service_times = [
            (t.completed_at - t.served_at).total_seconds() / 60
            for t in completed_tickets
            if t.completed_at and t.served_at
        ]
        avg_service_time = sum(service_times) / len(service_times) if service_times else 0
    else:
        avg_service_time = 0

    return StatisticsResponse(
        total_tickets_today=total_tickets_today,
        total_served_today=total_served_today,
        total_waiting=total_waiting,
        total_expired=total_expired,
        active_counters=active_counters,
        average_service_time_minutes=round(avg_service_time, 2),
        peak_hour=None  # Can be calculated with more data
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        reload=False
    )

