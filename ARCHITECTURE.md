# System Architecture — Queue Management System

## Overview

This system manages physical queues at Ethiopian public service offices. Citizens take a numbered ticket, wait, and are called by name/number to a service counter.

---

## Component Map

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLIENTS (Browsers)                        │
├─────────────────┬──────────────────┬──────────────┬─────────────┤
│  kiosk_portal   │  counter_portal  │display_portal│demo_dashboard│
│  (Citizen)      │  (Staff)         │  (TV Screen) │  (Admin)    │
│  Create ticket  │  Call / Verify   │  Show queue  │  Manage all │
│  Print / QR     │  Complete service│  Now serving │  Statistics │
└────────┬────────┴────────┬─────────┴──────┬───────┴──────┬──────┘
         │                 │                │              │
         └─────────────────┴────────────────┴──────────────┘
                                   │  HTTP / REST
                        ┌──────────▼───────────┐
                        │    FastAPI Backend    │
                        │      main.py          │
                        │    port 8001          │
                        ├───────────────────────┤
                        │  POST /api/tickets    │  ← Kiosk
                        │  GET  /api/tickets/:n │
                        │  POST /api/counters   │  ← Counter staff
                        │  POST /counters/:id/  │
                        │    call-next          │
                        │    verify             │
                        │    complete           │
                        │  GET /api/display/    │  ← Display board
                        │    queue-status       │
                        │  GET /api/statistics  │  ← Dashboard
                        │  GET /web/*.html      │  ← Serves HTML files
                        │  GET /health          │
                        └──────────┬────────────┘
                                   │
               ┌───────────────────┴────────────────────┐
               │                                        │
   ┌───────────▼──────────┐              ┌─────────────▼──────────┐
   │   SQLite / PostgreSQL │              │   Telegram Bot          │
   │   (SQLAlchemy ORM)    │              │   (Optional)            │
   ├───────────────────────┤              ├─────────────────────────┤
   │  citizens             │              │  Ticket confirmation    │
   │  tickets              │              │  Appointment reminders  │
   │  counters             │              │  Queue call alerts      │
   │  audit_logs           │              └─────────────────────────┘
   └───────────────────────┘
```

---

## Streamlit Hub (streamlit_app.py)

Streamlit is a **navigation wrapper only** — it embeds the 4 HTML portals inside iframes. It does not replace the FastAPI backend.

```
streamlit_app.py
    │
    ├── Tab: 🎫 Kiosk       → <iframe src="{API_URL}/web/kiosk_portal.html">
    ├── Tab: 💼 Counter     → <iframe src="{API_URL}/web/counter_portal.html?counter=1">
    ├── Tab: 🖥️ Display     → <iframe src="{API_URL}/web/display_portal.html">
    └── Tab: 📊 Dashboard   → <iframe src="{API_URL}/web/demo_dashboard.html">
```

---

## Data & State Flow

```
1. CITIZEN arrives at kiosk
   └── kiosk_portal.html
         POST /api/tickets  {id_number, full_name, service_type}
         ← Returns: ticket_number (e.g. KI-042), QR code, queue_position

2. DISPLAY BOARD refreshes every few seconds
   └── display_portal.html
         GET /api/display/queue-status
         ← Returns: now_serving[], waiting_count, counters[]

3. STAFF at counter calls next person
   └── counter_portal.html
         POST /api/counters/{id}/call-next
         ← Returns: ticket_number, citizen name

4. CITIZEN approaches counter — staff verifies identity
   └── counter_portal.html
         POST /api/counters/{id}/verify  {ticket_number, id_number}
         ← Returns: verified=true/false

5. Service complete
   └── counter_portal.html
         POST /api/counters/{id}/complete
         ← Ticket status → COMPLETED, audit log written
```

---

## Ticket Status Lifecycle

```
  [Created]
      │
   WAITING  ──── expired after 2h ──→  EXPIRED
      │
   CALLED   ← staff calls next
      │
   SERVING  ← citizen verified at counter
      │
  COMPLETED ← service done
      │
(or CANCELLED at any point by admin)
```

---

## Security & Anti-Fraud

| Rule | How it works |
|---|---|
| One active ticket per person | ID number is SHA-256 hashed; uniqueness enforced in DB |
| Ticket expiration | `expires_at` set to `created_at + TICKET_EXPIRY_HOURS` |
| ID verification at counter | Hash of presented ID must match ticket's stored hash |
| Blacklist | `citizens.is_blacklisted` flag checked on ticket creation |
| Audit log | Every action (create, call, verify, complete) written to `audit_logs` |
| Suspicious activity | `detect_suspicious_activity()` in `utils.py` flags rapid repeat requests |

---

## Deployment Architectures

### Local (Development)
```
Terminal 1:  python run_server.py        → FastAPI at http://localhost:8001
Terminal 2:  streamlit run streamlit_app.py → Streamlit at http://localhost:8501

Open directly: http://localhost:8001/web/kiosk_portal.html
            or via Streamlit hub: http://localhost:8501
```

### Cloud (Production) — Two-Service Setup
```
┌─────────────────────────────┐     ┌──────────────────────────────┐
│      Render / Railway        │     │      Streamlit Cloud          │
│  FastAPI + HTML files        │     │      streamlit_app.py         │
│  yourapp.onrender.com        │◄────│      yourapp.streamlit.app    │
│                              │     │  (iframes → Render URL)       │
│  uvicorn main:app            │     │                               │
│  --host 0.0.0.0 --port $PORT │     │  Set API_URL in sidebar       │
└─────────────────────────────┘     └──────────────────────────────┘
         │
         │  persists to
         ▼
  PostgreSQL (Render managed DB)
  or SQLite (dev/demo only)
```

### Procfile (for Render — single process)
```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

> Note: Render supports only **one** process per free-tier service.
> Deploy FastAPI (backend) and Streamlit (hub) as separate Render services,
> or access portals directly via the FastAPI `/web/` URLs without Streamlit.

---

## File Roles

| File | Role |
|---|---|
| `main.py` | FastAPI app — all routes, middleware, startup |
| `database.py` | SQLAlchemy models: Citizen, Ticket, Counter, AuditLog |
| `models.py` | Pydantic request/response schemas |
| `config.py` | Settings (reads `.env`) |
| `auth.py` | Role-based token auth (admin / counter / display) |
| `utils.py` | Hashing, QR generation, wait time, fraud detection |
| `run_server.py` | Uvicorn entry point |
| `streamlit_app.py` | Streamlit navigation hub |
| `kiosk_portal.html` | Citizen-facing ticket creation UI |
| `counter_portal.html` | Staff UI — call, verify, complete |
| `display_portal.html` | Public queue display board |
| `demo_dashboard.html` | Admin dashboard and statistics |
| `telegram_routes.py` | FastAPI router for Telegram webhook |
| `telegram_service.py` | Telegram bot message logic |
| `queue_telegram_integration.py` | Scheduler for appointment reminders |
| `reminder_scheduler.py` | APScheduler job management |
