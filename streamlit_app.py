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

# Constants
API_URL = "http://localhost:8001"
# Map Display names to the actual filenames
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

def start_backend():
    if not is_port_in_use(8001):
        st.warning("⚠️ Backend is offline. Attempting to start...")
        try:
            # Using sys.executable ensures we use the same environment
            cmd = [sys.executable, "run_server.py"]
            subprocess.Popen(cmd, shell=False)
            
            # Wait for server to start with a progress bar
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i in range(15):
                progress_bar.progress((i + 1) / 15)
                status_text.text(f"Waiting for backend... ({i+1}/15s)")
                try:
                    # Check health endpoint
                    resp = requests.get(f"{API_URL}/api/display/queue-status", timeout=1)
                    if resp.status_code == 200:
                        status_text.success("✅ Backend is now ONLINE!")
                        time.sleep(1)
                        st.rerun()
                        return
                except:
                    pass
                time.sleep(1)
            
            st.error("❌ Failed to start backend automatically. Please run 'python run_server.py' manually in a separate terminal.")
        except Exception as e:
            st.error(f"❌ Error starting backend: {e}")
    else:
        st.sidebar.success("✅ Backend Service Running")

# Sidebar navigation
st.sidebar.title("🎫 Queue System")
st.sidebar.markdown("**Ethiopia Queue Management**")
st.sidebar.markdown("---")

selection = st.sidebar.radio("Navigation", list(PORTALS.keys()))

st.sidebar.markdown("---")
if st.sidebar.button("Force Refresh Dashboard"):
    st.rerun()

# Main logic
start_backend()

# Get selected portal filename
portal_file = PORTALS[selection]

# Display the portal
st.subheader(f"🏢 {selection}")

# We serve the local HTML files via an iframe pointing to the FastAPI static mount
iframe_url = f"{API_URL}/web/{portal_file}"

# Fallback Link
st.markdown(f"[🔗 Open in New Tab]({iframe_url})")

# Responsive iframe
try:
    # Adding a timestamp or unique key helps force refresh
    st.components.v1.iframe(iframe_url, height=900, scrolling=True)
except Exception as e:
    st.error(f"Could not load the portal iframe: {e}")

st.markdown("---")
st.caption("Ethiopia Queue Management System - Unified Portal Hub")
