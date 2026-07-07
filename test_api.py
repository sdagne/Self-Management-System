"""
Test script for Queue Management System
Run this to test the API endpoints
"""

import requests
import time

BASE_URL = "http://localhost:8001"


def cleanup_old_tickets():
    """Clean up any stuck tickets from previous runs"""
    print("\n[CLEAN] Cleaning up old tickets...")
    test_ids = ["ETH001", "ETH002", "ETH003", "ABC123456", "TEST123"]

    cleaned = 0
    for id_number in test_ids:
        try:
            response = requests.delete(
                f"{BASE_URL}/api/tickets/cancel-by-id", params={"id_number": id_number}, timeout=3
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("cancelled_tickets"):
                    cleaned += len(result["cancelled_tickets"])
        except Exception:
            pass  # Ignore errors during cleanup

    if cleaned > 0:
        print(f"   Cleaned {cleaned} old ticket(s)")
    else:
        print("   No old tickets to clean")
    time.sleep(1)


def test_health_check():
    """Test health endpoint"""
    print("\n[CHECK] Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200


def test_create_ticket():
    """Test ticket creation"""
    print("\n[TICKET] Creating Ticket...")
    data = {
        "id_number": "ABC123456",
        "full_name": "Tesfaye Bekele",
        "service_type": "immigration",
        "phone_number": "+251911234567",
    }
    response = requests.post(f"{BASE_URL}/api/tickets", json=data)
    print(f"Status: {response.status_code}")
    if response.status_code == 201:
        ticket = response.json()
        print("[OK] Ticket Created!")
        print(f"   Ticket Number: {ticket['ticket_number']}")
        print(f"   Name: {ticket['full_name']}")
        print(f"   Service: {ticket['service_type']}")
        print(f"   Queue Position: {ticket['queue_position']}")
        print(f"   Estimated Wait: {ticket['estimated_wait_minutes']} minutes")
        return ticket
    else:
        print(f"[ERROR] Error: {response.json()}")
        return None


def test_get_ticket_status(ticket_number):
    """Test getting ticket status"""
    print(f"\n[STATUS] Getting Ticket Status for {ticket_number}...")
    response = requests.get(f"{BASE_URL}/api/tickets/{ticket_number}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        ticket = response.json()
        print(f"   Status: {ticket['status']}")
        print(f"   Queue Position: {ticket.get('queue_position', 'N/A')}")
    return response.json()


def test_create_counter():
    """Test counter creation"""
    print("\n[COUNTER] Creating Service Counter...")
    data = {
        "counter_number": 1,
        "counter_name": "Immigration Counter 1",
        "service_types": ["immigration", "passport_renewal"],
        "staff_name": "Almaz Worku",
    }
    response = requests.post(f"{BASE_URL}/api/counters", json=data)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        counter = response.json()
        print("[OK] Counter Created!")
        print(f"   Counter Number: {counter['counter_number']}")
        print(f"   Counter Name: {counter['counter_name']}")
        print(f"   Staff: {counter['staff_name']}")
        return counter
    else:
        print(f"Response: {response.json()}")
        return None


def test_call_next_ticket(counter_id):
    """Test calling next ticket"""
    print(f"\n[CALL] Calling Next Ticket at Counter {counter_id}...")
    response = requests.post(f"{BASE_URL}/api/counters/{counter_id}/call-next")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"[OK] {result['message']}")
        if "ticket_number" in result:
            print(f"   Now Serving: {result['ticket_number']}")
            print(f"   Citizen: {result['full_name']}")
            print(f"   Counter: {result['counter_number']}")
        return result
    return None


def test_verify_ticket(counter_id, ticket_number, id_number):
    """Test ticket verification"""
    print("\n[VERIFY] Verifying Ticket at Counter...")
    data = {"ticket_number": ticket_number, "id_number": id_number}
    response = requests.post(f"{BASE_URL}/api/counters/{counter_id}/verify", json=data)
    print(f"Status: {response.status_code}")
    result = response.json()
    if response.status_code == 200:
        print(f"[OK] {result['message']}")
    else:
        print(f"[ERROR] {result['detail']}")
    return result


def test_queue_status():
    """Test queue status display"""
    print("\n[DISPLAY] Getting Queue Status...")
    response = requests.get(f"{BASE_URL}/api/display/queue-status")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        status = response.json()
        print(f"   Now Serving: {len(status['now_serving'])} tickets")
        print(f"   Waiting: {status['waiting_count']} people")
        print(f"   Served Today: {status['total_served_today']}")
        return status
    return None


def test_statistics():
    """Test statistics endpoint"""
    print("\n[STATS] Getting Statistics...")
    response = requests.get(f"{BASE_URL}/api/statistics")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        stats = response.json()
        print(f"   Total Tickets Today: {stats['total_tickets_today']}")
        print(f"   Total Served: {stats['total_served_today']}")
        print(f"   Currently Waiting: {stats['total_waiting']}")
        print(f"   Active Counters: {stats['active_counters']}")
        print(f"   Avg Service Time: {stats['average_service_time_minutes']:.2f} min")
        return stats
    return None


def run_full_demo():
    """Run complete demo scenario"""
    print("=" * 60)
    print("ETHIOPIA Queue Management System - Demo Test")
    print("=" * 60)

    # Wait for server to be ready
    print("\nWaiting for server to be ready...")
    time.sleep(2)

    # Clean up old tickets first
    cleanup_old_tickets()

    # Test 1: Health Check
    if not test_health_check():
        print("[ERROR] Server is not running!")
        return

    # Test 2: Create Counter
    counter = test_create_counter()
    if not counter:
        print("[WARNING] Counter might already exist, continuing...")
        counter = {"id": 1, "counter_number": 1}

    # Test 3: Create Tickets
    print("\n" + "=" * 60)
    print("Creating Multiple Tickets...")
    print("=" * 60)

    tickets = []
    citizens = [
        {"id_number": "ETH001", "full_name": "Tesfaye Bekele", "service_type": "immigration"},
        {"id_number": "ETH002", "full_name": "Almaz Tadesse", "service_type": "passport_renewal"},
        {"id_number": "ETH003", "full_name": "Dawit Haile", "service_type": "immigration"},
    ]

    for citizen in citizens:
        ticket = test_create_ticket_with_data(citizen)
        if ticket:
            tickets.append(ticket)
        time.sleep(1)

    # Test 4: Queue Status
    time.sleep(1)
    test_queue_status()

    # Test 5: Call and Serve First Ticket
    if tickets:
        print("\n" + "=" * 60)
        print("Serving First Ticket...")
        print("=" * 60)

        called = test_call_next_ticket(counter["id"])
        if called and "ticket_number" in called:
            time.sleep(1)
            test_verify_ticket(counter["id"], tickets[0]["ticket_number"], citizens[0]["id_number"])

    # Test 6: Statistics
    time.sleep(1)
    test_statistics()

    # Test 7: Try duplicate ticket (should fail)
    print("\n" + "=" * 60)
    print("Testing Anti-Fraud: Duplicate Ticket Request...")
    print("=" * 60)
    test_create_ticket_with_data(citizens[0])

    print("\n" + "=" * 60)
    print("[OK] Demo Complete!")
    print("=" * 60)


def test_create_ticket_with_data(data):
    """Helper to create ticket with custom data"""
    response = requests.post(f"{BASE_URL}/api/tickets", json=data)
    if response.status_code == 201:
        ticket = response.json()
        print(f"[OK] Ticket {ticket['ticket_number']} created for {ticket['full_name']}")
        return ticket
    else:
        print(f"[ERROR] Failed to create ticket: {response.json().get('detail', 'Unknown error')}")
        return None


if __name__ == "__main__":
    try:
        run_full_demo()
    except requests.exceptions.ConnectionError:
        print("\n[ERROR] Could not connect to server!")
        print("Make sure the server is running: python main.py")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
