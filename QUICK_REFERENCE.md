# ⚡ Quick Command Reference

## Start/Stop Server

### Start Server
```powershell
cd "D:\Queue Management Standard"
python run_server.py
```

### Stop Server
Press `CTRL+C` in the terminal

### Check if Server is Running
```powershell
curl http://localhost:8001/health
```

---

## Open Tools

### Demo Dashboard (Visual Interface)
```powershell
# Open in default browser
start demo_dashboard.html
```

### API Documentation
```powershell
# Swagger UI
start http://localhost:8001/docs

# ReDoc
start http://localhost:8001/redoc
```

---

## Run Tests

### Full Demo Test
```powershell
python test_api.py
```

### Quick Health Check
```powershell
python -c "import requests; print(requests.get('http://localhost:8001/health').json())"
```

---

## Database Management

### View Database
```powershell
# Install DB Browser for SQLite (optional)
# Open queue_management.db file
```

### Reset Database
```powershell
# Delete and restart server to recreate
Remove-Item queue_management.db
python run_server.py
```

---

## API Quick Examples (PowerShell)

### Create Ticket
```powershell
$body = @{
    id_number = "ABC123"
    full_name = "Tesfaye Bekele"
    service_type = "immigration"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8001/api/tickets" -Method Post -Body $body -ContentType "application/json"
```

### Get Queue Status
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/api/display/queue-status"
```

### Get Statistics
```powershell
Invoke-RestMethod -Uri "http://localhost:8001/api/statistics"
```

---

## Python Quick Examples

### Create Ticket
```python
import requests

response = requests.post("http://localhost:8001/api/tickets", json={
    "id_number": "ABC123",
    "full_name": "Tesfaye Bekele",
    "service_type": "immigration"
})
print(response.json())
```

### Call Next Ticket
```python
import requests

response = requests.post("http://localhost:8001/api/counters/1/call-next")
print(response.json())
```

---

## Service Types

Use these values in `service_type` field:

- `birth_certificate`
- `tax_service`
- `immigration`
- `business_license`
- `passport_renewal`
- `document_legalization`
- `other`

---

## Ticket Status Values

- `waiting` - In queue
- `called` - Called to counter
- `serving` - Being served
- `completed` - Service done
- `expired` - Ticket expired
- `cancelled` - Cancelled

---

## URLs

| Service | URL |
|---------|-----|
| API Base | http://localhost:8001 |
| Health Check | http://localhost:8001/health |
| Swagger UI | http://localhost:8001/docs |
| ReDoc | http://localhost:8001/redoc |
| Demo Dashboard | file:///D:/Queue%20Management%20Standard/demo_dashboard.html |

---

## File Locations

| File | Purpose |
|------|---------|
| `main.py` | Main API application |
| `run_server.py` | Server launcher |
| `test_api.py` | Test suite |
| `demo_dashboard.html` | Visual demo |
| `queue_management.db` | SQLite database |
| `GETTING_STARTED.md` | Full guide |
| `PROJECT_COMPLETION.md` | Summary |

---

## Troubleshooting

### Port Already in Use
```powershell
# Kill process on port 8001
Get-Process -Id (Get-NetTCPConnection -LocalPort 8001).OwningProcess | Stop-Process -Force
```

### Module Not Found
```powershell
# Install dependencies
pip install -r requirements.txt
```

### Database Locked
```powershell
# Close all connections and restart
Remove-Item queue_management.db
python run_server.py
```

---

## One-Line Demo

```powershell
# Start server, wait, run test, show results
python run_server.py & Start-Sleep -Seconds 3 & python test_api.py
```

---

## Production Deployment (Future)

### With Gunicorn
```bash
pip install gunicorn
gunicorn main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

### With Environment Variables
```bash
export DATABASE_URL="postgresql://user:pass@localhost/queuedb"
export SECRET_KEY="your-secret-key"
python run_server.py
```

---

## Backup Commands

### Backup Database
```powershell
Copy-Item queue_management.db "queue_management_backup_$(Get-Date -Format 'yyyy-MM-dd').db"
```

### Export Data (Future)
```powershell
# Add export endpoint or use SQLite export
```

---

**💡 Tip**: Keep this file open while working with the system!

**⭐ Bookmark**: `demo_dashboard.html` for visual testing

