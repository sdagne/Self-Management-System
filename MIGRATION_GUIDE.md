# Code Restructuring Migration Guide

## Overview

This guide covers migrating from the flat project structure (v1.x) to the modular package structure (v2.x).

## Status

**Current State**: Partial migration
- ✅ Directory structure created (`app/` with subpackages)
- ✅ New infrastructure code in place (Redis, Celery, tasks)
- ⚠️ Original code still in root directory (functional)
- 🔄 Full migration pending (non-breaking)

## Package Structure (Target)

```
queue-management-system/
├── app/                    # Main application package
│   ├── __init__.py
│   ├── main.py            # FastAPI app (from root main.py)
│   ├── config.py          # Settings (from root config.py)
│   │
│   ├── api/               # API layer
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       ├── auth.py    # Auth endpoints
│   │       ├── tickets.py # Ticket management
│   │       ├── counters.py # Counter operations
│   │       └── health.py  # Health checks
│   │
│   ├── core/              # Core functionality
│   │   ├── __init__.py
│   │   ├── auth.py        # Auth logic (from root auth.py)
│   │   ├── security.py    # Security headers (from root security_headers.py)
│   │   ├── redis_client.py # ✅ NEW: Redis integration
│   │   └── celery_config.py # ✅ NEW: Celery configuration
│   │
│   ├── db/                # Database layer
│   │   ├── __init__.py
│   │   ├── database.py    # DB config (from root database.py)
│   │   └── models.py      # SQLAlchemy models (from root models.py)
│   │
│   ├── services/          # Business logic
│   │   ├── __init__.py
│   │   ├── telegram.py    # Telegram integration
│   │   ├── scheduler.py   # Reminder scheduler
│   │   └── tasks.py       # ✅ NEW: Celery async tasks
│   │
│   └── utils/             # Utilities
│       ├── __init__.py
│       └── helpers.py     # Helper functions (from root utils.py)
│
├── k8s/                   # ✅ NEW: Kubernetes manifests
├── scripts/               # ✅ NEW: Deployment scripts
├── tests/                 # Test suite
├── alembic/               # Database migrations
└── ...
```

## Migration Steps (Future)

### Phase 1: Setup (DONE ✅)

```bash
# Create directory structure
mkdir -p app/{api/routes,core,db,services,utils}
touch app/__init__.py app/api/__init__.py ...
```

### Phase 2: Move Core Files (TODO)

1. **Database layer**:
   ```bash
   git mv database.py app/db/database.py
   git mv models.py app/db/ # (only DB models, not Pydantic)
   ```

2. **Core logic**:
   ```bash
   git mv auth.py app/core/auth.py
   git mv security_headers.py app/core/security.py
   git mv config.py app/config.py
   ```

3. **Services**:
   ```bash
   git mv telegram_service.py app/services/telegram.py
   git mv queue_telegram_integration.py app/services/telegram.py  # merge
   git mv reminder_scheduler.py app/services/scheduler.py
   ```

4. **Utilities**:
   ```bash
   git mv utils.py app/utils/helpers.py
   ```

### Phase 3: Split main.py into Routes (TODO)

Extract route handlers from `main.py` into dedicated route modules:

**app/api/routes/tickets.py**:
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

router = APIRouter(prefix="/api/tickets", tags=["tickets"])

@router.post("/", response_model=TicketResponse)
async def create_ticket(request: TicketCreateRequest, db: Session = Depends(get_db)):
    # ... (extract from main.py)
```

**app/api/routes/counters.py**:
```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/counters", tags=["counters"])

@router.post("/")
async def create_counter(...):
    # ... (extract from main.py)
```

### Phase 4: Update Imports (TODO)

Update all import statements throughout the codebase:

**Before**:
```python
from database import get_db, Ticket
from auth import require_role
from config import settings
```

**After**:
```python
from app.db.database import get_db, Ticket
from app.core.auth import require_role
from app.config import settings
```

Use find-and-replace or `sed`:
```bash
find app tests -name "*.py" -exec sed -i 's/from database import/from app.db.database import/g' {} +
```

### Phase 5: Update Entry Point (TODO)

**app/main.py**:
```python
from fastapi import FastAPI
from app.api.routes import tickets, counters, auth as auth_routes, health
from app.core.security import SecurityHeadersMiddleware
from app.core.redis_client import RedisClient
# ...

app = FastAPI(title="Self Management System")

# Include routers
app.include_router(tickets.router)
app.include_router(counters.router)
app.include_router(auth_routes.router)
app.include_router(health.router)

@app.on_event("startup")
async def startup():
    # Initialize Redis, database, etc.
    pass
```

### Phase 6: Update Configuration Files (TODO)

1. **Dockerfile**:
   ```dockerfile
   # Update WORKDIR and CMD
   WORKDIR /app
   CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
   ```

2. **alembic/env.py**:
   ```python
   from app.db.database import Base
   from app.db.models import *  # Import all models
   ```

3. **tests/conftest.py**:
   ```python
   from app.db.database import Base, get_db
   from app.main import app
   ```

4. **pyproject.toml**:
   ```toml
   [tool.mypy]
   mypy_path = "app"
   ```

### Phase 7: Testing (TODO)

```bash
# Run all tests
pytest tests/ -v

# Check import issues
python -m app.main

# Verify Docker build
docker build -t queue-api:test .
docker run --rm queue-api:test python -c "from app.main import app; print('✅ Imports OK')"
```

### Phase 8: Cleanup (TODO)

```bash
# Remove old files from root (after confirming everything works)
rm main.py config.py auth.py database.py models.py utils.py
rm telegram_service.py queue_telegram_integration.py reminder_scheduler.py
# Keep: Dockerfile, docker-compose.yml, requirements.txt, etc.
```

## Why This Wasn't Done Immediately

1. **Non-breaking approach**: Existing infrastructure kept working
2. **High-priority features first**: Added K8s, Redis, Celery, backups, CD pipeline
3. **Incremental migration**: Can be done gradually without downtime
4. **Testing required**: Full integration testing needed before moving production code

## Benefits of Migration

- ✅ **Better organization**: Clear separation of concerns
- ✅ **Easier testing**: Isolated modules for unit tests
- ✅ **Scalability**: Easier to add features in specific areas
- ✅ **Team collaboration**: Multiple developers can work on different modules
- ✅ **IDE support**: Better autocomplete and navigation
- ✅ **Import clarity**: Explicit package paths

## Current Workaround

The system works in "hybrid mode":
- Old code in root directory (working, tested)
- New infrastructure in `app/` package (Redis, Celery, K8s)
- Both can coexist during migration period
- No breaking changes for current deployments

## Recommended Timeline

- **Week 1**: Move database and core modules
- **Week 2**: Split routes, update imports
- **Week 3**: Full testing and validation
- **Week 4**: Cleanup and documentation

## Testing Checklist

Before completing migration:

- [ ] All tests pass (`pytest tests/`)
- [ ] Docker build succeeds
- [ ] Docker-compose stack starts
- [ ] Manual API testing works
- [ ] Alembic migrations run
- [ ] Celery tasks execute
- [ ] Redis caching functional
- [ ] K8s deployment works

## Rollback Plan

If issues arise:
1. Keep old code in a `legacy/` directory
2. Git allows easy revert: `git revert <migration-commit>`
3. Dual deployment during transition period

---

**Note**: This migration is **optional** for v2.0. All new features work without restructuring. The migration can be done gradually as time permits.
