# reminder_scheduler.py
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """
    Scheduler for managing appointment reminders.
    Sends reminders 2 days before appointments.
    """

    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
        logger.info("✅ Reminder scheduler initialized")

    def schedule_appointment_reminder(
        self,
        chat_id: str,
        ticket_number: str,
        appointment_date: str,  # Format: YYYY-MM-DD
        reminder_callback: Callable,
        queue_name: str,
        appointment_time: Optional[str] = None,
        service_counter: Optional[str] = None,
        instructions: Optional[str] = None,
        timezone: str = "UTC",
    ) -> bool:
        """
        Schedule a reminder for 2 days before appointment.

        Args:
            chat_id (str): User's Telegram chat ID
            ticket_number (str): Ticket number
            appointment_date (str): Appointment date (YYYY-MM-DD)
            reminder_callback (Callable): Function to call when reminder is due
            queue_name (str): Name of the queue
            appointment_time (str, optional): Appointment time (HH:MM)
            service_counter (str, optional): Counter number
            instructions (str, optional): Special instructions
            timezone (str): User's timezone

        Returns:
            bool: True if scheduled successfully
        """
        try:
            # Parse appointment date
            appointment_dt = datetime.strptime(appointment_date, "%Y-%m-%d")

            # Calculate reminder date (2 days before)
            reminder_dt = appointment_dt - timedelta(days=2)

            # Set reminder time to 9:00 AM
            reminder_dt = reminder_dt.replace(hour=9, minute=0, second=0)

            # Create job ID
            job_id = f"reminder_{ticket_number}_{chat_id}"

            # Check if appointment is in the future
            if appointment_dt <= datetime.now():
                logger.warning(f"⚠️ Appointment date {appointment_date} is in the past")
                return False

            # Schedule the job
            self.scheduler.add_job(
                func=reminder_callback,
                trigger="date",
                run_date=reminder_dt,
                args=[
                    chat_id,
                    ticket_number,
                    queue_name,
                    appointment_date,
                    appointment_time,
                    service_counter,
                    instructions,
                ],
                id=job_id,
                name=f"Reminder for {ticket_number}",
                replace_existing=True,
            )

            logger.info(
                f"✅ Reminder scheduled for ticket {ticket_number} "
                f"on {reminder_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            return True

        except ValueError as e:
            logger.error(f"❌ Invalid date format: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Error scheduling reminder: {str(e)}")
            return False

    def cancel_reminder(self, ticket_number: str, chat_id: str) -> bool:
        """
        Cancel a scheduled reminder.

        Args:
            ticket_number (str): Ticket number
            chat_id (str): User's chat ID

        Returns:
            bool: True if cancelled successfully
        """
        try:
            job_id = f"reminder_{ticket_number}_{chat_id}"
            self.scheduler.remove_job(job_id)
            logger.info(f"✅ Reminder cancelled for ticket {ticket_number}")
            return True
        except Exception as e:
            logger.error(f"❌ Error cancelling reminder: {str(e)}")
            return False

    def get_scheduled_reminders(self) -> list:
        """Get all scheduled reminders."""
        return [
            {"job_id": job.id, "name": job.name, "next_run": job.next_run_time}
            for job in self.scheduler.get_jobs()
        ]

    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("✅ Reminder scheduler shutdown")
        else:
            logger.debug("Scheduler was not running, skipping shutdown")
