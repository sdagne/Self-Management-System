"""
Configuration settings for Queue Management System
"""
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
import os
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""

    # Database
    database_url: str = "sqlite:///./queue_management.db"
    api_tokens: dict[str, str] = {
        "admin": "admin-token",
        "counter": "counter-token",
        "display": "display-token"

    }

    # Security
    secret_key: str = "your-secret-key-change-in-production-09876543210"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Ticket Configuration
    ticket_expiry_hours: int = 2
    max_queue_size: int = 500

    # Server
    host: str = "0.0.0.0"
    port: int = 8001

    # Application
    app_name: str = "SAN - Queue Management System"
    version: str = "1.0.0"

    # Telegram Integration
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ENABLED: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

