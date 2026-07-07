"""
Diagnostic script to check what's in the database
"""

import sqlite3

# Connect to database
conn = sqlite3.connect("queue_management.db")
cursor = conn.cursor()

print("\n" + "=" * 60)
print("DIAGNOSTIC: Current Tickets in Database")
print("=" * 60 + "\n")

# Get all active tickets
cursor.execute("""
    SELECT ticket_number, counter_number, status, full_name
    FROM tickets
    WHERE status IN ('called', 'serving', 'waiting')
    ORDER BY created_at
""")

tickets = cursor.fetchall()

if not tickets:
    print("No active tickets found.\n")
else:
    print(f"Found {len(tickets)} active ticket(s):\n")
    print(f"{'Ticket':<15} {'Counter':<10} {'Status':<15} {'Name'}")
    print("-" * 60)

    for ticket in tickets:
        ticket_num, counter, status, name = ticket
        counter_display = str(counter) if counter else "None"
        print(f"{ticket_num:<15} {counter_display:<10} {status:<15} {name}")

print("\n" + "=" * 60)
print("DIAGNOSTIC: Counters in Database")
print("=" * 60 + "\n")

# Get all counters
cursor.execute("""
    SELECT counter_number, counter_name, is_active, current_ticket_id, staff_name
    FROM counters
    ORDER BY counter_number
""")

counters = cursor.fetchall()

if not counters:
    print("No counters found.\n")
else:
    print(f"Found {len(counters)} counter(s):\n")
    print(f"{'Counter #':<12} {'Name':<25} {'Active':<10} {'Current Ticket':<15} {'Staff'}")
    print("-" * 80)

    for counter in counters:
        counter_num, name, is_active, current_ticket_id, staff = counter
        active_display = "Yes" if is_active else "No"
        ticket_display = str(current_ticket_id) if current_ticket_id else "None"
        staff_display = staff if staff else "N/A"
        print(
            f"{counter_num:<12} {name:<25} {active_display:<10} {ticket_display:<15} {staff_display}"
        )

print("\n" + "=" * 60)
print("ISSUE DIAGNOSIS")
print("=" * 60 + "\n")

# Check for tickets with counter_number = 1
cursor.execute("""
    SELECT COUNT(*) FROM tickets 
    WHERE status IN ('called', 'serving') AND counter_number = 1
""")
count_counter_1 = cursor.fetchone()[0]

# Check for tickets with other counter numbers
cursor.execute("""
    SELECT COUNT(*) FROM tickets 
    WHERE status IN ('called', 'serving') AND counter_number != 1 AND counter_number IS NOT NULL
""")
count_other_counters = cursor.fetchone()[0]

# Check for tickets with no counter number
cursor.execute("""
    SELECT COUNT(*) FROM tickets 
    WHERE status IN ('called', 'serving') AND counter_number IS NULL
""")
count_no_counter = cursor.fetchone()[0]

print(f"Active tickets at Counter 1: {count_counter_1}")
print(f"Active tickets at other counters: {count_other_counters}")
print(f"Active tickets with NO counter assigned: {count_no_counter}")

if count_other_counters == 0 and count_counter_1 > 0:
    print("\n⚠️  PROBLEM IDENTIFIED:")
    print("   All active tickets are assigned to Counter 1.")
    print("   This could mean:")
    print("   1. You only have Counter 1 created in the database")
    print("   2. All tickets were called from Counter 1")
    print("   3. You need to create additional counters (Counter 2, 3, etc.)")
    print("\n💡 SOLUTION:")
    print("   Create more counters using the counter portal or demo dashboard.")
    print("   Each counter will then call tickets and assign them properly.")

print("\n" + "=" * 60 + "\n")

conn.close()
