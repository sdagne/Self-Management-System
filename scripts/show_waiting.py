import requests
import sys

API_BASE = "http://localhost:8001/api"


def fetch_waiting_tickets():
    try:
        response = requests.get(f"{API_BASE}/display/waiting-tickets")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        print("Failed to reach the API:", exc)
        sys.exit(1)


def display_tickets(data):
    tickets = data.get("tickets", [])
    if not tickets:
        print("No waiting tickets found.")
        return

    widths = [10, 15, 24, 10]
    header = ["Position", "Ticket", "ID Number", "Service", "Created"]
    fmt = "{:<10} {:<15} {:<24} {:<20} {:<20}"
    print(fmt.format(*header))
    print("-" * 90)

    for ticket in tickets:
        created = ticket.get("created_at", "-")
        print(
            fmt.format(
                ticket.get("position", "-"),
                ticket.get("ticket_number", "-"),
                ticket.get("id_number_display", "-"),
                ticket.get("service_type", "-"),
                created,
            )
        )


if __name__ == "__main__":
    payload = fetch_waiting_tickets()
    display_tickets(payload)

