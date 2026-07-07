# Production Deployment Guide

## Overview

This guide covers deploying the Self Management System to production using Kubernetes, including:

- ✅ High Availability (HA) configuration
- ✅ Auto-scaling (HPA)
- ✅ Redis caching layer
- ✅ Celery message queue for async tasks
- ✅ Automated backups
- ✅ Secrets management
- ✅ CI/CD pipeline
- ✅ Multi-region support

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Load Balancer (Ingress)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴─────────────┐
        │                          │
    ┌───▼────┐  ┌────────┐  ┌────▼───┐
    │  API   │  │  API   │  │  API   │  (Auto-scaled 3-20 pods)
    │  Pod   │  │  Pod   │  │  Pod   │
    └───┬────┘  └───┬────┘  └───┬────┘
        │           │           │
        └───────┬───┴───────┬───┘
                │           │
        ┌───────▼──┐    ┌──▼──────┐
        │  Redis   │    │ Celery  │
        │  Cache   │    │ Workers │
        └──────────┘    └────┬────┘
                             │
                      ┌──────▼──────┐
                      │  PostgreSQL │
                      │ (StatefulSet)│
                      └─────────────┘
```

## Prerequisites

### Required Tools

```bash
# Kubernetes CLI
kubectl version --client

# Kustomize
kustomize version

# Helm (for dependencies)
helm version

# Docker
docker --version

# Optional: k9s for cluster management
k9s version
```

### Required Access

- Kubernetes cluster (GKE, EKS, AKS, or on-premises)
- Container registry access (GitHub Container Registry, Docker Hub, etc.)
- Secrets management system (Vault, AWS Secrets Manager, etc.)
- S3-compatible storage for backups

## Quick Start

### 1. Install External Secrets Operator

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace
```

### 2. Configure Secrets in Vault

```bash
# Set up Vault secrets
vault kv put secret/queue-management/prod \
  secret_key="your-secret-key-here" \
  admin_token="your-admin-token" \
  counter_token="your-counter-token" \
  telegram_bot_token="your-telegram-bot-token"

vault kv put secret/queue-management/prod/postgres \
  username="queueuser" \
  password="secure-password-here" \
  connection_string="postgresql://queueuser:password@postgres-service:5432/queue_management"
```

### 3. Deploy to Production

```bash
# Navigate to K8s production overlay
cd k8s/overlays/prod

# Review the configuration
kustomize build .

# Apply to cluster
kubectl apply -k .

# Watch the rollout
kubectl rollout status deployment/prod-queue-api -n queue-management-prod
```

### 4. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n queue-management-prod

# Check services
kubectl get svc -n queue-management-prod

# Check ingress
kubectl get ingress -n queue-management-prod

# Test health endpoint
curl https://queue.production.example.com/health
```

## High Availability Configuration

### Pod Distribution

- **Minimum replicas**: 3
- **Maximum replicas**: 20 (HPA)
- **Pod Anti-Affinity**: Ensures pods are distributed across different nodes
- **Pod Disruption Budget**: Maintains at least 2 pods during voluntary disruptions

### Auto-Scaling

Horizontal Pod Autoscaler (HPA) configuration:

```yaml
metrics:
  - CPU: 70% average utilization
  - Memory: 80% average utilization

behavior:
  scaleUp: Fast (up to 100% or 2 pods per 30s)
  scaleDown: Conservative (50% per 60s, 5min stabilization)
```

### Database HA

For production, configure PostgreSQL in HA mode:

#### Option 1: Managed Service (Recommended)

```yaml
# Use cloud provider's managed PostgreSQL
# - AWS RDS
# - Google Cloud SQL
# - Azure Database for PostgreSQL

DATABASE_URL: "postgresql://user:pass@managed-db.region.provider.com:5432/queue"
```

#### Option 2: Self-Managed Cluster

```bash
# Install PostgreSQL Operator
kubectl apply -f https://raw.githubusercontent.com/zalando/postgres-operator/master/manifests/operator.yaml

# Deploy HA PostgreSQL cluster
kubectl apply -f k8s/postgres-ha-cluster.yaml
```

### Redis HA

For production, use Redis Cluster or Sentinel:

```bash
# Install Redis Operator
helm repo add ot-helm https://ot-container-kit.github.io/helm-charts/
helm install redis-operator ot-helm/redis-operator

# Deploy Redis Cluster
kubectl apply -f k8s/redis-cluster.yaml
```

## Multi-Region Deployment

### Active-Active Configuration

```yaml
# Region 1: us-east-1
context: prod-us-east-1
kubectl config use-context prod-us-east-1
kubectl apply -k k8s/overlays/prod

# Region 2: eu-west-1
context: prod-eu-west-1
kubectl config use-context prod-eu-west-1
kubectl apply -k k8s/overlays/prod
```

### Global Load Balancing

Use a global load balancer:

- **AWS**: Route 53 with health checks
- **GCP**: Cloud Load Balancing
- **Azure**: Traffic Manager
- **Cloudflare**: Load Balancing with health checks

## Backup & Disaster Recovery

### Automated Backups

Backups run daily at 2 AM via CronJob:

```bash
# View backup schedule
kubectl get cronjob -n queue-management-prod

# Trigger manual backup
kubectl create job --from=cronjob/database-backup \
  manual-backup-$(date +%s) \
  -n queue-management-prod

# List backups in S3
aws s3 ls s3://queue-management-backups/postgres/
```

### Restore from Backup

```bash
# Download restore script
./scripts/backup/restore-database.sh

# Restore specific backup
export NAMESPACE=queue-management-prod
./scripts/backup/restore-database.sh s3://queue-management-backups/postgres/queue_management_20260706_020000.sql.gz
```

### Disaster Recovery Testing

Perform quarterly DR drills:

```bash
# 1. Create test namespace
kubectl create namespace dr-test

# 2. Restore backup to test environment
export NAMESPACE=dr-test
./scripts/backup/restore-database.sh <latest-backup>

# 3. Deploy application to test namespace
kubectl apply -k k8s/overlays/prod -n dr-test

# 4. Run verification tests
./scripts/dr-verification-tests.sh

# 5. Clean up
kubectl delete namespace dr-test
```

## Monitoring & Alerts

### Prometheus Metrics

Exposed at `/metrics` endpoint:

- `http_requests_total` - Total HTTP requests
- `http_request_duration_seconds` - Request latency
- `queue_waiting_tickets` - Current waiting tickets
- `celery_task_success_total` - Successful async tasks
- `redis_cache_hit_ratio` - Cache hit percentage

### Grafana Dashboards

Access Grafana: `http://grafana.monitoring.example.com`

Default dashboards:
- Application Performance
- Self Management KPIs
- Infrastructure Health
- Celery Task Monitoring

### Alerting Rules

Critical alerts configured:

- High error rate (>1% 5xx responses)
- Pod crash loops
- Database connection failures
- High memory/CPU usage
- Backup failures

## Scaling Guidelines

### Vertical Scaling (Resources)

Update resource limits in deployment:

```yaml
resources:
  requests:
    cpu: "2000m"
    memory: "2Gi"
  limits:
    cpu: "4000m"
    memory: "4Gi"
```

### Horizontal Scaling (Replicas)

HPA automatically scales, but you can set custom min/max:

```bash
kubectl patch hpa prod-queue-api-hpa -n queue-management-prod \
  --patch '{"spec":{"minReplicas":5,"maxReplicas":30}}'
```

## Security Best Practices

### Network Policies

```bash
# Apply network policies to restrict traffic
kubectl apply -f k8s/network-policies/
```

### Pod Security Standards

All pods run with:
- Non-root user (UID 1000)
- Read-only root filesystem
- No privilege escalation
- Dropped capabilities

### Secrets Rotation

Rotate secrets quarterly:

```bash
# Update secrets in Vault
vault kv put secret/queue-management/prod \
  secret_key="new-rotated-key"

# External Secrets Operator will auto-sync within 1 hour
# Or force refresh:
kubectl annotate externalsecret app-secrets \
  force-sync="$(date +%s)" \
  -n queue-management-prod
```

## Cost Optimization

### Resource Right-Sizing

Review monthly:

```bash
# Get resource usage
kubectl top pods -n queue-management-prod

# Analyze recommendations
kubectl describe vpa -n queue-management-prod
```

### Auto-Scaling Policies

- Scale down during off-peak hours (22:00 - 06:00 local time)
- Use spot/preemptible instances for Celery workers
- Enable cluster autoscaler

## Troubleshooting

### Common Issues

#### Pods Not Starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n queue-management-prod

# View logs
kubectl logs <pod-name> -n queue-management-prod

# Check events
kubectl get events -n queue-management-prod --sort-by='.lastTimestamp'
```

#### Database Connection Issues

```bash
# Test database connectivity
kubectl run -it --rm debug --image=postgres:15 --restart=Never \
  -- psql -h postgres-service -U queueuser -d queue_management

# Check database pod
kubectl logs postgres-0 -n queue-management-prod
```

#### Redis Connection Issues

```bash
# Test Redis connectivity
kubectl run -it --rm redis-test --image=redis:7-alpine --restart=Never \
  -- redis-cli -h redis-service ping
```

## CI/CD Pipeline

### GitHub Actions Workflow

Automated deployment on:
- **Develop branch** → Dev environment
- **Main branch** → Staging environment (after migration)
- **Release tag** → Production (with canary deployment)

### Manual Deployment

```bash
# Trigger deployment workflow
gh workflow run deploy.yml \
  -f environment=production \
  -f version=v2.0.0
```

### Rollback

```bash
# Automatic rollback on failure
# Or manual:
kubectl rollout undo deployment/prod-queue-api -n queue-management-prod

# Rollback to specific revision
kubectl rollout undo deployment/prod-queue-api \
  --to-revision=5 \
  -n queue-management-prod
```

## Performance Tuning

### Redis Optimization

```yaml
# Increase cache size for high-traffic environments
maxmemory: 512mb  # or 1gb, 2gb based on needs
maxmemory-policy: allkeys-lru
```

### Database Connection Pooling

```python
# config.py
SQLALCHEMY_POOL_SIZE = 20
SQLALCHEMY_MAX_OVERFLOW = 40
SQLALCHEMY_POOL_TIMEOUT = 30
SQLALCHEMY_POOL_RECYCLE = 3600
```

### Celery Worker Tuning

```yaml
# Adjust concurrency based on workload
command:
  - --concurrency=8  # Increase for CPU-bound tasks
  - --max-tasks-per-child=500  # Prevent memory leaks
```

## Maintenance Windows

### Planned Maintenance

```bash
# 1. Set maintenance mode
kubectl scale deployment prod-queue-api --replicas=1 -n queue-management-prod

# 2. Drain specific node
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# 3. Perform maintenance

# 4. Uncordon node
kubectl uncordon <node-name>

# 5. Scale back up
kubectl scale deployment prod-queue-api --replicas=5 -n queue-management-prod
```

## Support & Further Reading

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [External Secrets Operator](https://external-secrets.io/)
- [Prometheus Operator](https://prometheus-operator.dev/)
- [Celery Documentation](https://docs.celeryq.dev/)

---

**Last Updated**: July 6, 2026  
**Version**: 2.0.0
