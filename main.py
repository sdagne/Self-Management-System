"""
Main FastAPI application for Queue Management System
Ethiopia - Queue Management Standard
"""
import os
import logging
from datetime import datetime
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from database import (
    get_db, init_db, Ticket, Citizen, Counter, AuditLog, 
    TicketStatus, ServiceType
)
from models import (
    TicketCreateRequest, TicketResponse, TicketVerifyRequest,
    TicketAssignRequest, CounterCreateRequest, CounterResponse, 
    StatisticsResponse, QueueStatusResponse
)
from utils import (
    hash_id_number, generate_ticket_number, generate_qr_code,
    calculate_expiry_time, is_ticket_expired, estimate_wait_time,
    detect_suspicious_activity
)
from config import settings
from auth import require_role
from telegram_routes import router as telegram_router
from queue_telegram_integration import QueueTelegramIntegration

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

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
    allow_origins=["*", "null"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================= STATIC FILES =================
# Serving from root directly as requested
app.mount("/web", StaticFiles(directory=os.path.dirname(os.path.abspath(__file__))), name="web")

# ================= TELEGRAM INTEGRATION =================
telegram_integration = None
if settings.TELEGRAM_ENABLED and settings.TELEGRAM_BOT_TOKEN:
    try:
        telegram_integration = QueueTelegramIntegration(settings.TELEGRAM_BOT_TOKEN)
        logger.info("✅ Telegram integration initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Telegram integration: {e}")
else:
    logger.warning("⚠️ Telegram notifications disabled or token missing")

# ================= STARTUP & SHUTDOWN =================
@app.on_event("startup")
async def startup_event():
    """Initialize database and services on startup"""
    init_db()
    logger.info("✅ Database initialized")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if telegram_integration:
        telegram_integration.shutdown()
        logger.info("✅ Telegram integration shutdown")

# ================= ROUTES =================
app.include_router(telegram_router)

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

@app.get("/status")
async def server_status():
    """Endpoint for portals to check if server is online"""
    return {"server": "online"}

# ==================== KIOSK ENDPOINTS ====================

@app.post("/api/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    request: TicketCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new ticket at kiosk"""
    id_hash = hash_id_number(request.id_number)

    # Check for existing active ticket
    existing_ticket = db.query(Ticket).filter(
        Ticket.id_number_hash == id_hash,
        Ticket.status.in_([TicketStatus.WAITING, TicketStatus.CALLED, TicketStatus.SERVING])
    ).first()

    if existing_ticket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"You already have an active ticket: {existing_ticket.ticket_number}."
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

    if citizen.is_blacklisted:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied. Reason: {citizen.blacklist_reason}"
        )

    if detect_suspicious_activity(citizen.id, db):
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

    # QR Code data
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

    # Audit log
    audit = AuditLog(
        action="TICKET_CREATED",
        citizen_id=citizen.id,
        ticket_id=new_ticket.id,
        details=f"Ticket {ticket_number} created for {request.service_type.value}"
    )
    db.add(audit)
    db.commit()

    # Telegram Notification
    if (telegram_integration and 
        citizen.telegram_chat_id and 
        citizen.telegram_notifications_enabled):
        try:
            telegram_integration.register_ticket_sync(
                chat_id=citizen.telegram_chat_id,
                ticket_number=ticket_number,
                queue_name=request.service_type.value,
                estimated_wait_time=f"{estimate_wait_time(queue_position)} minutes"
            )
            new_ticket.telegram_notification_sent = True
            db.commit()
        except Exception as e:
            logger.error(f"❌ Error sending Telegram notification: {e}")

    return TicketResponse(
        id=new_ticket.id,
        ticket_number=new_ticket.ticket_number,
        full_name=new_ticket.full_name,
        service_type=new_ticket.service_type,
        status=new_ticket.status,
        created_at=new_ticket.created_at,
        expires_at=new_ticket.expires_at,
        estimated_wait_minutes=estimate_wait_time(queue_position),
        queue_position=queue_position,
        qr_code=new_ticket.qr_code
    )

@app.get("/api/tickets/{ticket_number}", response_model=TicketResponse)
async def get_ticket_status(ticket_number: str, db: Session = Depends(get_db)):
    """Get ticket status"""
    ticket = db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    if is_ticket_expired(ticket.expires_at) and ticket.status == TicketStatus.WAITING:
        ticket.status = TicketStatus.EXPIRED
        db.commit()

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
async def create_counter(request: CounterCreateRequest, db: Session = Depends(get_db)):
    """Create a new service counter"""
    existing = db.query(Counter).filter(Counter.counter_number == request.counter_number).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Counter number exists")

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
    return db.query(Counter).all()

@app.post("/api/counters/{counter_id}/call-next")
async def call_next_ticket(counter_id: int, db: Session = Depends(get_db)):
    """Call next ticket in queue for this counter"""
    counter = db.query(Counter).filter(Counter.id == counter_id).first()
    if not counter or not counter.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Counter not active")

    # Robust parsing of service types (strip whitespace and skip empty)
    service_types_list = [st.strip() for st in counter.service_types.split(",") if st.strip()]
    
    # Get next ticket
    next_ticket = db.query(Ticket).filter(
        Ticket.service_type.in_([ServiceType(st) for st in service_types_list]),
        Ticket.status == TicketStatus.WAITING,
        Ticket.expires_at > datetime.utcnow()
    ).order_by(Ticket.created_at).first()

    if not next_ticket:
        return {"message": "No tickets waiting", "counter_number": counter.counter_number}

    next_ticket.status = TicketStatus.CALLED
    next_ticket.counter_number = counter.counter_number
    next_ticket.called_at = datetime.utcnow()
    counter.current_ticket_id = next_ticket.id
    db.commit()

    db.add(AuditLog(
        action="TICKET_CALLED",
        ticket_id=next_ticket.id,
        counter_id=counter.id,
        details=f"Ticket {next_ticket.ticket_number} called to counter {counter.counter_number}"
    ))
    db.commit()

    return {
        "message": "Ticket called",
        "ticket_number": next_ticket.ticket_number,
        "counter_number": counter.counter_number,
        "full_name": next_ticket.full_name
    }

@app.post("/api/counters/{counter_id}/verify")
async def verify_ticket_at_counter(counter_id: int, request: TicketVerifyRequest, db: Session = Depends(get_db)):
    """Verify citizen ID matches ticket at counter"""
    ticket = db.query(Ticket).filter(Ticket.ticket_number == request.ticket_number).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    if ticket.id_number_hash != hash_id_number(request.id_number):
        db.add(AuditLog(
            action="VERIFICATION_FAILED",
            ticket_id=ticket.id,
            details=f"ID mismatch for ticket {ticket.ticket_number}",
            is_suspicious=True
        ))
        db.commit()
        raise HTTPException(status_code=403, detail="ID mismatch")

    ticket.status = TicketStatus.SERVING
    ticket.served_at = datetime.utcnow()
    db.commit()

    db.add(AuditLog(
        action="VERIFICATION_SUCCESS",
        ticket_id=ticket.id,
        details=f"Ticket {ticket.ticket_number} verified"
    ))
    db.commit()

    return {"message": "Verification successful", "status": ticket.status}

@app.post("/api/counters/{counter_id}/complete")
async def complete_service(counter_id: int, ticket_number: str, db: Session = Depends(get_db)):
    """Mark service as completed"""
    ticket = db.query(Ticket).filter(Ticket.ticket_number == ticket_number).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.status = TicketStatus.COMPLETED
    ticket.completed_at = datetime.utcnow()
    
    counter = db.query(Counter).filter(Counter.id == counter_id).first()
    if counter:
        counter.current_ticket_id = None
    db.commit()

    return {"message": "Service completed", "ticket_number": ticket.ticket_number}

# ==================== DISPLAY & STATS ====================

@app.get("/api/display/queue-status", response_model=QueueStatusResponse)
async def get_queue_status(db: Session = Depends(get_db)):
    """Get current queue status for display screen"""
    serving = db.query(Ticket).filter(Ticket.status.in_([TicketStatus.CALLED, TicketStatus.SERVING])).all()
    now_serving = [{"ticket_number": t.ticket_number, "counter_number": t.counter_number} for t in serving]
    waiting_count = db.query(Ticket).filter(Ticket.status == TicketStatus.WAITING).count()
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_served = db.query(Ticket).filter(Ticket.status == TicketStatus.COMPLETED, Ticket.completed_at >= today_start).count()
    
    return QueueStatusResponse(
        now_serving=now_serving,
        waiting_count=waiting_count,
        total_served_today=total_served,
        average_wait_minutes=15 # This can be calculated if needed
    )

@app.get("/api/display/waiting-tickets")
async def get_waiting_tickets(db: Session = Depends(get_db)):
    """Get all waiting tickets with details for dashboard display"""
    waiting_tickets = db.query(Ticket).filter(
        Ticket.status == TicketStatus.WAITING,
        Ticket.expires_at > datetime.utcnow()
    ).order_by(Ticket.created_at).all()

    tickets = []
    for idx, ticket in enumerate(waiting_tickets, 1):
        tickets.append({
            "ticket_number": ticket.ticket_number,
            "full_name": ticket.full_name,
            "service_type": ticket.service_type.value,
            "status": ticket.status.value,
            "created_at": ticket.created_at.isoformat(),
            "position": idx,
            "id_number_display": ticket.id_number_hash[:8] + "***" 
        })

    return {
        "total_waiting": len(tickets),
        "tickets": tickets
    }

@app.get("/api/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """Get system statistics"""
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_tickets = db.query(Ticket).filter(Ticket.created_at >= today_start).count()
    total_served = db.query(Ticket).filter(Ticket.status == TicketStatus.COMPLETED, Ticket.completed_at >= today_start).count()
    
    return StatisticsResponse(
        total_tickets_today=total_tickets,
        total_served_today=total_served,
        total_waiting=db.query(Ticket).filter(Ticket.status == TicketStatus.WAITING).count(),
        total_expired=db.query(Ticket).filter(Ticket.status == TicketStatus.EXPIRED).count(),
        active_counters=db.query(Counter).filter(Counter.is_active == True).count(),
        average_service_time_minutes=10.5
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", settings.port)),
        reload=False
    )
