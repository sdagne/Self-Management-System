"""
Create Multiple Counters for Testing
This will create Counter 2 and Counter 3 so you can see multiple counters on the display
"""

import requests

API_BASE = "http://localhost:8001"


def create_counter(counter_number, name, service_types, staff_name):
    """Create a new counter"""
    data = {
        "counter_number": counter_number,
        "counter_name": name,
        "service_types": service_types,
        "staff_name": staff_name,
    }

    try:
        response = requests.post(f"{API_BASE}/api/counters", json=data)

        if response.status_code == 200:
            result = response.json()
            print(f"✅ Created: Counter {counter_number} - {name} (Staff: {staff_name})")
            return True
        else:
            error = response.json()
            print(f"❌ Failed Counter {counter_number}: {error.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Error creating Counter {counter_number}: {e}")
        return False


def main():
    print("\n" + "=" * 60)
    print("CREATING MULTIPLE COUNTERS FOR TESTING")
    print("=" * 60 + "\n")

    # Check server
    try:
        response = requests.get(f"{API_BASE}/health", timeout=3)
        if response.status_code != 200:
            print("❌ Server is not responding properly")
            return
    except:
        print("❌ Server is not running!")
        print("   Start it with: python run_server.py\n")
        return

    print("✅ Server is online\n")
    print("Creating counters...\n")

    # Counter 1 already exists, so we'll create Counter 2 and 3
    counters = [
        {
            "counter_number": 2,
            "name": "Passport Services Counter",
            "service_types": ["passport_renewal", "immigration"],
            "staff_name": "Dawit Haile",
        },
        {
            "counter_number": 3,
            "name": "Document Services Counter",
            "service_types": ["birth_certificate", "document_legalization"],
            "staff_name": "Sara Tesfaye",
        },
        {
            "counter_number": 4,
            "name": "General Services Counter",
            "service_types": ["tax_service", "business_license", "other"],
            "staff_name": "Yonas Bekele",
        },
    ]

    success_count = 0
    for counter in counters:
        if create_counter(
            counter["counter_number"],
            counter["name"],
            counter["service_types"],
            counter["staff_name"],
        ):
            success_count += 1

    print("\n" + "=" * 60)
    print(f"RESULT: Created {success_count} new counter(s)")
    print("=" * 60 + "\n")

    if success_count > 0:
        print("✅ You now have multiple counters!")
        print("\nTo test:")
        print("1. Open counter_portal.html in multiple browser windows")
        print("2. In first window, use Counter ID = 1")
        print("3. In second window, change Counter ID to 2")
        print("4. In third window, change Counter ID to 3")
        print("5. Call tickets from different counters")
        print("6. Watch display_portal.html show different counter numbers!\n")
        print("OR:")
        print("1. Use the demo_dashboard.html to create tickets")
        print("2. Call them from different counters")
        print("3. Display will show: Counter 1, Counter 2, Counter 3, etc.\n")
    else:
        print("⚠️  No new counters created (they may already exist)")
        print("   Check if counters 2, 3, 4 already exist in the database\n")


if __name__ == "__main__":
    main()
