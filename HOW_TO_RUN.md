# 🚀 How to Run the Queue Management System

## Quick Start (3 Steps)

### Step 1: Open Terminal/Console
```powershell
# Open PowerShell or Command Prompt
# Navigate to project directory
cd "D:\Queue Management Standard"
```

### Step 2: Start the Server
```powershell
python run_server.py
```

You should see:
```
============================================================
🇪🇹 Queue Management System - Ethiopia
Version: 1.0.0
============================================================

🚀 Starting server on http://0.0.0.0:8001
📖 API Documentation: http://localhost:8001/docs
📊 Alternative Docs: http://localhost:8001/redoc

Press CTRL+C to stop the server

============================================================
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Step 3: Access the Application

Open in your browser:
- **Demo Dashboard**: http://localhost:8001 (or open `demo_dashboard.html`)
- **API Docs**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

---

## Alternative: Direct Server Start

```powershell
# Method 1: Using run_server.py (Recommended)
python run_server.py

# Method 2: Using main.py directly
python main.py

# Method 3: Using uvicorn command
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

---

## Run the Demo Test

**In a NEW terminal window** (while server is running):

```powershell
cd "D:\Queue Management Standard"
python test_api.py
```

This will:
- ✅ Test all API endpoints
- ✅ Create sample tickets
- ✅ Test counter operations
- ✅ Verify anti-fraud features
- ✅ Display statistics

---

## Complete Workflow Example

### Terminal 1: Start Server
```powershell
cd "D:\Queue Management Standard"
python run_server.py
```
Leave this running...

### Terminal 2: Run Tests
```powershell
cd "D:\Queue Management Standard"
python test_api.py
```

### Browser: Open Demo
```
1. Navigate to: D:\Queue Management Standard\demo_dashboard.html
2. Double-click to open in browser
3. Or visit: http://localhost:8001/docs
```

---

## Stop the Server

In the terminal where server is running:
```
Press CTRL+C
```

---

## Troubleshooting

### Problem: "python is not recognized"
**Solution**: Python not in PATH
```powershell
# Use full path
py run_server.py
# or
python.exe run_server.py
```

### Problem: "Module not found"
**Solution**: Install dependencies
```powershell
pip install -r requirements.txt
```

### Problem: "Port 8001 already in use"
**Solution**: Kill existing process
```powershell
# Find process using port 8001
netstat -ano | findstr :8001

# Kill process (replace PID with actual number)
taskkill /PID <PID> /F
```

### Problem: Server starts but doesn't respond
**Solution**: Check firewall or try localhost
```
http://127.0.0.1:8001
```

---

## Quick Test Commands

### Check if server is running
```powershell
curl http://localhost:8001/health
```

### Create a test ticket
```powershell
curl -X POST http://localhost:8001/api/tickets -H "Content-Type: application/json" -d "{\"id_number\":\"TEST123\",\"full_name\":\"Test User\",\"service_type\":\"immigration\"}"
```

### Get queue status
```powershell
curl http://localhost:8001/api/display/queue-status
```

---

## One-Command Demo

Run everything in one go:
```powershell
# Start server in background, wait 3 seconds, run test
Start-Process python -ArgumentList "run_server.py" -WindowStyle Normal ; Start-Sleep -Seconds 3 ; python test_api.py
```

---

## Development Mode (With Auto-Reload)

```powershell
# Server automatically restarts when you change code
python run_server.py
# or
uvicorn main:app --reload
```

---

## Production Mode (Future)

```powershell
# Install gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

---

## Check Python Version

```powershell
python --version
# Should be Python 3.8 or higher
```

---

## Virtual Environment (If needed)

```powershell
# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python run_server.py
```

---

## Summary - Copy/Paste This

```powershell
# 1. Navigate to project
cd "D:\Queue Management Standard"

# 2. Install dependencies (first time only)
pip install -r requirements.txt

# 3. Start server
python run_server.py

# 4. Open browser to:
#    http://localhost:8001/docs
#    or open demo_dashboard.html

# 5. Stop server: Press CTRL+C
```

---

## Video Tutorial (Text Version)

```
┌─────────────────────────────────────────┐
│  1. Open PowerShell/Terminal            │
│  2. Type: cd "D:\Queue Management..."   │
│  3. Press Enter                          │
│  4. Type: python run_server.py          │
│  5. Press Enter                          │
│  6. Wait for "Uvicorn running..."       │
│  7. Open browser                         │
│  8. Visit: localhost:8001/docs          │
│  9. Done! 🎉                            │
└─────────────────────────────────────────┘
```

---

## Expected Output

When you run `python run_server.py`, you should see:

```
============================================================
🇪🇹 Queue Management System - Ethiopia
Version: 1.0.0
============================================================

🚀 Starting server on http://0.0.0.0:8001
📖 API Documentation: http://localhost:8001/docs
📊 Alternative Docs: http://localhost:8001/redoc

Press CTRL+C to stop the server

============================================================
🚀 Queue Management System v1.0.0 started
📊 Server running on http://0.0.0.0:8001
INFO:     Will watch for changes in these directories: ['D:\\Queue Management Standard']
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Started reloader process [XXXX] using WatchFiles
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

**✅ This means the server is running successfully!**

---

## Now You're Ready!

The Queue Management System is now running and ready to use.

**Access Points:**
- 🌐 Demo Dashboard: `demo_dashboard.html`
- 📚 API Docs: http://localhost:8001/docs
- 🧪 Run Tests: `python test_api.py`

**To Stop:**
- Press `CTRL+C` in the terminal

---

*Last Updated: February 17, 2026*
*Quick Reference Guide*

