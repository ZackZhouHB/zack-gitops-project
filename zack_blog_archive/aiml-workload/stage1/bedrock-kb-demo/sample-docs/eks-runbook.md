# EKS Cluster Operations Runbook

## Cluster Information

| Environment | Cluster Name | Region | Version |
|-------------|--------------|--------|---------|
| Production | eks-prod-01 | ap-southeast-2 | 1.28 |
| Staging | eks-stg-01 | ap-southeast-2 | 1.29 |
| Development | eks-dev-01 | ap-southeast-2 | 1.29 |

## Common Operations

### How to Access EKS Cluster

```bash
# Update kubeconfig
aws eks update-kubeconfig --name eks-prod-01 --region ap-southeast-2

# Verify access
kubectl get nodes
```

### How to Restart a Deployment

```bash
# Rolling restart (zero downtime)
kubectl rollout restart deployment/<deployment-name> -n <namespace>

# Check rollout status
kubectl rollout status deployment/<deployment-name> -n <namespace>
```

### How to Scale a Deployment

```bash
# Scale to specific replicas
kubectl scale deployment/<deployment-name> --replicas=5 -n <namespace>

# Check current replicas
kubectl get deployment <deployment-name> -n <namespace>
```

### How to Check Pod Logs

```bash
# Current logs
kubectl logs <pod-name> -n <namespace>

# Previous container logs (after crash)
kubectl logs <pod-name> -n <namespace> --previous

# Follow logs
kubectl logs -f <pod-name> -n <namespace>
```

## Troubleshooting

### Pods Stuck in Pending

**Check:**
1. Node resources: `kubectl describe nodes | grep -A 5 "Allocated resources"`
2. Pod events: `kubectl describe pod <pod-name> -n <namespace>`
3. Node selector/affinity matches available nodes
4. PVC bound if using persistent storage

**Resolution:**
- Scale node group if resource constrained
- Fix node selector if misconfigured
- Check PVC/StorageClass if storage issue

### Pods CrashLoopBackOff

**Check:**
1. Pod logs: `kubectl logs <pod-name> -n <namespace> --previous`
2. Container exit code: `kubectl describe pod <pod-name>`
3. Resource limits (OOMKilled = exit code 137)
4. Liveness probe configuration

**Resolution:**
- Fix application error from logs
- Increase memory limits if OOMKilled
- Adjust liveness probe timing

### Cannot Pull Image

**Check:**
1. Image exists in ECR: `aws ecr describe-images --repository-name <repo>`
2. Node IAM role has ECR permissions
3. Image tag is correct
4. ECR is in same region or cross-region pull configured

**Resolution:**
- Push image if missing
- Attach AmazonEC2ContainerRegistryReadOnly policy
- Fix image tag in deployment

## Monitoring

- Grafana Dashboard: https://grafana.internal.company.com/d/eks-overview
- CloudWatch Container Insights: AWS Console > CloudWatch > Container Insights
- Prometheus: https://prometheus.internal.company.com

## Contacts

- EKS Platform Team: eks-platform@company.com
- On-call: PagerDuty - "EKS Production"
