#!/bin/bash
# Automated PostgreSQL backup script for Kubernetes

set -euo pipefail

# Configuration
NAMESPACE="${NAMESPACE:-queue-management-prod}"
POD_NAME=$(kubectl get pods -n "$NAMESPACE" -l app=postgres -o jsonpath='{.items[0].metadata.name}')
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
S3_BUCKET="${S3_BUCKET:-queue-management-backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="queue_management_backup_${TIMESTAMP}.sql.gz"

echo "🔄 Starting database backup at $(date)"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Perform backup
echo "📦 Creating backup: $BACKUP_FILE"
kubectl exec -n "$NAMESPACE" "$POD_NAME" -- bash -c \
  "pg_dump -U \$POSTGRES_USER -d queue_management | gzip" \
  > "$BACKUP_DIR/$BACKUP_FILE"

# Verify backup
if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
  SIZE=$(du -h "$BACKUP_DIR/$BACKUP_FILE" | cut -f1)
  echo "✅ Backup created successfully: $BACKUP_FILE ($SIZE)"
else
  echo "❌ Backup failed!"
  exit 1
fi

# Upload to S3 (AWS CLI required)
if command -v aws &> /dev/null; then
  echo "☁️ Uploading to S3..."
  aws s3 cp "$BACKUP_DIR/$BACKUP_FILE" "s3://$S3_BUCKET/postgres/$BACKUP_FILE" \
    --storage-class STANDARD_IA
  
  if [ $? -eq 0 ]; then
    echo "✅ Backup uploaded to S3"
  else
    echo "⚠️ S3 upload failed, but local backup exists"
  fi
fi

# Clean up old backups (local)
echo "🧹 Cleaning up old backups (older than $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "queue_management_backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Clean up old backups (S3)
if command -v aws &> /dev/null; then
  CUTOFF_DATE=$(date -d "$RETENTION_DAYS days ago" +%Y-%m-%d)
  aws s3 ls "s3://$S3_BUCKET/postgres/" | while read -r line; do
    FILE_DATE=$(echo "$line" | awk '{print $1}')
    FILE_NAME=$(echo "$line" | awk '{print $4}')
    
    if [[ "$FILE_DATE" < "$CUTOFF_DATE" ]]; then
      echo "Deleting old backup: $FILE_NAME"
      aws s3 rm "s3://$S3_BUCKET/postgres/$FILE_NAME"
    fi
  done
fi

echo "✅ Backup completed successfully at $(date)"

# Send notification (optional)
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
  curl -X POST "$SLACK_WEBHOOK_URL" \
    -H 'Content-Type: application/json' \
    -d "{\"text\":\"✅ Database backup completed: $BACKUP_FILE ($SIZE)\"}"
fi
