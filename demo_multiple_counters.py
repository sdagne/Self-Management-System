"""
Quick Demo: Create tickets and call from different counters
This will show the display working with multiple counters
"""
import requests
import time

API_BASE = "http://localhost:8001"

print("\n" + "="*70)
print("DEMO: Multiple Counters on Display")
print("="*70 + "\n")

# Check server
try:
    response = requests.get(f"{API_BASE}/health", timeout=3)
    if response.status_code != 200:
        print("❌ Server is not running properly")
        exit(1)
except:
    print("❌ Server is not running!")
    print("   Start it with: python run_server.py\n")
    exit(1)

print("✅ Server is online\n")

# Step 1: Create 3 tickets
print("STEP 1: Creating 3 tickets...\n")

tickets_data = [
    {"id_number": "DEMO001", "full_name": "Tesfaye Bekele", "service_type": "immigration"},
    {"id_number": "DEMO002", "full_name": "Almaz Tadesse", "service_type": "passport_renewal"},
    {"id_number": "DEMO003", "full_name": "Dawit Haile", "service_type": "birth_certificate"}
]

created_tickets = []

for i, data in enumerate(tickets_data, 1):
    try:
        response = requests.post(f"{API_BASE}/api/tickets", json=data)
        if response.status_code == 201:
            ticket = response.json()
            created_tickets.append(ticket)
            print(f"✅ Created Ticket {i}: {ticket['ticket_number']} - {data['full_name']}")
        else:
            error = response.json()
            print(f"❌ Failed to create ticket {i}: {error.get('detail', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Error creating ticket {i}: {e}")

if len(created_tickets) < 2:
    print("\n⚠️ Not enough tickets created. You may need to cancel old tickets first.")
    print("   Run: python clean_tickets.py\n")
    exit(1)

time.sleep(2)

# Step 2: Call tickets from different counters
print("\n" + "="*70)
print("STEP 2: Calling tickets from DIFFERENT counters...\n")

counters_to_call = [
    {"counter_id": 1, "counter_name": "Counter 1 (Immigration)"},
    {"counter_id": 2, "counter_name": "Counter 2 (Passport)"},
    {"counter_id": 3, "counter_name": "Counter 3 (Documents)"}
]

called_tickets = []

for counter in counters_to_call[:len(created_tickets)]:
    try:
        response = requests.post(f"{API_BASE}/api/counters/{counter['counter_id']}/call-next")
        if response.status_code == 200:
            result = response.json()
            if 'ticket_number' in result:
                called_tickets.append({
                    'ticket': result['ticket_number'],
                    'counter': counter['counter_id'],
                    'name': result['full_name']
                })
                print(f"✅ {counter['counter_name']} called: {result['ticket_number']} - {result['full_name']}")
            else:
                print(f"ℹ️  {counter['counter_name']}: {result['message']}")
        else:
            print(f"❌ Failed to call from {counter['counter_name']}")
    except Exception as e:
        print(f"❌ Error calling from {counter['counter_name']}: {e}")
    
    time.sleep(1)

if not called_tickets:
    print("\n⚠️ No tickets were called.")
    exit(1)

time.sleep(2)

# Step 3: Check what the display will show
print("\n" + "="*70)
print("STEP 3: Checking display data...\n")

try:
    response = requests.get(f"{API_BASE}/api/display/queue-status")
    if response.status_code == 200:
        data = response.json()
        
        print("NOW SERVING (what display_portal.html will show):")
        print("-" * 70)
        
        if data['now_serving']:
            for ticket in data['now_serving']:
                print(f"  Ticket: {ticket['ticket_number']:<10} Counter: {ticket['counter_number']}")
        else:
            print("  (No tickets being served)")
        
        print()
        
except Exception as e:
    print(f"❌ Error checking display: {e}")

# Step 4: Instructions
print("\n" + "="*70)
print("STEP 4: NOW OPEN display_portal.html")
print("="*70 + "\n")

print("You should see:")
for ticket in called_tickets:
    print(f"  • Ticket {ticket['ticket']:<10} at COUNTER {ticket['counter']}")

print("\nIf you see 'Counter 1' for all tickets, it means:")
print("  ❌ You opened counter_portal.html multiple times")
print("  ❌ All windows used COUNTER_ID = 1")
print()
print("The correct way:")
print("  ✅ Open counter_portal.html (Counter 1)")
print("  ✅ Open counter_portal_2.html (Counter 2)")
print("  ✅ Open counter_portal_3.html (Counter 3)")

print("\n" + "="*70)
print("✅ Demo Complete!")
print("="*70)
print("\nNow refresh display_portal.html to see the different counter numbers!\n")

