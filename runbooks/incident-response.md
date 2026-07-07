# Incident Response Runbook

**System**: Self Management System  
**Owner**: Backend Engineering Team  
**Last Updated**: 2026-07-06

---

## Table of Contents

- [Incident Response Runbook](#incident-response-runbook)
  - [Table of Contents](#table-of-contents)
  - [Severity Levels](#severity-levels)
  - [Incident Commander Role](#incident-commander-role)
  - [High Error Rate](#high-error-rate)
    - [Immediate Steps (\< 5 min)](#immediate-steps--5-min)
    - [Investigation Steps](#investigation-steps)
    - [Mitigation Actions](#mitigation-actions)
    - [Rollback Command](#rollback-command)
  - [API Down](#api-down)
    - [Immediate Steps](#immediate-steps)
    - [Recovery Steps](#recovery-steps)
    - [Escalation Path](#escalation-path)
  - [High Latency](#high-latency)
    - [Investigation Steps](#investigation-steps-1)
    - [Common Causes \& Fixes](#common-causes--fixes)
  - [Pod Crash-Loop](#pod-crash-loop)
    - [OOMKilled Fix](#oomkilled-fix)
  - [Database Outage](#database-outage)
    - [Quick Recovery](#quick-recovery)
  - [Redis Outage](#redis-outage)
  - [Celery Worker Failure](#celery-worker-failure)
  - [Certificate Expiry](#certificate-expiry)
  - [Post-Incident Review](#post-incident-review)

---

## Severity Levels

| Severity | Impact | Response Time | Examples |
|----------|--------|---------------|---------|
| **P1 Critical** | Service completely down or data loss | < 15 min | API Down, DB unresponsive |
| **P2 High** | Degraded service, SLO breached | < 30 min | Error rate > 1%, latency > 2s |
| **P3 Medium** | Partial degradation, SLO at risk | < 2 hrs | Error rate 0.5–1%, one worker down |
| **P4 Low** | Minor issue, no user impact | < 24 hrs | Non-critical alert, cosmetic issue |

---

## Incident Commander Role

For P1/P2 incidents, designate an Incident Commander (IC) who:
- Creates a war-room channel (e.g., `#inc-YYYY-MM-DD-issue`)
- Coordinates response, delegates tasks
- Communicates status updates every 15 minutes
- Declares incident resolved and schedules post-mortem

---

## High Error Rate

**Alert**: `APIHighErrorRate` — HTTP 5xx rate > 1%  
**Dashboard**: https://grafana.example.com/d/queue-overview

### Immediate Steps (< 5 min)

```bash
# 1. Identify which endpoints are failing
kubectl logs -n queue-management-prod \
  -l app=queue-api --tail=100 | grep '"level": "ERROR"'

# 2. Check recent deployments (did a bad release just go out?)
kubectl rollout history deployment/prod-queue-api -n queue-management-prod

# 3. Check pod health
kubectl get pods -n queue-management-prod -l app=queue-api
kubectl describe pod <failing-pod> -n queue-management-prod
```

### Investigation Steps

```bash
# Check error breakdown by endpoint in Prometheus
# Query: sum(rate(http_requests_total{status=~"5.."}[5m])) by (handler)

# Check database connectivity from a pod
kubectl exec -it <api-pod> -n queue-management-prod -- \
  python -c "from database import engine; engine.connect(); print('DB OK')"

# Check Redis connectivity
kubectl exec -it <api-pod> -n queue-management-prod -- \
  python -c "import redis; r = redis.from_url('$REDIS_URL'); r.ping(); print('Redis OK')"
```

### Mitigation Actions

| Root Cause | Action |
|-----------|--------|
| Bad release | `kubectl rollout undo deployment/prod-queue-api -n queue-management-prod` |
| DB connection exhaustion | Restart pods: `kubectl rollout restart deployment/prod-queue-api` |
| External API timeout | Enable circuit breaker or return cached response |
| Config change | Revert ConfigMap and redeploy |

### Rollback Command

```bash
# Rollback to previous image
kubectl rollout undo deployment/prod-queue-api -n queue-management-prod

# Verify rollback
kubectl rollout status deployment/prod-queue-api -n queue-management-prod --timeout=5m
```

---

## API Down

**Alert**: `APIDown` — No healthy pods for > 1 minute  
**Severity**: P1 — Page on-call immediately

### Immediate Steps

```bash
# 1. Check pod count
kubectl get pods -n queue-management-prod -l app=queue-api

# 2. Check for recent events
kubectl get events -n queue-management-prod --sort-by='.lastTimestamp' | tail -20

# 3. Check if nodes are healthy
kubectl get nodes
kubectl describe node <node-name>

# 4. Check resource quotas
kubectl describe resourcequota -n queue-management-prod
kubectl top nodes
kubectl top pods -n queue-management-prod
```

### Recovery Steps

```bash
# Force a rollout restart
kubectl rollout restart deployment/prod-queue-api -n queue-management-prod

# If image pull is failing, check registry credentials
kubectl get secret registry-credentials -n queue-management-prod

# If ResourceQuota is the issue, temporarily scale down non-critical workloads
kubectl scale deployment/celery-beat --replicas=0 -n queue-management-prod

# Manually scale API up
kubectl scale deployment/prod-queue-api --replicas=3 -n queue-management-prod
```

### Escalation Path

1. Try rollback → wait 3 min
2. Try node drain + reschedule → wait 5 min
3. Escalate to Platform team (cluster issues)
4. If data loss suspected → escalate to DBA team

---

## High Latency

**Alert**: `APIHighLatency` — p95 > 500ms  
**Alert**: `APIVeryHighLatency` — p95 > 2s (P1)

### Investigation Steps

```bash
# 1. Check database query performance
# In Jaeger UI (https://tracing.example.com) filter by service=queue-api, min duration=500ms

# 2. Check slow queries in PostgreSQL
kubectl exec -it postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "
    SELECT query, calls, mean_exec_time, total_exec_time
    FROM pg_stat_statements
    ORDER BY mean_exec_time DESC
    LIMIT 10;
  "

# 3. Check connection pool utilisation
kubectl exec -it <api-pod> -n queue-management-prod -- \
  python -c "
    from database import engine
    pool = engine.pool
    print(f'Pool size: {pool.size()}')
    print(f'Checked out: {pool.checkedout()}')
    print(f'Overflow: {pool.overflow()}')
  "

# 4. Check Redis cache hit rate
kubectl exec -it redis-0 -n queue-management-prod -- \
  redis-cli info stats | grep -E "keyspace_hits|keyspace_misses"
```

### Common Causes & Fixes

| Cause | Fix |
|-------|-----|
| N+1 DB queries | Add eager loading; add index on hot columns |
| Cache miss storm | Warm cache after deployment: `python scripts/warm_cache.py` |
| Connection pool exhausted | Increase `pool_size` in database.py + redeploy |
| Missing DB index | Add index via Alembic migration |
| External API slow | Add timeout + fallback |

---

## Pod Crash-Loop

**Alert**: `PodCrashLooping`

```bash
# 1. Get crash reason
kubectl describe pod <pod> -n queue-management-prod | grep -A 20 "Last State:"

# 2. Get last logs before crash
kubectl logs <pod> -n queue-management-prod --previous --tail=100

# 3. Check for OOMKilled
kubectl get pod <pod> -n queue-management-prod -o jsonpath='{.status.containerStatuses[*].lastState.terminated.reason}'
# If OOMKilled → increase memory limits in deployment.yaml

# 4. Check liveness probe thresholds
kubectl get pod <pod> -n queue-management-prod -o jsonpath='{.spec.containers[*].livenessProbe}'
```

### OOMKilled Fix

```bash
# Temporarily patch memory limit
kubectl patch deployment prod-queue-api -n queue-management-prod \
  --type='json' \
  -p='[{"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/memory","value":"3Gi"}]'
```

---

## Database Outage

**Alert**: `PostgreSQLDown`  
**Runbook**: See [database-operations.md](./database-operations.md#emergency-recovery)

### Quick Recovery

```bash
# 1. Check PostgreSQL pod
kubectl get pods -n queue-management-prod -l app=postgres
kubectl logs postgres-0 -n queue-management-prod --tail=50

# 2. Check persistent volume
kubectl get pvc -n queue-management-prod
kubectl describe pvc postgres-data -n queue-management-prod

# 3. Force pod restart
kubectl delete pod postgres-0 -n queue-management-prod
# StatefulSet will recreate it

# 4. If data volume is corrupted, initiate restore from backup
# See: runbooks/database-operations.md#restore-from-backup
```

---

## Redis Outage

**Alert**: `RedisDown`

Redis is non-critical (app degrades gracefully with cache miss fallback). Celery task queue is impacted.

```bash
# 1. Check Redis pod
kubectl get pods -n queue-management-prod -l app=redis
kubectl logs -n queue-management-prod -l app=redis --tail=50

# 2. Restart Redis pod
kubectl delete pod -n queue-management-prod -l app=redis

# 3. Verify recovery
kubectl exec -it <redis-pod> -n queue-management-prod -- redis-cli ping
# Expected: PONG

# 4. Verify app reconnected (check logs for "Redis reconnected" message)
kubectl logs -n queue-management-prod -l app=queue-api --tail=50 | grep -i redis
```

---

## Celery Worker Failure

**Alert**: `CeleryWorkerDown`

Impact: Telegram notifications and reminders are queued but not delivered. Non-critical.

```bash
# 1. Check worker pods
kubectl get pods -n queue-management-prod -l app=celery-worker
kubectl logs -n queue-management-prod -l app=celery-worker --tail=100

# 2. Restart workers
kubectl rollout restart deployment/celery-worker -n queue-management-prod

# 3. Check queue backlog in Flower UI (if available)
# kubectl port-forward svc/flower 5555:5555 -n queue-management-prod
# Then open http://localhost:5555

# 4. Check dead letter queue
kubectl exec -it <celery-pod> -n queue-management-prod -- \
  celery -A app.core.celery_config inspect reserved
```

---

## Certificate Expiry

```bash
# List certificates and expiry
kubectl get certificate -n queue-management-prod

# Force renewal
kubectl annotate certificate queue-api-tls \
  cert-manager.io/issue-temporary-certificate="true" \
  --overwrite \
  -n queue-management-prod

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail=50
```

---

## Post-Incident Review

Schedule a blameless post-mortem within 48 hours of resolution.

**Post-Mortem Template**:

```markdown
## Incident: [Short description] — [Date]

**Duration**: [Start] → [End] ([X] hours [Y] minutes)
**Severity**: P[1-4]
**Impact**: [Number of users affected, services impacted]

### Timeline
| Time | Event |
|------|-------|
| HH:MM | Alert fired |
| HH:MM | IC assigned |
| HH:MM | Root cause identified |
| HH:MM | Mitigation applied |
| HH:MM | Incident resolved |

### Root Cause
[Clear description of the root cause]

### Contributing Factors
- [Factor 1]
- [Factor 2]

### What Went Well
- [Thing 1]

### Action Items
| Action | Owner | Due Date |
|--------|-------|----------|
| Add missing test | @engineer | [date] |
| Update alert threshold | @engineer | [date] |
```
