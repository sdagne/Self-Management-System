import streamlit as st
import subprocess
import time
import os
import requests
import socket
import sys

# Page configuration
st.set_page_config(
    page_title="Ethiopia Queue Management System",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="collapsed" # Hide sidebar to prioritize top menu
)

# Constants
API_URL = "http://localhost:8001"
# Map Display names to the actual filenames
PORTALS = {
    "Kiosk": "kiosk_portal.html",
    "Counter": "counter_portal.html",
    "Display": "display_portal.html",
    "Admin": "demo_dashboard.html"
}

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('localhost', port)) == 0

def start_backend():
    if not is_port_in_use(8001):
        st.warning("⚠️ Backend is offline. Starting service...")
        try:
            cmd = [sys.executable, "run_server.py"]
            subprocess.Popen(cmd, shell=False)
            
            with st.status("Starting Backend Service...", expanded=True) as status:
                for i in range(15):
                    st.write(f"Connecting... {i+1}/15s")
                    try:
                        resp = requests.get(f"{API_URL}/api/display/queue-status", timeout=1)
                        if resp.status_code == 200:
                            status.update(label="✅ Backend Online!", state="complete", expanded=False)
                            st.rerun()
                            return
                    except:
                        pass
                    time.sleep(1)
            st.error("❌ Failed to start backend manually. Run 'python run_server.py' in terminal.")
        except Exception as e:
            st.error(f"❌ Startup Error: {e}")
    else:
        # Backend is running, display status in a small header
        pass

def create_test_ticket():
    try:
        payload = {
            "id_number": "TEST-USER-1",
            "full_name": "Streamlit Test",
            "service_type": "kebele_id"
        }
        resp = requests.post(f"{API_URL}/api/tickets", json=payload)
        if resp.status_code == 201:
            data = resp.json()
            st.toast(f"✅ Success! Generated Ticket: {data['ticket_number']}", icon="🎫")
        else:
            st.error(f"Error creating ticket: {resp.text}")
    except Exception as e:
        st.error(f"Connection error: {e}")

# Header & Quick Actions
st.title("🎫 Ethiopia Queue Management System")

# Navigation Tabs as requested (Horizontal Menu)
tabs = st.tabs(list(PORTALS.keys()))

# Main logic
start_backend()

# Render content for each tab
for i, (name, filename) in enumerate(PORTALS.items()):
    with tabs[i]:
        # Top toolbar for each tab
        col1, col2, col3 = st.columns([2, 2, 4])
        with col1:
            if st.button(f"Refresh {name} Page", key=f"btn_{name}"):
                st.rerun()
        with col2:
            if st.button("➕ Create Quick Ticket", key=f"add_{name}", help="Adds a test ticket to 'kebele_id' service"):
                create_test_ticket()
        
        iframe_url = f"{API_URL}/web/{filename}"
        if name == "Counter":
            iframe_url += "?counter=1"

        st.markdown(f"[🔗 Open {name} in New Tab]({iframe_url})")
        
        # Responsive iframe
        st.components.v1.iframe(iframe_url, height=900, scrolling=True)

# Footer
st.markdown("---")
col_f1, col_f2 = st.columns(2)
with col_f1:
    st.caption("Ethiopia Queue Management System - Unified Portal Hub")
with col_f2:
    if st.button("Stop & Restart Backend"):
        st.rerun()
