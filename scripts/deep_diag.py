import socket
import os
import requests
import subprocess
import sys

def diagnose():
    print("--- 🔍 SYSTEM DIAGNOSTIC ---")
    
    # Check if port 8001 is in use
    port = 8001
    print(f"Checking Port {port}...")
    
    # Try IPv4
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        res = s.connect_ex(('127.0.0.1', port))
        if res == 0:
            print(f"✅ Port {port} is OPEN on 127.0.0.1 (IPv4)")
        else:
            print(f"❌ Port {port} is CLOSED on 127.0.0.1")

    # Try IPv6
    try:
        with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            res = s.connect_ex(('::1', port))
            if res == 0:
                print(f"✅ Port {port} is OPEN on ::1 (IPv6)")
            else:
                print(f"❌ Port {port} is CLOSED on ::1")
    except:
        print("IPv6 not supported/available.")

    # Try to ping the API if it's open
    try:
        resp = requests.get(f"http://127.0.0.1:{port}/api/display/queue-status", timeout=2)
        print(f"--- API RESPONSE (127.0.0.1) ---")
        print(f"Status: {resp.status_code}")
        print(f"Data: {resp.text[:100]}")
    except Exception as e:
            print(f"--- API FAILURE (127.0.0.1) ---\n{e}")

    # Check process list for python/uvicorn
    print("\n--- PROCESS CHECK ---")
    if os.name == 'nt':
        cmd = 'tasklist /FI "IMAGENAME eq python.exe"'
        subprocess.run(cmd, shell=True)
    
if __name__ == "__main__":
    diagnose()
