import sqlite3
import sys

def check_db():
    conn = sqlite3.connect('queue_management.db')
    c = conn.cursor()
    
    print("--- COUNTERS CONFIG ---")
    c.execute("SELECT id, counter_number, service_types FROM counters")
    for row in c.fetchall():
        print(f"ID: {row[0]} | Num: {row[1]} | Services: {row[2]}")
        
    print("\n--- WAITING TICKETS ---")
    c.execute("SELECT ticket_number, service_type, status, created_at FROM tickets WHERE status='waiting' ORDER BY created_at ASC")
    rows = c.fetchall()
    if not rows:
        print("No tickets currently waiting.")
    for row in rows:
        print(f"Num: {row[0]} | Type: {row[1]} | Status: {row[2]} | Created: {row[3]}")

    conn.close()

if __name__ == "__main__":
    check_db()
