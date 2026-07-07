# Production Infrastructure - Quick Reference

## 🚀 What's New (v2.0)

All HIGH PRIORITY infrastructure items have been implemented:

### ✅ 1. Kubernetes Deployment
- Full K8s manifests in `k8s/` directory
- Base configuration + environment overlays (dev/staging/prod)
- Auto-scaling (HPA): 3-20 pods based on CPU/memory
- Pod anti-affinity for high availability
- Pod Disruption Budget (PDB) for zero-downtime deployments

### ✅ 2. Secrets Management
- **External Secrets Operator** integration
- Supports HashiCorp Vault, AWS Secrets Manager, Azure Key Vault
- Auto-sync secrets every hour
- See: `k8s/overlays/prod/external-secrets.yaml`

### ✅ 3. Automated CI/CD Pipeline
- **GitHub Actions** workflow: `.github/workflows/deploy.yml`
- Automated deployments:
  - `develop` branch → Dev environment
  - `main` branch → Staging (with DB migrations)
  - Release tags → Production (with canary deployment)
- Automatic rollback on failure
- Smoke tests before production

### ✅ 4. High Availability Setup
- **Multi-pod deployment** with anti-affinity rules
- **Load balancing** via Kubernetes Ingress
- **Database**: PostgreSQL StatefulSet (supports HA via managed services)
- **Cache**: Redis with optional clustering
- **Message Queue**: Celery workers with auto-scaling
- Multi-region deployment ready

### ✅ 5. Automated Backup/Restore
- **Daily automated backups** via CronJob (2 AM)
- S3-compatible storage integration
- 30-day retention policy
- Scripts: `scripts/backup/`
  - `backup-database.sh` - Create backups
  - `restore-database.sh` - Restore from backup
- Kubernetes CronJob: `k8s/base/backup-cronjob.yaml`

### ✅ 6. Caching Layer (Redis)
- **Redis** integration for performance
- Cache client: `app/core/redis_client.py`
- Features:
  - Connection pooling
  - Cache decorators (`@cache_result`)
  - Rate limiting with sliding window
  - Graceful fallback when Redis unavailable

### ✅ 7. Message Queue (Async Processing)
- **Celery** with Redis backend
- Configuration: `app/core/celery_config.py`
- Async tasks: `app/services/tasks.py`
  - Telegram notifications (non-blocking)
  - Ticket reminders
  - Daily reports
  - Cleanup tasks
- **Celery Beat** for scheduled tasks
- **Flower** UI for monitoring (port 5555)

### ✅ 8. Proper Project Structure
- Directory structure created:
  ```
  app/
  ├── api/           # API routes
  ├── core/          # Auth, security, Redis, Celery
  ├── db/            # Database models
  ├── services/      # Business logic, tasks
  └── utils/         # Utilities
  k8s/               # Kubernetes manifests
  scripts/backup/    # Backup scripts
  ```
- Modular, production-ready architecture

## 📦 Quick Start

### Local Development with Full Stack

```bash
# Install new dependencies
pip install -r requirements.txt

# Start all services (app, db, redis, celery, flower)
docker-compose up -d

# View services:
# - API: http://localhost:8001
# - Flower (Celery UI): http://localhost:5555
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (with profile: monitoring)
```

### Deploy to Kubernetes

```bash
# Production deployment
cd k8s/overlays/prod
kubectl apply -k .

# Watch rollout
kubectl rollout status deployment/prod-queue-api -n queue-management-prod

# Check status
kubectl get pods -n queue-management-prod
```

## 📚 New Components

### Redis Cache
```python
from app.core.redis_client import RedisClient, cache_result

# Get Redis client
redis = RedisClient.get_client()

# Use cache decorator
@cache_result(ttl=300)
def expensive_function():
    return complex_calculation()
```

### Celery Tasks
```python
from app.services.tasks import send_telegram_notification

# Send async notification
send_telegram_notification.delay(
    chat_id="123456",
    message="Your ticket is ready!",
    ticket_number="IM-001"
)
```

### Kubernetes Resources

| Resource | Purpose | Replicas |
|----------|---------|----------|
| `queue-api` | Main API server | 3-20 (HPA) |
| `celery-worker` | Async task processing | 2 |
| `celery-beat` | Task scheduler | 1 |
| `postgres` | Database (StatefulSet) | 1 |
| `redis` | Cache & message broker | 1 |

## 🔧 Configuration

### Environment Variables (New)

```bash
# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Secrets (loaded from Vault in production)
# See .env.example for full list
```

### Docker Compose Services

- `app` - FastAPI application
- `db` - PostgreSQL database
- `redis` - Redis cache & broker
- `celery-worker` - Background task workers
- `celery-beat` - Periodic task scheduler
- `flower` - Celery monitoring dashboard
- `prometheus` - Metrics collection
- `grafana` - Metrics visualization (optional)

## 🛠️ Management Commands

### Backups

```bash
# Manual backup
./scripts/backup/backup-database.sh

# Restore from backup
./scripts/backup/restore-database.sh /path/to/backup.sql.gz

# In Kubernetes
kubectl create job --from=cronjob/database-backup manual-backup -n queue-management-prod
```

### Scaling

```bash
# Scale API pods
kubectl scale deployment prod-queue-api --replicas=10 -n queue-management-prod

# Scale Celery workers
kubectl scale deployment celery-worker --replicas=5 -n queue-management-prod

# Update HPA limits
kubectl patch hpa prod-queue-api-hpa --patch '{"spec":{"maxReplicas":30}}'
```

### Monitoring

```bash
# View Celery tasks (local)
open http://localhost:5555

# View Prometheus metrics (local)
open http://localhost:9090

# View logs
kubectl logs -f deployment/prod-queue-api -n queue-management-prod

# View Celery worker logs
kubectl logs -f deployment/celery-worker -n queue-management-prod
```

## 📊 Health Checks

### Application Health

```bash
# Health endpoint
curl http://localhost:8001/health

# Metrics endpoint
curl http://localhost:8001/metrics

# Queue status
curl http://localhost:8001/api/display/queue-status
```

### Infrastructure Health

```bash
# All pods running
kubectl get pods -n queue-management-prod

# HPA status
kubectl get hpa -n queue-management-prod

# Recent events
kubectl get events -n queue-management-prod --sort-by='.lastTimestamp'
```

## 🔐 Security

### Secrets in Production

Never commit secrets! Use:

1. **Local Dev**: `.env` file (gitignored)
2. **Kubernetes**: External Secrets Operator with Vault
3. **GitHub Actions**: GitHub Secrets

### Updating Production Secrets

```bash
# Update in Vault
vault kv put secret/queue-management/prod secret_key="new-key"

# Force sync (or wait 1 hour)
kubectl annotate externalsecret app-secrets force-sync="$(date +%s)"
```

## 📈 Performance

### Redis Cache Hit Ratio

Aim for >80% cache hit ratio:

```bash
# View metrics
curl http://localhost:8001/metrics | grep redis_cache
```

### Celery Task Processing

Monitor via Flower:
- Task success rate: >95%
- Average task time: <10s
- Queue length: <1000

## 🚨 Troubleshooting

### Redis Not Available

Application gracefully degrades:
- Cache operations no-op
- Synchronous task execution
- Warning logs emitted

### Celery Workers Stuck

```bash
# Restart workers
kubectl rollout restart deployment/celery-worker -n queue-management-prod

# Check Flower dashboard
open http://localhost:5555
```

### Database Connection Pool Exhausted

```bash
# Scale down connections
kubectl set env deployment/prod-queue-api SQLALCHEMY_POOL_SIZE=10

# Or scale up pods
kubectl scale deployment prod-queue-api --replicas=10
```

## 📖 Further Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete production deployment guide
- **[README.md](README.md)** - Main application documentation
- **[.github/workflows/deploy.yml](.github/workflows/deploy.yml)** - CI/CD pipeline
- **[k8s/](k8s/)** - Kubernetes manifests and overlays

## 🎯 Migration from v1.0

### For Existing Deployments

1. Install new dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Update docker-compose:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

3. Run database migrations:
   ```bash
   alembic upgrade head
   ```

4. Update environment variables (see `.env.example`)

### Breaking Changes

- **None!** All new features are additive
- Redis is optional (graceful fallback)
- Celery is optional (sync fallback)

## 🎉 Benefits

| Before (v1.0) | After (v2.0) |
|---------------|--------------|
| Single instance | Auto-scaled 3-20 pods |
| Manual deployment | GitOps CD pipeline |
| No backups | Daily automated backups |
| Synchronous tasks | Async with Celery |
| No caching | Redis cache layer |
| Flat structure | Modular packages |
| Secrets in .env | External Secrets Operator |
| No HA | Multi-pod, multi-region ready |

---

**Version**: 2.0.0  
**Last Updated**: July 6, 2026
