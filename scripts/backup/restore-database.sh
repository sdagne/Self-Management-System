#!/bin/bash
# Database restore script

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-queue-management-prod}"
POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}')
BACKUP_FILE="${1:-}"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup-file.sql.gz>"
  echo ""
  echo "Available backups:"
  if command -v aws &> /dev/null; then
    aws s3 ls "s3://${S3_BUCKET:-queue-management-backups}/postgres/" | grep .sql.gz
  fi
  exit 1
fi

echo "⚠️  WARNING: This will restore the database from backup!"
echo "Database: queue_management"
echo "Backup: $BACKUP_FILE"
echo ""
read -p "Are you sure you want to continue? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
  echo "Restore cancelled"
  exit 0
fi

# Download from S3 if needed
if [[ "$BACKUP_FILE" =~ ^s3:// ]]; then
  echo "📥 Downloading backup from S3..."
  LOCAL_FILE="/tmp/$(basename "$BACKUP_FILE")"
  aws s3 cp "$BACKUP_FILE" "$LOCAL_FILE"
  BACKUP_FILE="$LOCAL_FILE"
fi

# Verify backup file exists
if [ ! -f "$BACKUP_FILE" ]; then
  echo "❌ Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "🔄 Starting database restore..."

# Create a pre-restore backup
echo "📦 Creating pre-restore backup..."
./backup-database.sh

# Drop all connections
echo "🔌 Dropping active connections..."
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- bash -c \
  "psql -U \$POSTGRES_USER -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'queue_management' AND pid <> pg_backend_pid();\""

# Drop and recreate database
echo "🗑️ Dropping database..."
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- bash -c \
  "psql -U \$POSTGRES_USER -d postgres -c 'DROP DATABASE IF EXISTS queue_management;'"

echo "📝 Creating database..."
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- bash -c \
  "psql -U \$POSTGRES_USER -d postgres -c 'CREATE DATABASE queue_management;'"

# Restore database
echo "📥 Restoring database from backup..."
gunzip < "$BACKUP_FILE" | kubectl exec -i -n "$NAMESPACE" "$POD_NAME" -- \
  psql -U \$POSTGRES_USER -d queue_management

if [ $? -eq 0 ]; then
  echo "✅ Database restored successfully!"
else
  echo "❌ Database restore failed!"
  exit 1
fi

# Verify restore
echo "🔍 Verifying restore..."
RECORD_COUNT=$(kubectl exec -n "$NAMESPACE" "$POD_NAME" -- bash -c \
  "psql -U \$POSTGRES_USER -d queue_management -t -c 'SELECT COUNT(*) FROM tickets;'")

echo "Records in tickets table: $(echo $RECORD_COUNT | tr -d ' ')"

echo "✅ Restore completed at $(date)"

# Send notification
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
  curl -X POST "$SLACK_WEBHOOK_URL" \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"⚠️ Database restored from backup: $BACKUP_FILE\"}"
fi
