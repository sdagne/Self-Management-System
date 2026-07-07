# Database Operations Runbook

**System**: Self Management System — PostgreSQL  
**Owner**: DBA / Backend Team  
**Last Updated**: 2026-07-06

---

## Table of Contents

1. [Connection Information](#connection-information)
2. [Health Checks](#health-checks)
3. [Backup Procedures](#backup-procedures)
4. [Restore from Backup](#restore-from-backup)
5. [Schema Migrations](#schema-migrations)
6. [Performance Tuning](#performance-tuning)
7. [Emergency Recovery](#emergency-recovery)
8. [Maintenance Tasks](#maintenance-tasks)

---

## Connection Information

```bash
# Connect to production PostgreSQL (via kubectl)
kubectl exec -it postgres-0 -n queue-management-prod -- \
  psql -U queue_user -d queue_db

# Connect via port-forward (from local machine, for admin tools)
kubectl port-forward pod/postgres-0 5432:5432 -n queue-management-prod
# Then: psql postgresql://queue_user:$PASS@localhost:5432/queue_db

# Get connection string from secret
kubectl get secret postgres-credentials -n queue-management-prod \
  -o jsonpath='{.data.DATABASE_URL}' | base64 -d
```

---

## Health Checks

```bash
# ── Basic connectivity check ──────────────────────────────────────────────────
kubectl exec -it postgres-0 -n queue-management-prod -- pg_isready -U queue_user

# ── Check running queries ─────────────────────────────────────────────────────
kubectl exec -it postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "
    SELECT pid, now() - pg_stat_activity.query_start AS duration,
           query, state
    FROM pg_stat_activity
    WHERE state = 'active'
    ORDER BY duration DESC;
  "

# ── Check connections count ───────────────────────────────────────────────────
kubectl exec -it postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "
    SELECT count(*) AS total_connections,
           max_conn,
           count(*) * 100 / max_conn AS usage_percent
    FROM pg_stat_activity,
         (SELECT setting::int AS max_conn FROM pg_settings WHERE name = 'max_connections') mc
    GROUP BY max_conn;
  "

# ── Table sizes ───────────────────────────────────────────────────────────────
kubectl exec -it postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "
    SELECT schemaname, tablename,
           pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
    FROM pg_tables
    WHERE schemaname = 'public'
    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
  "

# ── Index usage (find unused indexes) ────────────────────────────────────────
kubectl exec -it postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "
    SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
    FROM pg_stat_user_indexes
    ORDER BY idx_scan ASC
    LIMIT 20;
  "

# ── Slow queries (requires pg_stat_statements extension) ─────────────────────
kubectl exec -it postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "
    SELECT substring(query, 1, 80) AS short_query,
           calls, mean_exec_time::int AS mean_ms,
           total_exec_time::int AS total_ms,
           rows
    FROM pg_stat_statements
    WHERE mean_exec_time > 100
    ORDER BY mean_exec_time DESC
    LIMIT 20;
  "
```

---

## Backup Procedures

### Automated Backups

Daily backups run automatically via the Kubernetes CronJob at 02:00 UTC.

```bash
# Check backup CronJob status
kubectl get cronjob database-backup -n queue-management-prod
kubectl get jobs -n queue-management-prod | grep backup

# View last backup job logs
kubectl logs job/$(kubectl get jobs -n queue-management-prod \
  --sort-by=.metadata.creationTimestamp | grep backup | tail -1 | awk '{print $1}') \
  -n queue-management-prod
```

### Manual Backup (On-Demand)

```bash
# Trigger an immediate backup job
kubectl create job --from=cronjob/database-backup \
  manual-backup-$(date +%Y%m%d-%H%M%S) \
  -n queue-management-prod

# Or run the backup script directly (from a node with kubectl access)
cd /path/to/queue-management
bash scripts/backup/backup-database.sh

# Verify backup exists in S3
aws s3 ls s3://$BACKUP_BUCKET/backups/postgres/ | tail -5
```

### Backup Verification

```bash
# Download latest backup and verify it's valid
LATEST=$(aws s3 ls s3://$BACKUP_BUCKET/backups/postgres/ \
  | sort | tail -1 | awk '{print $4}')

aws s3 cp s3://$BACKUP_BUCKET/backups/postgres/$LATEST /tmp/verify-backup.sql.gz

# Restore to a test database to verify
gunzip -c /tmp/verify-backup.sql.gz | \
  psql postgresql://test_user:test_pass@localhost:5432/test_db

echo "Backup contains $(psql -t -c "SELECT count(*) FROM tickets" \
  postgresql://test_user:test_pass@localhost:5432/test_db) tickets"
```

---

## Restore from Backup

> ⚠️ **CAUTION**: This will overwrite the current database. Always take a pre-restore backup first.

### Quick Restore (Last Known Good Backup)

```bash
# Use the automated restore script
bash scripts/backup/restore-database.sh

# The script will:
# 1. List available backups
# 2. Prompt you to select one
# 3. Take a safety backup of current DB
# 4. Perform the restore
# 5. Run Alembic migrations to catch up
```

### Manual Restore

```bash
# 1. Scale down the API to prevent writes during restore
kubectl scale deployment prod-queue-api --replicas=0 -n queue-management-prod
kubectl scale deployment celery-worker --replicas=0 -n queue-management-prod

# 2. Take a safety snapshot
kubectl exec postgres-0 -n queue-management-prod -- \
  pg_dump -U queue_user queue_db | \
  gzip > /tmp/pre-restore-$(date +%Y%m%d-%H%M%S).sql.gz

# 3. Download the backup to restore
aws s3 cp s3://$BACKUP_BUCKET/backups/postgres/queue_backup_YYYYMMDD_HHMMSS.sql.gz /tmp/restore.sql.gz

# 4. Drop and recreate the database
kubectl exec postgres-0 -n queue-management-prod -- \
  psql -U postgres -c "
    SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'queue_db';
    DROP DATABASE IF EXISTS queue_db;
    CREATE DATABASE queue_db OWNER queue_user;
  "

# 5. Restore
kubectl exec -i postgres-0 -n queue-management-prod -- \
  gunzip -c /tmp/restore.sql.gz | psql -U queue_user -d queue_db

# 6. Run migrations to bring schema up to date
kubectl run alembic-upgrade --rm -i --restart=Never \
  --image=ghcr.io/your-org/queue-management-api:latest \
  --namespace=queue-management-prod \
  --env="DATABASE_URL=$DATABASE_URL" \
  -- alembic upgrade head

# 7. Scale API back up
kubectl scale deployment prod-queue-api --replicas=3 -n queue-management-prod
kubectl scale deployment celery-worker --replicas=2 -n queue-management-prod

# 8. Verify
curl -f https://queue.production.example.com/health
```

---

## Schema Migrations

### Running Migrations

```bash
# Apply all pending migrations (automatically runs in CD pipeline)
kubectl run alembic-migrate --rm -i --restart=Never \
  --image=ghcr.io/your-org/queue-management-api:latest \
  --namespace=queue-management-prod \
  --env="DATABASE_URL=$DATABASE_URL" \
  -- alembic upgrade head

# Check current migration version
kubectl exec -it <api-pod> -n queue-management-prod -- alembic current

# View migration history
kubectl exec -it <api-pod> -n queue-management-prod -- alembic history --verbose
```

### Creating a New Migration

```bash
# (Run locally with DB access configured)
source .venv/bin/activate
export DATABASE_URL="postgresql://..."

# Auto-generate from model changes
alembic revision --autogenerate -m "add_column_X_to_tickets"

# Review the generated file in alembic/versions/
# ALWAYS review before running!

# Test locally first
alembic upgrade head
alembic downgrade -1  # Test rollback
alembic upgrade head  # Re-apply
```

### Rolling Back a Migration

```bash
# Rollback one step
alembic downgrade -1

# Rollback to a specific revision
alembic downgrade <revision_id>

# Rollback all (WARNING: destructive)
alembic downgrade base
```

---

## Performance Tuning

### Connection Pool Status

```python
# Run from inside a pod to check pool health
python -c "
from database import engine
pool = engine.pool
print(f'Pool size (configured): {pool.size()}')
print(f'Connections checked out: {pool.checkedout()}')
print(f'Overflow connections: {pool.overflow()}')
print(f'Total connections: {pool.checkedout() + pool.size()}')
"
```

### Recommended PostgreSQL Configuration

```sql
-- Apply tuning params (requires postgres superuser)
-- Run once after provisioning the database

-- Connection limits
ALTER SYSTEM SET max_connections = 200;

-- Memory tuning (adjust for your instance size)
-- For 4GB RAM instance:
ALTER SYSTEM SET shared_buffers = '1GB';
ALTER SYSTEM SET effective_cache_size = '3GB';
ALTER SYSTEM SET maintenance_work_mem = '256MB';
ALTER SYSTEM SET work_mem = '16MB';

-- Query planner
ALTER SYSTEM SET random_page_cost = 1.1;         -- For SSDs
ALTER SYSTEM SET effective_io_concurrency = 200; -- For SSDs

-- WAL and checkpoints
ALTER SYSTEM SET wal_buffers = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET max_wal_size = '4GB';

-- Logging
ALTER SYSTEM SET log_min_duration_statement = 500; -- Log queries > 500ms
ALTER SYSTEM SET log_checkpoints = ON;

-- Enable pg_stat_statements
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';

SELECT pg_reload_conf();
```

### Adding Missing Indexes

```sql
-- Find sequential scans on large tables (candidates for indexing)
SELECT schemaname, tablename, seq_scan, seq_tup_read,
       idx_scan, idx_tup_fetch
FROM pg_stat_user_tables
WHERE seq_scan > 100
ORDER BY seq_tup_read DESC;

-- Common indexes to add if missing
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tickets_status
  ON tickets(status) WHERE status IN ('waiting', 'called', 'serving');

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tickets_citizen_id
  ON tickets(citizen_id);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tickets_created_at
  ON tickets(created_at DESC);

CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_audit_logs_timestamp
  ON audit_logs(timestamp DESC);
```

---

## Emergency Recovery

### Database Unresponsive

```bash
# 1. Check PostgreSQL process
kubectl exec postgres-0 -n queue-management-prod -- pg_isready

# 2. Check disk space
kubectl exec postgres-0 -n queue-management-prod -- df -h /var/lib/postgresql

# 3. Check postgres logs
kubectl logs postgres-0 -n queue-management-prod --tail=100

# 4. If disk full — emergency cleanup
kubectl exec postgres-0 -n queue-management-prod -- \
  psql -U postgres -c "VACUUM FULL ANALYZE audit_logs;"

# 5. Kill long-running queries blocking recovery
kubectl exec postgres-0 -n queue-management-prod -- \
  psql -U postgres -c "
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE state = 'active'
    AND query_start < NOW() - INTERVAL '10 minutes'
    AND query NOT LIKE '%pg_terminate%';
  "
```

### Data Corruption Detected

1. **Immediately** scale API to 0 replicas to prevent further writes
2. Notify the DBA team and incident commander
3. Take a snapshot of the corrupted state for forensics
4. Restore from the most recent clean backup (see [Restore from Backup](#restore-from-backup))
5. Run data validation queries to verify integrity after restore

---

## Maintenance Tasks

### Weekly

```bash
# Update statistics for query planner
kubectl exec postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "ANALYZE VERBOSE;"

# Reclaim space from deleted rows
kubectl exec postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "VACUUM (VERBOSE, ANALYZE);"
```

### Monthly

```bash
# Purge old audit logs (> 90 days)
kubectl exec postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "
    DELETE FROM audit_logs
    WHERE timestamp < NOW() - INTERVAL '90 days';
    VACUUM audit_logs;
  "

# Purge completed/expired tickets (> 30 days)
kubectl exec postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "
    DELETE FROM tickets
    WHERE status IN ('completed', 'expired', 'cancelled')
    AND created_at < NOW() - INTERVAL '30 days';
    VACUUM tickets;
  "

# Rebuild bloated indexes
kubectl exec postgres-0 -n queue-management-prod -- \
  psql -U queue_user queue_db -c "
    REINDEX INDEX CONCURRENTLY idx_tickets_status;
    REINDEX INDEX CONCURRENTLY idx_tickets_created_at;
  "
```

### Quarterly

- Review and rotate database credentials (update Vault secrets)
- Test full backup restore in staging environment
- Review and update PostgreSQL configuration for current load
- Audit database users and permissions
