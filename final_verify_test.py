import requests
import sys

API_BASE = "http://localhost:8001"


def test_flow():
    print(f"--- Starting Final Verification Test ---")

    # 1. Create ticket
    payload = {
        "id_number": "V-FINAL-TEST-1",
        "full_name": "Verification User",
        "service_type": "kebele_id",
    }
    resp = requests.post(f"{API_BASE}/api/tickets", json=payload)
    if resp.status_code != 201:
        print(f"Error creating ticket: {resp.text}")
        return
    ticket = resp.json()
    ticket_num = ticket["ticket_number"]
    print(f"Ticket Created: {ticket_num}")

    # 2. Verify it's in display waiting list
    resp = requests.get(f"{API_BASE}/api/display/waiting-tickets")
    waiting = resp.json()["tickets"]
    if any(t["ticket_number"] == ticket_num for t in waiting):
        print(f"Ticket {ticket_num} found in Waiting List API")
    else:
        print(f"Ticket {ticket_num} NOT in Waiting List API!")

    # 3. Call ticket from Counter 1
    resp = requests.post(f"{API_BASE}/api/counters/1/call-next")
    if resp.status_code != 200:
        print(f"Error calling ticket: {resp.text}")
        return
    call_data = resp.json()
    if call_data.get("ticket_number") == ticket_num:
        print(f"Ticket {ticket_num} successfully called by Counter 1")
    else:
        print(f"Failed to call {ticket_num}. Server returned: {call_data}")
        return

    # 4. Verify it's in Display NOW SERVING
    resp = requests.get(f"{API_BASE}/api/display/queue-status")
    serving = resp.json()["now_serving"]
    if any(t["ticket_number"] == ticket_num for t in serving):
        print(f"Ticket {ticket_num} confirmed in NOW SERVING display API")
    else:
        print(f"Ticket {ticket_num} NOT in NOW SERVING display API!")

    print(f"--- Verification Successful ---")


if __name__ == "__main__":
    test_flow()
