import streamlit as st
import subprocess
import time
import os
import requests
import socket
import sys

# Page configuration
st.set_page_config(
    page_title="Ethiopia Self Management System",
    page_icon="🎫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Sidebar Configuration
st.sidebar.title("🎫 Queue System")
st.sidebar.markdown("**Ethiopia Self Management**")
st.sidebar.markdown("---")

# Deployment Mode Selection
deployment_mode = st.sidebar.radio(
    "🌍 Current Environment",
    ["Local Home / Office", "Public Website (Cloud)"],
    help="Use 'Local' if you are running this on your own machine. Use 'Public' if you are visiting the Streamlit web address."
)

if deployment_mode == "Local Home / Office":
    API_URL = "http://localhost:8001"
    st.sidebar.info("🏠 Localhost Mode Active")
else:
    API_URL = st.sidebar.text_input(
        "🔗 Enter Backend API URL",
        value="https://your-api.onrender.com",
        placeholder="Paste your Render/Railway URL here"
    )
    st.sidebar.warning("⚠️ If you see 'Connection Refused', ensure your public backend is online and the URL is correct.")

st.sidebar.markdown("---")

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('localhost', port)) == 0

def start_backend_local():
    if deployment_mode == "Local Home / Office":
        if not is_port_in_use(8001):
            st.warning("⚠️ Local Backend is Offline.")
            if st.button("🚀 START BACKEND NOW"):
                try:
                    # Using sys.executable to ensure we use the same venv
                    cmd = [sys.executable, "run_server.py"]
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
                    
                    with st.status("Starting Backend...", expanded=True) as status_box:
                        for i in range(10):
                            st.write(f"Connecting to server... {i+1}/10")
                            try:
                                resp = requests.get(f"{API_URL}/api/display/queue-status", timeout=1)
                                if resp.status_code == 200:
                                    status_box.update(label="✅ Success!", state="complete", expanded=False)
                                    st.rerun()
                                    return
                            except:
                                pass
                            time.sleep(1)
                    st.error("❌ Startup Timeout. please run it manually.")
                except Exception as e:
                    st.error(f"❌ Startup Error: {e}")
            
            st.markdown("---")
            st.markdown("### 🛠️ Manual Start (Recommended)")
            st.markdown("If the button above fails, please run this in a **separate** terminal:")
            st.code("python run_server.py", language="bash")
        else:
            st.sidebar.success("✅ Local Backend Online")
    else:
        # Remote Mode - No auto-start
        try:
            resp = requests.get(f"{API_URL}/health", timeout=2)
            if resp.status_code == 200:
                st.sidebar.success("🔗 Connected to Cloud API")
            else:
                st.sidebar.error("❌ Cloud API responded with error")
        except:
            st.sidebar.warning("⚠️ Cloud API Unreachable")

# Tabs for Portals
tabs = st.tabs(["🎫 Kiosk", "💼 Counter", "🖥️ Public Display", "📊 Dashboard"])
PORTALS = ["kiosk_portal.html", "counter_portal.html", "display_portal.html", "demo_dashboard.html"]

# Check/Start Connection
start_backend_local()

# Content
for i, tab_name in enumerate(["🎫 Kiosk", "💼 Counter", "🖥️ Public Display", "📊 Dashboard"]):
    with tabs[i]:
        filename = PORTALS[i]
        
        # Tools
        c1, c2, c3 = st.columns([2, 1, 5])
        with c1:
            if st.button(f"Refresh {tab_name}", key=f"r_{i}"):
                st.rerun()
        with c2:
            if st.button("➕ Test Ticket", key=f"t_{i}"):
                try:
                    requests.post(f"{API_URL}/api/tickets", json={"id_number":"TEST","full_name":"Test User","service_type":"kebele_id"})
                    st.toast("Ticket created!")
                except:
                    st.error("Link offline")
        
        # Build URL
        iframe_src = f"{API_URL}/web/{filename}"
        if "Counter" in tab_name:
            iframe_src += "?counter=1"
        
        st.markdown(f"[[🌐 Fullscreen Page]]({iframe_src})")
        
        # Rendering
        try:
            st.components.v1.iframe(iframe_src, height=900, scrolling=True)
        except Exception as e:
            st.info("Iframe loading... ensure the backend is running.")

st.markdown("---")
st.caption("Ethiopia Self Management System - Cloud Hub Beta")
