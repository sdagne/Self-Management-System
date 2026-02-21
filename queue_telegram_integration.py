# queue_telegram_integration.py
import logging
from datetime import datetime
from typing import Optional, Dict
from telegram_service import TelegramService, send_registration_ticket_sync, send_appointment_reminder_sync
from reminder_scheduler import ReminderScheduler
import asyncio

logger = logging.getLogger(__name__)


class QueueTelegramIntegration:
    """
    Main integration class for queue management system with Telegram.
    """
    
    def __init__(self, bot_token: str):
        """
        Initialize the integration.
        
        Args:
            bot_token (str): Your Telegram bot token
        """
        self.telegram_service = TelegramService(bot_token)
        self.reminder_scheduler = ReminderScheduler()
        self.bot_token = bot_token
    
    async def register_ticket_async(
        self,
        chat_id: str,
        ticket_number: str,
        queue_name: str,
        appointment_date: Optional[str] = None,
        appointment_time: Optional[str] = None,
        estimated_wait_time: Optional[str] = None,
        service_counter: Optional[str] = None,
        instructions: Optional[str] = None
    ) -> Dict:
        """
        Register a ticket and send Telegram notification (async version).
        
        Args:
            chat_id (str): User's Telegram chat ID
            ticket_number (str): Generated ticket number
            queue_name (str): Queue/service name
            appointment_date (str, optional): Appointment date (YYYY-MM-DD)
            appointment_time (str, optional): Appointment time (HH:MM)
            estimated_wait_time (str, optional): Estimated wait time
            service_counter (str, optional): Counter number
            instructions (str, optional): Special instructions
            
        Returns:
            Dict: Result with status and details
        """
        try:
            # Send registration notification
            success = await self.telegram_service.send_registration_ticket(
                chat_id=chat_id,
                ticket_number=ticket_number,
                queue_name=queue_name,
                appointment_date=appointment_date,
                estimated_wait_time=estimated_wait_time,
                service_counter=service_counter
            )
            
            if not success:
                return {
                    'status': 'error',
                    'message': 'Failed to send Telegram notification',
                    'ticket_number': ticket_number
                }
            
            # If appointment is booked in advance, schedule reminder
            if appointment_date:
                reminder_scheduled = self.reminder_scheduler.schedule_appointment_reminder(
                    chat_id=chat_id,
                    ticket_number=ticket_number,
                    appointment_date=appointment_date,
                    reminder_callback=self._send_reminder_callback,
                    queue_name=queue_name,
                    appointment_time=appointment_time,
                    service_counter=service_counter,
                    instructions=instructions
                )
                
                return {
                    'status': 'success',
                    'message': 'Ticket registered and notification sent',
                    'ticket_number': ticket_number,
                    'reminder_scheduled': reminder_scheduled,
                    'appointment_date': appointment_date
                }
            
            return {
                'status': 'success',
                'message': 'Ticket registered and notification sent',
                'ticket_number': ticket_number,
                'reminder_scheduled': False
            }
            
        except Exception as e:
            logger.error(f"❌ Error registering ticket: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error: {str(e)}',
                'ticket_number': ticket_number
            }
    
    def register_ticket_sync(
        self,
        chat_id: str,
        ticket_number: str,
        queue_name: str,
        appointment_date: Optional[str] = None,
        appointment_time: Optional[str] = None,
        estimated_wait_time: Optional[str] = None,
        service_counter: Optional[str] = None,
        instructions: Optional[str] = None
    ) -> Dict:
        """
        Register a ticket and send Telegram notification (sync version).
        Use this if your code doesn't support async/await.
        """
        try:
            # Send registration notification
            success = send_registration_ticket_sync(
                bot_token=self.bot_token,
                chat_id=chat_id,
                ticket_number=ticket_number,
                queue_name=queue_name,
                appointment_date=appointment_date,
                estimated_wait_time=estimated_wait_time,
                service_counter=service_counter
            )
            
            if not success:
                return {
                    'status': 'error',
                    'message': 'Failed to send Telegram notification',
                    'ticket_number': ticket_number
                }
            
            # If appointment is booked in advance, schedule reminder
            if appointment_date:
                reminder_scheduled = self.reminder_scheduler.schedule_appointment_reminder(
                    chat_id=chat_id,
                    ticket_number=ticket_number,
                    appointment_date=appointment_date,
                    reminder_callback=self._send_reminder_callback,
                    queue_name=queue_name,
                    appointment_time=appointment_time,
                    service_counter=service_counter,
                    instructions=instructions
                )
                
                return {
                    'status': 'success',
                    'message': 'Ticket registered and notification sent',
                    'ticket_number': ticket_number,
                    'reminder_scheduled': reminder_scheduled,
                    'appointment_date': appointment_date
                }
            
            return {
                'status': 'success',
                'message': 'Ticket registered and notification sent',
                'ticket_number': ticket_number,
                'reminder_scheduled': False
            }
            
        except Exception as e:
            logger.error(f"❌ Error registering ticket: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error: {str(e)}',
                'ticket_number': ticket_number
            }
    
    def _send_reminder_callback(
        self,
        chat_id: str,
        ticket_number: str,
        queue_name: str,
        appointment_date: str,
        appointment_time: Optional[str] = None,
        service_counter: Optional[str] = None,
        instructions: Optional[str] = None
    ):
        """
        Callback function for sending reminders.
        Called by the scheduler.
        """
        try:
            success = send_appointment_reminder_sync(
                bot_token=self.bot_token,
                chat_id=chat_id,
                ticket_number=ticket_number,
                queue_name=queue_name,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                service_counter=service_counter,
                instructions=instructions
            )
            
            if success:
                logger.info(f"✅ Reminder sent to {chat_id}")
            else:
                logger.error(f"❌ Failed to send reminder to {chat_id}")
                
        except Exception as e:
            logger.error(f"❌ Error in reminder callback: {str(e)}")
    
    def cancel_appointment_reminder(self, ticket_number: str, chat_id: str) -> bool:
        """Cancel an appointment reminder."""
        return self.reminder_scheduler.cancel_reminder(ticket_number, chat_id)
    
    def get_all_scheduled_reminders(self) -> list:
        """Get all scheduled reminders."""
        return self.reminder_scheduler.get_scheduled_reminders()
    
    def shutdown(self):
        """Shutdown the integration."""
        self.reminder_scheduler.shutdown()
