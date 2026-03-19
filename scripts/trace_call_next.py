import sqlite3
import datetime

def trace_query():
    conn = sqlite3.connect('queue_management.db')
    c = conn.cursor()
    
    now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
    print(f"Current UTC (Str): {now}")
    
    # Mimic the SQLAlchemy query
    # statuses: waiting
    # services: kebele_id (example)
    query = """
    SELECT ticket_number, service_type, status, expires_at 
    FROM tickets 
    WHERE status = 'waiting' 
    AND expires_at > ?
    ORDER BY created_at ASC
    """
    
    print("\n--- Running Trace Query ---")
    c.execute(query, (now,))
    rows = c.fetchall()
    
    if not rows:
        print("❌ NO TICKETS FOUND (Query returned 0 rows)")
        # Check why
        print("\n--- Inspecting All Waiting Tickets (Ignoring Expiry) ---")
        c.execute("SELECT ticket_number, expires_at, status FROM tickets WHERE status='waiting'")
        for r in c.fetchall():
            is_valid = r[1] > now
            print(f"Ticket: {r[0]} | Expires: {r[1]} | Status: {r[2]} | Valid: {is_valid}")
    else:
        for r in rows:
            print(f"✅ Found: {r[0]} (Type: {r[1]}, Status: {r[2]}, Expires: {r[3]})")
            
    conn.close()

if __name__ == "__main__":
    trace_query()
