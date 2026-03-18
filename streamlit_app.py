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
    initial_sidebar_state="expanded"
)

# Sidebar Configuration
st.sidebar.title("🎫 Queue System")
st.sidebar.markdown("**Ethiopia Queue Management**")
st.sidebar.markdown("---")

# Deployment Mode Selection
deployment_mode = st.sidebar.selectbox(
    "🌍 Deployment Mode",
    ["Local (Auto-start)", "Cloud (Remote API)"],
    help="Select 'Local' if running on your machine, or 'Cloud' if the backend is hosted elsewhere."
)

if deployment_mode == "Local (Auto-start)":
    API_URL = "http://localhost:8001"
    st.sidebar.info("Running on Localhost:8001")
else:
    API_URL = st.sidebar.text_input(
        "🔗 Backend API URL",
        value="https://your-api.onrender.com",
        help="Paste the URL of your hosted FastAPI backend (e.g. from Render or Railway)"
    )

st.sidebar.markdown("---")

# Constants
PORTALS = {
    "Kiosk - Create Ticket": "kiosk_portal.html",
    "Counter - Process Tickets": "counter_portal.html",
    "Display - Public View": "display_portal.html",
    "Admin - Demo Dashboard": "demo_dashboard.html"
}

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('localhost', port)) == 0

def start_backend_local():
    if deployment_mode == "Local (Auto-start)":
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
                st.error("❌ Failed to start backend Automatically. Run 'python run_server.py' in terminal.")
            except Exception as e:
                st.error(f"❌ Startup Error: {e}")
        else:
            st.sidebar.success("✅ Local Backend Online")
    else:
        # Cloud Mode - Just check connectivity
        try:
            resp = requests.get(f"{API_URL}/health", timeout=2)
            if resp.status_code == 200:
                st.sidebar.success("🔗 Connected to Cloud API")
            else:
                st.sidebar.error("❌ Cloud API responded with error")
        except:
            st.sidebar.warning("⚠️ Could not reach Cloud API. Is the URL correct?")

# Tabs for Portals
tabs = st.tabs(list(PORTALS.keys()))

# Backend Lifecycle
start_backend_local()

def create_test_ticket():
    try:
        payload = {
            "id_number": "TEST-USER-1",
            "full_name": "Streamlit Cloud Test",
            "service_type": "kebele_id"
        }
        resp = requests.post(f"{API_URL}/api/tickets", json=payload)
        if resp.status_code == 201:
            data = resp.json()
            st.toast(f"✅ Created Ticket: {data['ticket_number']}", icon="🎫")
        else:
            st.error(f"API Error: {resp.text}")
    except Exception as e:
        st.error(f"Connection Error: {e}")

# Render content for each tab
for i, (name, filename) in enumerate(PORTALS.items()):
    with tabs[i]:
        # Quick Actions
        q_col1, q_col2, q_col3 = st.columns([2, 2, 4])
        with q_col1:
            if st.button(f"🔄 Reload {name}", key=f"re_{name}"):
                st.rerun()
        with q_col2:
            if st.button("➕ Quick Ticket", key=f"qt_{name}"):
                create_test_ticket()
        
        # Portal URL building
        # In Cloud mode, we rely on the backend serving the static files
        iframe_src = f"{API_URL}/web/{filename}"
        if name == "Counter":
            iframe_src += "?counter=1"

        st.markdown(f"[[🌐 Fullscreen View]]({iframe_src})")
        
        # Display the iframe
        st.components.v1.iframe(iframe_src, height=900, scrolling=True)

# Footer
st.markdown("---")
st.caption("Ethiopia Queue Management System - Cloud Hub Beta")
