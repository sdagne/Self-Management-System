import streamlit as st
import subprocess
import time
import os
import requests
import socket

# Page configuration
st.set_page_config(
    page_title="SAN Queue Management System",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constants
API_URL = "http://localhost:8001"
PORTALS = {
    "Kiosk Portal": "kiosk_portal.html",
    "Counter Portal": "counter_portal.html",
    "Display Portal": "display_portal.html",
    "Demo Dashboard": "demo_dashboard.html"
}

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def start_backend():
    if not is_port_in_use(8001):
        st.info("🚀 Starting Queue Management Backend...")
        # Start uvicorn in a background process
        process = subprocess.Popen(
            ["python", "run_server.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False
        )
        # Wait for server to start
        max_retries = 10
        for i in range(max_retries):
            try:
                requests.get(f"{API_URL}/health")
                st.success("✅ Backend is Online!")
                break
            except:
                time.sleep(2)
        else:
            st.error("❌ Failed to start backend server. Please check your logs.")
    else:
        st.sidebar.success("✅ Backend Service Running")

# Sidebar navigation
st.sidebar.title("🎫 SAN Queue")
st.sidebar.markdown("---")
selection = st.sidebar.radio("Go to Portal", list(PORTALS.keys()))

st.sidebar.markdown("---")
if st.sidebar.button("Restart Backend Service"):
    st.sidebar.warning("Restarting...")
    # This is a simplified way to trigger start_backend again
    st.rerun()

# Main logic
start_backend()

# Get selected portal filename
portal_file = PORTALS[selection]

# Display the portal
st.title(f"🏢 {selection}")

# We serve the local HTML files via an iframe pointing to the FastAPI static mount
iframe_url = f"{API_URL}/web/{portal_file}"

# Responsive iframe
st.components.v1.iframe(iframe_url, height=900, scrolling=True)

st.markdown("---")
st.caption("Ethiopia Queue Management System - Neural AI Dashboard")
