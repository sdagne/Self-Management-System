"""
Ticket Management Script - Cancel/Manage Tickets
Use this script to cancel stuck tickets or manage active tickets
"""
import requests
import sys

BASE_URL = "http://localhost:8001"


def cancel_ticket(ticket_number, id_number):
    """Cancel a specific ticket"""
    try:
        response = requests.delete(
            f"{BASE_URL}/api/tickets/{ticket_number}/cancel",
            params={"id_number": id_number}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
            print(f"   Ticket: {result['ticket_number']}")
            print(f"   Status: {result['status']}")
            return True
        else:
            error = response.json()
            print(f"❌ Error: {error.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Network error: {e}")
        return False


def cancel_all_by_id(id_number):
    """Cancel all active tickets for an ID"""
    try:
        response = requests.delete(
            f"{BASE_URL}/api/tickets/cancel-by-id",
            params={"id_number": id_number}
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
            print(f"   Cancelled tickets: {', '.join(result['cancelled_tickets'])}")
            return True
        else:
            error = response.json()
            print(f"❌ Error: {error.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Network error: {e}")
        return False


def get_active_tickets(id_number):
    """Check what active tickets exist for an ID"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/tickets/active/{id_number}"
        )

        if response.status_code == 200:
            result = response.json()
            print(f"📋 {result['message']}")

            if result['tickets']:
                print("\nActive Tickets:")
                for ticket in result['tickets']:
                    print(f"   • {ticket['ticket_number']} - {ticket['service_type']} ({ticket['status']})")
                    print(f"     Created: {ticket['created_at']}")
                    print(f"     Expires: {ticket['expires_at']}")
            return result['tickets']
        else:
            print(f"❌ Error checking tickets")
            return []
    except Exception as e:
        print(f"❌ Network error: {e}")
        return []


def force_expire(ticket_number):
    """Force expire a ticket (admin function)"""
    try:
        response = requests.post(
            f"{BASE_URL}/api/tickets/{ticket_number}/expire"
        )

        if response.status_code == 200:
            result = response.json()
            print(f"✅ {result['message']}")
            print(f"   Ticket: {result['ticket_number']}")
            print(f"   Status: {result['status']}")
            return True
        else:
            error = response.json()
            print(f"❌ Error: {error.get('detail', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"❌ Network error: {e}")
        return False


def interactive_menu():
    """Interactive menu for ticket management"""
    print("\n" + "="*60)
    print("🎫 TICKET MANAGEMENT TOOL")
    print("="*60)
    print("\nOptions:")
    print("1. Check active tickets for an ID")
    print("2. Cancel specific ticket")
    print("3. Cancel ALL tickets for an ID")
    print("4. Force expire ticket (admin)")
    print("5. Exit")

    choice = input("\nSelect option (1-5): ").strip()

    if choice == "1":
        id_number = input("Enter ID number: ").strip()
        get_active_tickets(id_number)

    elif choice == "2":
        ticket_number = input("Enter ticket number (e.g., IM-001): ").strip()
        id_number = input("Enter ID number for verification: ").strip()
        cancel_ticket(ticket_number, id_number)

    elif choice == "3":
        id_number = input("Enter ID number: ").strip()
        confirm = input(f"Cancel ALL active tickets for {id_number}? (yes/no): ").strip().lower()
        if confirm == "yes":
            cancel_all_by_id(id_number)
        else:
            print("Cancelled operation")

    elif choice == "4":
        ticket_number = input("Enter ticket number (e.g., IM-001): ").strip()
        confirm = input(f"Force expire {ticket_number}? (yes/no): ").strip().lower()
        if confirm == "yes":
            force_expire(ticket_number)
        else:
            print("Cancelled operation")

    elif choice == "5":
        print("Goodbye!")
        sys.exit(0)
    else:
        print("Invalid option")

    # Continue loop
    input("\nPress Enter to continue...")
    interactive_menu()


def quick_fix_stuck_ticket():
    """Quick fix for stuck tickets - common scenario"""
    print("\n" + "="*60)
    print("🔧 QUICK FIX: Cancel Stuck Ticket")
    print("="*60)
    print("\nThis happens when you have an active ticket blocking new ones.")

    id_number = input("\nEnter your ID number: ").strip()

    if not id_number:
        print("❌ ID number required")
        return

    print("\n🔍 Checking for active tickets...")
    tickets = get_active_tickets(id_number)

    if tickets:
        print(f"\n⚠️  Found {len(tickets)} active ticket(s)")
        cancel = input("\nCancel all active tickets? (yes/no): ").strip().lower()

        if cancel == "yes":
            print("\n🗑️  Cancelling tickets...")
            cancel_all_by_id(id_number)
            print("\n✅ You can now create a new ticket!")
        else:
            print("No tickets cancelled")
    else:
        print("\n✅ No active tickets found. You're good to go!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🇪🇹 QUEUE MANAGEMENT SYSTEM - Ticket Manager")
    print("="*60)

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        if response.status_code == 200:
            print("✅ Server is online\n")
        else:
            print("⚠️  Server responded but may have issues\n")
    except:
        print("❌ Server is not running!")
        print("   Start it with: python run_server.py\n")
        sys.exit(1)

    # Check for command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "check" and len(sys.argv) > 2:
            # Quick check: python cancel_ticket.py check ABC123
            get_active_tickets(sys.argv[2])

        elif command == "cancel" and len(sys.argv) > 2:
            # Quick cancel: python cancel_ticket.py cancel ABC123
            cancel_all_by_id(sys.argv[2])

        elif command == "quick":
            # Quick fix mode
            quick_fix_stuck_ticket()

        else:
            print("Usage:")
            print("  python cancel_ticket.py check <ID>    - Check active tickets")
            print("  python cancel_ticket.py cancel <ID>   - Cancel all tickets for ID")
            print("  python cancel_ticket.py quick         - Interactive quick fix")
            print("  python cancel_ticket.py               - Full interactive menu")
    else:
        # No arguments - show menu
        mode = input("Choose mode:\n1. Quick Fix (recommended)\n2. Full Menu\n\nSelect (1/2): ").strip()

        if mode == "1":
            quick_fix_stuck_ticket()
        else:
            interactive_menu()

