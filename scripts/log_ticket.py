import json
import uuid
from pathlib import Path
import requests
import sys

API_BASE = "http://localhost:8001/api"
LOG_FILE = Path(__file__).parent / "ticket_history.json"


def ensure_log():
    if not LOG_FILE.exists():
        LOG_FILE.write_text("[]")


def append_record(record):
    data = json.loads(LOG_FILE.read_text())
    data.append(record)
    LOG_FILE.write_text(json.dumps(data, indent=2))


def create_ticket(id_number: str | None = None):
    payload = {
        "id_number": id_number or f"EP{uuid.uuid4().hex[:6]}",
        "full_name": "Test User",
        "service_type": "land_registration",
        "phone_number": "+251911234567",
    }
    try:
        response = requests.post(f"{API_BASE}/tickets", json=payload)
        response.raise_for_status()
    except requests.RequestException as exc:
        print("Could not create ticket:", exc)
        sys.exit(1)

    ticket = response.json()
    record = {
        "ticket_number": ticket["ticket_number"],
        "id_number": payload["id_number"],
        "created_at": ticket.get("created_at"),
    }
    append_record(record)
    print("Ticket created:", record)
    return record


def main():
    ensure_log()
    id_input = None
    if len(sys.argv) > 1:
        id_input = sys.argv[1]
    create_ticket(id_input)


if __name__ == "__main__":
    main()
