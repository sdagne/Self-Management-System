# telegram_service.py
import logging
from typing import Optional

from telegram import Bot
from telegram.error import TelegramError
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class TelegramService:
    """
    Service for sending Telegram messages for queue management system.
    Handles ticket registration notifications and appointment reminders.
    """

    def __init__(self, bot_token: str):
        """
        Initialize Telegram service.

        Args:
            bot_token (str): Your Telegram bot token from BotFather
        """
        self.bot = Bot(token=bot_token)
        self.bot_token = bot_token

    async def send_registration_ticket(
        self,
        chat_id: str,
        ticket_number: str,
        queue_name: str,
        appointment_date: Optional[str] = None,
        estimated_wait_time: Optional[str] = None,
        service_counter: Optional[str] = None,
    ) -> bool:
        """
        Send ticket registration confirmation to user via Telegram.

        Args:
            chat_id (str): User's Telegram chat ID
            ticket_number (str): Generated ticket number
            queue_name (str): Name of the queue/service
            appointment_date (str, optional): Appointment date if booked in advance
            estimated_wait_time (str, optional): Estimated wait time
            service_counter (str, optional): Counter number

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            # Build the message
            message = self._build_registration_message(
                ticket_number=ticket_number,
                queue_name=queue_name,
                appointment_date=appointment_date,
                estimated_wait_time=estimated_wait_time,
                service_counter=service_counter,
            )

            # Send the message
            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")

            logger.info(f"✅ Registration ticket sent to {chat_id} - Ticket: {ticket_number}")
            return True

        except TelegramError as e:
            logger.error(f"❌ Failed to send registration ticket to {chat_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending registration ticket: {str(e)}")
            return False

    async def send_appointment_reminder(
        self,
        chat_id: str,
        ticket_number: str,
        queue_name: str,
        appointment_date: str,
        appointment_time: Optional[str] = None,
        service_counter: Optional[str] = None,
        instructions: Optional[str] = None,
    ) -> bool:
        """
        Send appointment reminder 2 days before the appointment.

        Args:
            chat_id (str): User's Telegram chat ID
            ticket_number (str): Ticket number
            queue_name (str): Name of the queue/service
            appointment_date (str): Appointment date (YYYY-MM-DD format)
            appointment_time (str, optional): Appointment time (HH:MM format)
            service_counter (str, optional): Counter number
            instructions (str, optional): Special instructions

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            message = self._build_reminder_message(
                ticket_number=ticket_number,
                queue_name=queue_name,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                service_counter=service_counter,
                instructions=instructions,
            )

            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")

            logger.info(
                f"✅ Reminder sent to {chat_id} - Ticket: {ticket_number} - Date: {appointment_date}"
            )
            return True

        except TelegramError as e:
            logger.error(f"❌ Failed to send reminder to {chat_id}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error sending reminder: {str(e)}")
            return False

    async def send_custom_message(self, chat_id: str, message: str) -> bool:
        """
        Send a custom message to user.

        Args:
            chat_id (str): User's Telegram chat ID
            message (str): Message to send

        Returns:
            bool: True if message sent successfully, False otherwise
        """
        try:
            await self.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
            logger.info(f"✅ Custom message sent to {chat_id}")
            return True
        except TelegramError as e:
            logger.error(f"❌ Failed to send custom message to {chat_id}: {str(e)}")
            return False

    @staticmethod
    def _build_registration_message(
        ticket_number: str,
        queue_name: str,
        appointment_date: Optional[str] = None,
        estimated_wait_time: Optional[str] = None,
        service_counter: Optional[str] = None,
    ) -> str:
        """Build formatted registration message."""
        message = f"""
<b>🎫 Ticket Registered Successfully!</b>

<b>Queue:</b> {queue_name}
<b>Ticket Number:</b> <code>{ticket_number}</code>
"""

        if appointment_date:
            message += f"<b>📅 Appointment Date:</b> {appointment_date}\n"

        if appointment_date is None:
            message += f"<b>⏱️ Estimated Wait Time:</b> {estimated_wait_time or 'Calculating...'}\n"

        if service_counter:
            message += f"<b>🏪 Service Counter:</b> {service_counter}\n"

        message += """
<b>📌 Please keep this ticket number safe.</b>
You will be notified when it's your turn.

Thank you for using our service! 😊
"""
        return message

    @staticmethod
    def _build_reminder_message(
        ticket_number: str,
        queue_name: str,
        appointment_date: str,
        appointment_time: Optional[str] = None,
        service_counter: Optional[str] = None,
        instructions: Optional[str] = None,
    ) -> str:
        """Build formatted reminder message."""
        message = f"""
<b>⏰ Appointment Reminder!</b>

Your appointment is coming up in 2 days!

<b>Queue:</b> {queue_name}
<b>Ticket Number:</b> <code>{ticket_number}</code>
<b>📅 Appointment Date:</b> {appointment_date}
"""

        if appointment_time:
            message += f"<b>🕐 Appointment Time:</b> {appointment_time}\n"

        if service_counter:
            message += f"<b>🏪 Service Counter:</b> {service_counter}\n"

        if instructions:
            message += f"\n<b>📋 Instructions:</b>\n{instructions}\n"

        message += """
<b>Please arrive 5-10 minutes early.</b>

If you need to reschedule, please contact us as soon as possible.

See you soon! 👋
"""
        return message

    async def verify_chat_id(self, chat_id: str) -> bool:
        """
        Verify if a chat ID is valid by sending a test message.

        Args:
            chat_id (str): Chat ID to verify

        Returns:
            bool: True if valid, False otherwise
        """
        try:
            await self.bot.send_message(chat_id=chat_id, text="✅ Telegram connection verified!")
            logger.info(f"✅ Chat ID verified: {chat_id}")
            return True
        except TelegramError as e:
            logger.error(f"❌ Invalid chat ID {chat_id}: {str(e)}")
            return False


# Synchronous wrapper for compatibility with non-async code
def send_registration_ticket_sync(
    bot_token: str,
    chat_id: str,
    ticket_number: str,
    queue_name: str,
    appointment_date: Optional[str] = None,
    estimated_wait_time: Optional[str] = None,
    service_counter: Optional[str] = None,
) -> bool:
    """
    Synchronous wrapper for sending registration ticket.
    Use this if your code doesn't support async/await.
    """
    try:
        service = TelegramService(bot_token)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            service.send_registration_ticket(
                chat_id=chat_id,
                ticket_number=ticket_number,
                queue_name=queue_name,
                appointment_date=appointment_date,
                estimated_wait_time=estimated_wait_time,
                service_counter=service_counter,
            )
        )
    except Exception as e:
        logger.error(f"Error in sync wrapper: {str(e)}")
        return False


def send_appointment_reminder_sync(
    bot_token: str,
    chat_id: str,
    ticket_number: str,
    queue_name: str,
    appointment_date: str,
    appointment_time: Optional[str] = None,
    service_counter: Optional[str] = None,
    instructions: Optional[str] = None,
) -> bool:
    """
    Synchronous wrapper for sending appointment reminder.
    Use this if your code doesn't support async/await.
    """
    try:
        service = TelegramService(bot_token)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            service.send_appointment_reminder(
                chat_id=chat_id,
                ticket_number=ticket_number,
                queue_name=queue_name,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                service_counter=service_counter,
                instructions=instructions,
            )
        )
    except Exception as e:
        logger.error(f"Error in sync wrapper: {str(e)}")
        return False
