"""Async tasks for background processing using Celery."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any
from celery import Task

from app.core.celery_config import celery_app

logger = logging.getLogger(__name__)


class DatabaseTask(Task):
    """Base task with database session management."""
    
    _db = None
    
    @property
    def db(self):
        if self._db is None:
            from app.db.database import SessionLocal
            self._db = SessionLocal()
        return self._db
    
    def after_return(self, *args, **kwargs):
        if self._db is not None:
            self._db.close()
            self._db = None


@celery_app.task(
    name="app.services.tasks.send_telegram_notification",
    bind=True,
    base=DatabaseTask,
    max_retries=3,
    default_retry_delay=60,
)
def send_telegram_notification(
    self,
    chat_id: str,
    message: str,
    ticket_number: str = None,
) -> Dict[str, Any]:
    """
    Send Telegram notification asynchronously.
    
    Args:
        chat_id: Telegram chat ID
        message: Message to send
        ticket_number: Optional ticket number for context
        
    Returns:
        Dict with status and message
    """
    try:
        from telegram_service import TelegramService
        
        telegram_service = TelegramService()
        result = telegram_service.send_message(chat_id, message)
        
        logger.info(
            f"✅ Telegram notification sent to {chat_id}"
            f"{f' for ticket {ticket_number}' if ticket_number else ''}"
        )
        
        return {
            "status": "success",
            "chat_id": chat_id,
            "ticket_number": ticket_number,
            "sent_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        logger.error(f"❌ Failed to send Telegram notification: {exc}")
        
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)


@celery_app.task(
    name="app.services.tasks.send_telegram_reminder",
    bind=True,
    base=DatabaseTask,
    max_retries=2,
)
def send_telegram_reminder(self, ticket_id: int) -> Dict[str, Any]:
    """
    Send reminder for waiting tickets.
    
    Args:
        ticket_id: Database ID of the ticket
        
    Returns:
        Dict with status and details
    """
    try:
        from app.db.database import Ticket
        
        ticket = self.db.query(Ticket).filter(Ticket.id == ticket_id).first()
        
        if not ticket or not ticket.telegram_chat_id:
            return {"status": "skipped", "reason": "No telegram chat ID"}
        
        if ticket.status != "waiting":
            return {"status": "skipped", "reason": f"Ticket status is {ticket.status}"}
        
        # Calculate position in queue
        queue_position = self.db.query(Ticket).filter(
            Ticket.service_type == ticket.service_type,
            Ticket.status == "waiting",
            Ticket.created_at < ticket.created_at
        ).count() + 1
        
        message = (
            f"🔔 *Reminder for Ticket {ticket.ticket_number}*\n\n"
            f"Your position in queue: *{queue_position}*\n"
            f"Estimated wait time: {queue_position * 5} minutes\n\n"
            f"Please be ready when your number is called!"
        )
        
        send_telegram_notification.delay(
            ticket.telegram_chat_id,
            message,
            ticket.ticket_number
        )
        
        return {
            "status": "success",
            "ticket_id": ticket_id,
            "queue_position": queue_position,
        }
        
    except Exception as exc:
        logger.error(f"❌ Failed to send reminder for ticket {ticket_id}: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="app.services.tasks.cleanup_expired_tickets",
    bind=True,
    base=DatabaseTask,
)
def cleanup_expired_tickets(self) -> Dict[str, Any]:
    """
    Clean up expired tickets (maintenance task).
    
    Returns:
        Dict with cleanup statistics
    """
    try:
        from app.db.database import Ticket, TicketStatus, AuditLog
        
        expiry_threshold = datetime.utcnow() - timedelta(hours=24)
        
        # Find expired waiting tickets
        expired_tickets = self.db.query(Ticket).filter(
            Ticket.status == TicketStatus.WAITING,
            Ticket.created_at < expiry_threshold
        ).all()
        
        expired_count = len(expired_tickets)
        
        for ticket in expired_tickets:
            ticket.status = TicketStatus.EXPIRED
            
            # Create audit log
            audit_log = AuditLog(
                action="TICKET_EXPIRED",
                performed_by="system",
                details=f"Ticket {ticket.ticket_number} auto-expired after 24h",
                ticket_id=ticket.id,
            )
            self.db.add(audit_log)
            
            # Notify user if they have Telegram
            if ticket.telegram_chat_id:
                send_telegram_notification.delay(
                    ticket.telegram_chat_id,
                    f"⏰ Your ticket {ticket.ticket_number} has expired. "
                    f"Please request a new ticket if you still need service.",
                    ticket.ticket_number
                )
        
        self.db.commit()
        
        logger.info(f"✅ Cleaned up {expired_count} expired tickets")
        
        return {
            "status": "success",
            "expired_count": expired_count,
            "cleaned_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as exc:
        self.db.rollback()
        logger.error(f"❌ Cleanup task failed: {exc}")
        raise


@celery_app.task(
    name="app.services.tasks.generate_daily_report",
    bind=True,
    base=DatabaseTask,
)
def generate_daily_report(self) -> Dict[str, Any]:
    """
    Generate daily statistics report.
    
    Returns:
        Dict with report data
    """
    try:
        from app.db.database import Ticket, Counter
        from sqlalchemy import func
        
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Collect statistics
        total_tickets = self.db.query(func.count(Ticket.id)).filter(
            Ticket.created_at >= today_start
        ).scalar()
        
        completed_tickets = self.db.query(func.count(Ticket.id)).filter(
            Ticket.created_at >= today_start,
            Ticket.status == "completed"
        ).scalar()
        
        avg_wait_time = self.db.query(
            func.avg(
                func.extract('epoch', Ticket.updated_at - Ticket.created_at) / 60
            )
        ).filter(
            Ticket.created_at >= today_start,
            Ticket.status == "completed"
        ).scalar() or 0
        
        active_counters = self.db.query(func.count(Counter.id)).filter(
            Counter.is_active == True
        ).scalar()
        
        report = {
            "date": today_start.isoformat(),
            "total_tickets": total_tickets,
            "completed_tickets": completed_tickets,
            "pending_tickets": total_tickets - completed_tickets,
            "completion_rate": (completed_tickets / total_tickets * 100) if total_tickets > 0 else 0,
            "avg_wait_time_minutes": round(avg_wait_time, 2),
            "active_counters": active_counters,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
        logger.info(f"📊 Daily report generated: {report}")
        
        # TODO: Send report to administrators via Telegram or email
        
        return report
        
    except Exception as exc:
        logger.error(f"❌ Report generation failed: {exc}")
        raise
