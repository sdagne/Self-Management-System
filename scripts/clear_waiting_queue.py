"""Utility to clear tickets stuck in waiting state for cleanup/testing."""

import os
import sys

# Allow running from scripts/ by adding the repo root to sys.path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from datetime import datetime

from sqlalchemy import create_engine, text

from config import settings


def get_engine():
    connect_args = {"check_same_thread": False} if "sqlite" in settings.database_url else {}
    return create_engine(settings.database_url, connect_args=connect_args)


def main():
    engine = get_engine()
    now = datetime.utcnow().isoformat()

    with engine.connect() as conn:
        result = conn.execute(
            text("UPDATE tickets SET status='cancelled', completed_at=:now WHERE status='waiting'"),
            {"now": now},
        )
        conn.commit()
        updated = result.rowcount

    if updated:
        print(f"Cleared {updated} waiting ticket(s).")
    else:
        print("No waiting tickets found.")


if __name__ == "__main__":
    main()
