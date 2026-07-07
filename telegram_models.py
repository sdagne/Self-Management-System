# telegram_models.py
from pydantic import BaseModel
from typing import Optional


class TelegramUserRegister(BaseModel):
    """Request model to register user's Telegram chat ID"""

    id_number: str
    phone_number: str
    telegram_chat_id: str
    full_name: str


class TelegramNotificationResponse(BaseModel):
    """Response for Telegram operations"""

    status: str
    message: str
    ticket_number: Optional[str] = None
    reminder_scheduled: Optional[bool] = None
    appointment_date: Optional[str] = None
