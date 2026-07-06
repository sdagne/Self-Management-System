"""
Configuration settings for Queue Management System
"""
from pydantic_settings import BaseSettings
from typing import Optional
from dotenv import load_dotenv
import os
load_dotenv()

class Settings(BaseSettings):
    """Application settings — all secrets must be supplied via environment variables."""

    # Database
    database_url: str = "sqlite:///./queue_management.db"

    # Security — NEVER commit real values; supply via .env or secret manager
    secret_key: str = "CHANGE_ME_BEFORE_FIRST_RUN"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # API Tokens — loaded from env, no defaults in code
    admin_token: str = ""
    counter_token: str = ""
    display_token: str = ""

    @property
    def api_tokens(self) -> dict[str, str]:
        """Build token → role map at runtime from env-supplied tokens."""
        tokens: dict[str, str] = {}
        if self.admin_token:
            tokens["admin"] = self.admin_token
        if self.counter_token:
            tokens["counter"] = self.counter_token
        if self.display_token:
            tokens["display"] = self.display_token
        return tokens

    # CORS — comma-separated list of allowed origins
    cors_origins: str = "http://localhost:8001,http://127.0.0.1:8001"

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # Rate Limiting (requests per minute per IP)
    rate_limit_tickets: str = "10/minute"
    rate_limit_default: str = "60/minute"

    # Ticket Configuration
    ticket_expiry_hours: int = 2
    max_queue_size: int = 500

    # Server
    host: str = "0.0.0.0"
    port: int = 8001
    app_env: str = "development"  # development | production

    # Application
    app_name: str = "SAN - Queue Management System"
    version: str = "1.0.0"

    # Telegram Integration
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_ENABLED: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


settings = Settings()

# Guard: warn loudly if using the placeholder secret key
if settings.secret_key == "CHANGE_ME_BEFORE_FIRST_RUN":
    import warnings
    warnings.warn(
        "\n⚠️  SECRET_KEY is not set! Set SECRET_KEY in your .env file before running in production.",
        stacklevel=2,
    )

