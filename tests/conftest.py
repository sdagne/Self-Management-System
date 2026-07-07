"""
Shared test fixtures for Queue Management System.

Uses an in-memory SQLite database so tests are:
  - Fast (no real Postgres needed locally)
  - Isolated (each test session gets a fresh DB)
  - Independent (no server process required)
"""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- Force test environment before importing app modules ---
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_queue.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("ADMIN_TOKEN", "test-admin-token")
os.environ.setdefault("COUNTER_TOKEN", "test-counter-token")
os.environ.setdefault("DISPLAY_TOKEN", "test-display-token")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:8001")
os.environ.setdefault("APP_ENV", "development")

from database import Base, get_db  # noqa: E402
from main import app  # noqa: E402

# ── In-memory test database ─────────────────────────────────────────────────
TEST_DB_URL = "sqlite:///./test_queue.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def setup_test_db(request):
    """Create all tables once for the test session, drop them afterwards."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    # Clean up the test DB file
    import pathlib

    # This may fail on Windows if the file is still locked, but it's not critical
    try:
        pathlib.Path("./test_queue.db").unlink(missing_ok=True)
    except PermissionError:
        print("Could not remove test_queue.db on teardown (likely locked).")


@pytest.fixture(scope="function")
def client():
    """
    Return a TestClient with the DB dependency overridden.
    Using "function" scope ensures the lifespan events run for each test.
    """
    # Reset the database before each test
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_headers():
    """Authorization header using the test admin token."""
    return {"Authorization": "Bearer test-admin-token"}


@pytest.fixture()
def counter_headers():
    """Authorization header using the test counter token."""
    return {"Authorization": "Bearer test-counter-token"}


@pytest.fixture()
def ticket_payload():
    """Valid ticket creation payload."""
    return {
        "id_number": "ETH-TEST-001",
        "full_name": "Tesfaye Bekele",
        "service_type": "immigration",
        "phone_number": "+251911234567",
    }
