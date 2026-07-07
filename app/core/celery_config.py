"""Celery configuration for async task processing."""

import os
from celery import Celery
from kombu import Exchange, Queue

# Celery app instance
celery_app = Celery(
    "queue_management",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Africa/Addis_Ababa",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    # Task routes
    task_routes={
        "app.services.tasks.send_telegram_notification": {"queue": "notifications"},
        "app.services.tasks.send_telegram_reminder": {"queue": "notifications"},
        "app.services.tasks.cleanup_expired_tickets": {"queue": "maintenance"},
        "app.services.tasks.generate_daily_report": {"queue": "reports"},
    },
    # Queue definitions
    task_queues=(
        Queue("default", Exchange("default"), routing_key="default"),
        Queue("notifications", Exchange("notifications"), routing_key="notifications"),
        Queue("maintenance", Exchange("maintenance"), routing_key="maintenance"),
        Queue("reports", Exchange("reports"), routing_key="reports"),
    ),
    # Beat schedule for periodic tasks
    beat_schedule={
        "cleanup-expired-tickets-every-hour": {
            "task": "app.services.tasks.cleanup_expired_tickets",
            "schedule": 3600.0,  # Every hour
        },
        "generate-daily-report": {
            "task": "app.services.tasks.generate_daily_report",
            "schedule": 86400.0,  # Every day
            "options": {"expires": 3600},
        },
    },
)

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.services"])
