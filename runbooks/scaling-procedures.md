# Scaling & Deployment Procedures Runbook

**System**: Self Management System  
**Owner**: Platform / Backend Team  
**Last Updated**: 2026-07-06

---

## Table of Contents

1. [Horizontal Scaling](#horizontal-scaling)
2. [Vertical Scaling](#vertical-scaling)
3. [Emergency Scale-Up](#emergency-scale-up)
4. [Deployment Procedures](#deployment-procedures)
5. [Configuration Changes](#configuration-changes)
6. [Capacity Planning](#capacity-planning)
7. [Traffic Management](#traffic-management)

---

## Horizontal Scaling

### Current Auto-Scaling Configuration

The API auto-scales between **3 and 20 replicas** based on CPU and memory usage.

| Metric | Target | Scale Up | Scale Down |
|--------|--------|----------|-----------|
| CPU | 70% | +2 pods per 30s | -50% per 60s |
| Memory | 80% | +2 pods per 30s | -50% per 60s |

### Check Current Scale

```bash
# Check current replica count and HPA status
kubectl get hpa -n queue-management-prod
kubectl describe hpa queue-api-hpa -n queue-management-prod

# View pod distribution across nodes
kubectl get pods -n queue-management-prod -l app=queue-api \
  -o wide --sort-by='.spec.nodeName'

# Check CPU/memory per pod
kubectl top pods -n queue-management-prod -l app=queue-api
```

### Manual Scale Override

```bash
# Temporarily override HPA and manually set replicas
# (HPA will resume control once you remove the annotation or it next reconciles)
kubectl scale deployment prod-queue-api --replicas=10 -n queue-management-prod

# To disable HPA auto-scaling temporarily (e.g., during an incident)
kubectl annotate hpa queue-api-hpa \
  kubectl.kubernetes.io/last-applied-configuration- \
  -n queue-management-prod

# Re-enable HPA
kubectl apply -f k8s/base/hpa.yaml
```

### Adjust HPA Limits

```bash
# Increase max replicas (e.g., before a known peak event like a national holiday)
kubectl patch hpa queue-api-hpa -n queue-management-prod \
  --type='json' \
  -p='[{"op":"replace","path":"/spec/maxReplicas","value":30}]'

# Restore normal limits after event
kubectl patch hpa queue-api-hpa -n queue-management-prod \
  --type='json' \
  -p='[{"op":"replace","path":"/spec/maxReplicas","value":20}]'
```

### Scale Celery Workers

```bash
# Check worker load
kubectl top pods -n queue-management-prod -l app=celery-worker

# Scale up workers for high task volume
kubectl scale deployment celery-worker --replicas=8 -n queue-management-prod

# Scale back down
kubectl scale deployment celery-worker --replicas=2 -n queue-management-prod
```

---

## Vertical Scaling

### Increase Pod Resources

**When to use**: Persistent high CPU/memory despite horizontal scaling, or OOMKilled pods.

```bash
# Patch resources directly (immediate effect via rolling update)
kubectl patch deployment prod-queue-api -n queue-management-prod \
  --type='json' \
  -p='[
    {"op":"replace","path":"/spec/template/spec/containers/0/resources/requests/cpu","value":"1000m"},
    {"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/cpu","value":"4000m"},
    {"op":"replace","path":"/spec/template/spec/containers/0/resources/requests/memory","value":"1Gi"},
    {"op":"replace","path":"/spec/template/spec/containers/0/resources/limits/memory","value":"4Gi"}
  ]'

# Verify the patch
kubectl describe deployment prod-queue-api -n queue-management-prod | grep -A 8 "Limits:"
```

> **Remember**: Also update `k8s/base/deployment.yaml` and `k8s/overlays/prod/deployment-patch.yaml`  
> to persist the change through the next deployment.

---

## Emergency Scale-Up

**Use case**: Traffic spike, national event, system degradation.

```bash
# ── Step 1: Immediate scale-up ───────────────────────────────────────────────
echo "🚨 Emergency scale-up initiated by: $(whoami)"
kubectl scale deployment prod-queue-api --replicas=15 -n queue-management-prod
kubectl scale deployment celery-worker --replicas=6 -n queue-management-prod

# ── Step 2: Raise HPA max to prevent it from scaling back down ───────────────
kubectl patch hpa queue-api-hpa -n queue-management-prod \
  --type='json' \
  -p='[{"op":"replace","path":"/spec/maxReplicas","value":25}]'

# ── Step 3: Watch rollout ────────────────────────────────────────────────────
kubectl rollout status deployment/prod-queue-api -n queue-management-prod --timeout=5m
kubectl get pods -n queue-management-prod -l app=queue-api

# ── Step 4: Verify health ────────────────────────────────────────────────────
for i in {1..5}; do
  curl -sf https://queue.production.example.com/health && echo "✅ Pod $i healthy"
  sleep 2
done

# ── Step 5: Monitor error rate for 10 minutes ────────────────────────────────
# Watch: kubectl get hpa -n queue-management-prod -w

# ── Step 6: Scale back down after event (notify team first!) ─────────────────
kubectl scale deployment prod-queue-api --replicas=5 -n queue-management-prod
kubectl scale deployment celery-worker --replicas=2 -n queue-management-prod
kubectl patch hpa queue-api-hpa -n queue-management-prod \
  --type='json' \
  -p='[{"op":"replace","path":"/spec/maxReplicas","value":20}]'
```

---

## Deployment Procedures

### Standard Deployment (via CD Pipeline)

Deployments are automated via GitHub Actions. This is the preferred method.

1. Merge PR to `develop` → auto-deploys to **dev**
2. Merge to `main` → auto-deploys to **staging** (with smoke tests)
3. Create a GitHub Release (semver tag) → auto-deploys to **production** (with canary)

### Manual Deployment (Emergency Hotfix)

```bash
# Build and push hotfix image
docker build -t ghcr.io/your-org/queue-management-api:hotfix-$(date +%Y%m%d) .
docker push ghcr.io/your-org/queue-management-api:hotfix-$(date +%Y%m%d)

# Apply to production directly
export HOTFIX_IMAGE="ghcr.io/your-org/queue-management-api:hotfix-$(date +%Y%m%d)"

# Run migrations first
kubectl run alembic-migrate --rm -i --restart=Never \
  --image=$HOTFIX_IMAGE \
  --namespace=queue-management-prod \
  --env="DATABASE_URL=$(kubectl get secret postgres-credentials \
    -n queue-management-prod -o jsonpath='{.data.DATABASE_URL}' | base64 -d)" \
  -- alembic upgrade head

# Deploy
kubectl set image deployment/prod-queue-api \
  queue-api=$HOTFIX_IMAGE \
  -n queue-management-prod

# Monitor rollout
kubectl rollout status deployment/prod-queue-api -n queue-management-prod --timeout=5m
```

### Rollback Deployment

```bash
# Rollback to previous version
kubectl rollout undo deployment/prod-queue-api -n queue-management-prod

# Rollback to a specific revision
kubectl rollout history deployment/prod-queue-api -n queue-management-prod
kubectl rollout undo deployment/prod-queue-api --to-revision=<N> -n queue-management-prod

# Monitor rollback
kubectl rollout status deployment/prod-queue-api -n queue-management-prod

# Verify the running image
kubectl get deployment prod-queue-api -n queue-management-prod \
  -o jsonpath='{.spec.template.spec.containers[0].image}'
```

### Pre-Deployment Checklist

Before deploying to production:

- [ ] All tests pass in CI (unit + integration)
- [ ] Load tests pass in staging
- [ ] Database migrations are backward-compatible
- [ ] New environment variables are configured in Vault/secrets
- [ ] Runbooks are updated if new failure modes are introduced
- [ ] Monitoring alerts are configured for new features
- [ ] Rollback plan is documented and tested

---

## Configuration Changes

### Update Environment Variables

```bash
# Update a single env var (triggers rolling restart)
kubectl set env deployment/prod-queue-api \
  NEW_VARIABLE=new_value \
  -n queue-management-prod

# Update secrets via Vault (preferred — auto-syncs via ExternalSecrets)
# vault kv put secret/queue-management KEY=value

# Force sync of ExternalSecret immediately (don't wait for 1h refresh)
kubectl annotate externalsecret queue-app-secrets \
  force-sync=$(date +%s) \
  --overwrite \
  -n queue-management-prod
```

### Update ConfigMap

```bash
# Edit a ConfigMap directly (changes take effect on next pod restart)
kubectl edit configmap queue-api-config -n queue-management-prod

# Force a rolling restart to pick up new config
kubectl rollout restart deployment/prod-queue-api -n queue-management-prod
```

---

## Capacity Planning

### Current Benchmarks (from load tests)

| Scenario | RPS | p95 Latency | Pod Count |
|----------|-----|-------------|-----------|
| Baseline | 50 | 120ms | 3 |
| Peak weekday | 200 | 280ms | 6 |
| Peak event (holiday) | 500 | 430ms | 12 |
| Stress test max | 800 | 490ms | 18 |

### Scaling Rules of Thumb

- **1 API pod** handles ~40–50 RPS sustainably at < 200ms p95
- **1 Celery worker** processes ~20 Telegram notifications/min
- **PostgreSQL** max_connections = 200; each pod uses ~10 connections (pool_size=10)
- **Redis** max memory = 256Mi; each cached response ≈ 2–10KB

### When to Add More Nodes

Add a worker node when:
1. HPA is maxed out (20 pods) but CPU is still > 80%
2. Pod scheduling is failing due to insufficient node resources
3. `kubectl top nodes` shows any node > 85% CPU or memory

```bash
# Check node resource utilisation
kubectl top nodes
kubectl describe nodes | grep -A 5 "Allocated resources:"
```

---

## Traffic Management

### Rate Limiting Adjustment

```bash
# Update rate limits (requires restart of API pods)
kubectl set env deployment/prod-queue-api \
  RATE_LIMIT_TICKETS=20/minute \
  RATE_LIMIT_DEFAULT=120/minute \
  -n queue-management-prod
```

### Ingress Traffic Shaping

```bash
# Temporarily limit ingress traffic (e.g., during maintenance)
kubectl annotate ingress queue-api-ingress \
  nginx.ingress.kubernetes.io/limit-connections="50" \
  nginx.ingress.kubernetes.io/limit-rpm="3000" \
  --overwrite \
  -n queue-management-prod

# Remove limits after maintenance
kubectl annotate ingress queue-api-ingress \
  nginx.ingress.kubernetes.io/limit-connections- \
  nginx.ingress.kubernetes.io/limit-rpm- \
  -n queue-management-prod
```

### Maintenance Mode

```bash
# Enable maintenance mode (returns 503 with maintenance page)
kubectl patch ingress queue-api-ingress -n queue-management-prod \
  --type='json' \
  -p='[{"op":"add","path":"/metadata/annotations/nginx.ingress.kubernetes.io~1default-backend","value":"maintenance-page"}]'

# Disable maintenance mode
kubectl patch ingress queue-api-ingress -n queue-management-prod \
  --type='json' \
  -p='[{"op":"remove","path":"/metadata/annotations/nginx.ingress.kubernetes.io~1default-backend"}]'
```
