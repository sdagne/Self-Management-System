import requests
import sqlite3
import datetime

API_BASE = "http://localhost:8001"

def debug_data():
    print("--- Creating Test Ticket ---")
    payload = {
        "id_number": "DBG-999",
        "full_name": "Debug User",
        "service_type": "kebele_id"
    }
    resp = requests.post(f"{API_BASE}/api/tickets", json=payload)
    if resp.status_code != 201:
        print(f"Error: {resp.text}")
        return
    ticket_num = resp.json()["ticket_number"]
    print(f"Created {ticket_num}")

    print("\n--- Inspecting Raw Database Row ---")
    conn = sqlite3.connect('queue_management.db')
    c = conn.cursor()
    c.execute("SELECT * FROM tickets WHERE ticket_number=?", (ticket_num,))
    row = c.fetchone()
    columns = [description[0] for description in c.description]
    data = dict(zip(columns, row))
    for k, v in data.items():
        print(f"{k}: {repr(v)} (Type: {type(v)})")

    print("\n--- Current UTC Time ---")
    print(f"Python datetime.utcnow(): {repr(datetime.datetime.utcnow())}")
    
    conn.close()

if __name__ == "__main__":
    debug_data()
