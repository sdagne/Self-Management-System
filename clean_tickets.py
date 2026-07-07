"""
Clean All Stuck Tickets - Quick Fix Script
Run this before running tests to clear all active tickets
"""

import requests
import sys

BASE_URL = "http://localhost:8001"

# Common test IDs that might have stuck tickets
TEST_IDS = ["ETH001", "ETH002", "ETH003", "ABC123456", "TEST123", "TEST_CANCEL_123"]


def clean_all_tickets():
    """Cancel all known test tickets"""
    print("\n" + "=" * 60)
    print("🧹 CLEANING ALL STUCK TICKETS")
    print("=" * 60 + "\n")

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
        if response.status_code != 200:
            print("❌ Server is not responding properly")
            return False
    except:
        print("❌ Server is not running!")
        print("   Start it with: python run_server.py\n")
        return False

    print("✅ Server is online\n")

    cancelled_count = 0
    not_found_count = 0

    for id_number in TEST_IDS:
        try:
            response = requests.delete(
                f"{BASE_URL}/api/tickets/cancel-by-id", params={"id_number": id_number}, timeout=5
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("cancelled_tickets"):
                    print(f"✅ {id_number}: Cancelled {len(result['cancelled_tickets'])} ticket(s)")
                    print(f"   {', '.join(result['cancelled_tickets'])}")
                    cancelled_count += len(result["cancelled_tickets"])
            elif response.status_code == 404:
                print(f"ℹ️  {id_number}: No active tickets")
                not_found_count += 1
            else:
                error = response.json()
                print(f"⚠️  {id_number}: {error.get('detail', 'Unknown error')}")

        except Exception as e:
            print(f"❌ {id_number}: Error - {e}")

    print("\n" + "=" * 60)
    print(f"🎉 CLEANUP COMPLETE!")
    print("=" * 60)
    print(f"   Cancelled: {cancelled_count} ticket(s)")
    print(f"   No tickets: {not_found_count} ID(s)")
    print("\n✅ You can now run your tests successfully!\n")

    return True


if __name__ == "__main__":
    success = clean_all_tickets()

    if success:
        # Ask if user wants to run tests
        if len(sys.argv) > 1 and sys.argv[1] == "test":
            print("🧪 Running tests...\n")
            import subprocess

            subprocess.run(["python", "test_api.py"])
        else:
            print("💡 TIP: Run 'python clean_tickets.py test' to clean and test automatically")

    sys.exit(0 if success else 1)
