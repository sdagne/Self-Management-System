# telegram_routes.py
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db, Citizen
from telegram_models import TelegramUserRegister
from queue_telegram_integration import QueueTelegramIntegration
from config import settings
from utils import hash_id_number

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

# Initialize Telegram integration
telegram_integration = None


def get_telegram_integration():
    """Get or initialize Telegram integration"""
    global telegram_integration
    if telegram_integration is None and settings.TELEGRAM_ENABLED:
        telegram_integration = QueueTelegramIntegration(settings.TELEGRAM_BOT_TOKEN)
    return telegram_integration


@router.post("/register-user")
async def register_telegram_user(request: TelegramUserRegister, db: Session = Depends(get_db)):
    """
    Register user's Telegram chat ID for notifications.
    User must provide this to receive ticket notifications.

    Args:
        request: Contains ID number, phone, Telegram chat ID, and full name

    Returns:
        Success/failure response
    """
    if not settings.TELEGRAM_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram notifications are not enabled",
        )

    try:
        # Hash ID for privacy
        id_hash = hash_id_number(request.id_number)

        # Get or create citizen
        citizen = db.query(Citizen).filter(Citizen.id_number_hash == id_hash).first()

        if not citizen:
            citizen = Citizen(
                id_number_hash=id_hash,
                full_name=request.full_name,
                phone_number=request.phone_number,
                telegram_chat_id=request.telegram_chat_id,
                telegram_notifications_enabled=True,
            )
            db.add(citizen)
        else:
            # Update existing citizen with Telegram ID
            citizen.telegram_chat_id = request.telegram_chat_id
            citizen.telegram_notifications_enabled = True

        db.commit()
        db.refresh(citizen)

        logger.info(f"✅ Telegram user registered: {request.telegram_chat_id}")

        return {
            "status": "success",
            "message": "Telegram chat ID registered successfully",
            "chat_id": request.telegram_chat_id,
        }

    except Exception as e:
        logger.error(f"❌ Error registering Telegram user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error registering Telegram user: {str(e)}",
        )


@router.post("/disable-notifications")
async def disable_telegram_notifications(id_number: str, db: Session = Depends(get_db)):
    """Disable Telegram notifications for a user"""
    try:
        id_hash = hash_id_number(id_number)
        citizen = db.query(Citizen).filter(Citizen.id_number_hash == id_hash).first()

        if not citizen:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        citizen.telegram_notifications_enabled = False
        db.commit()

        return {"status": "success", "message": "Telegram notifications disabled"}

    except Exception as e:
        logger.error(f"❌ Error disabling notifications: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/enable-notifications")
async def enable_telegram_notifications(id_number: str, db: Session = Depends(get_db)):
    """Enable Telegram notifications for a user"""
    try:
        id_hash = hash_id_number(id_number)
        citizen = db.query(Citizen).filter(Citizen.id_number_hash == id_hash).first()

        if not citizen:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        citizen.telegram_notifications_enabled = True
        db.commit()

        return {"status": "success", "message": "Telegram notifications enabled"}

    except Exception as e:
        logger.error(f"❌ Error enabling notifications: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
