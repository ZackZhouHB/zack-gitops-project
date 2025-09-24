# OpenWebUI + Bedrock Gateway: Terraform Fargate to Minikube Migration

This project demonstrates migrating from a cloud-native Terraform setup to a local Minikube environment, maintaining the same application architecture while adapting to Kubernetes-native resources.

## Migration Architecture Mapping

| AWS Fargate Component | Kubernetes Equivalent | Purpose |
|----------------------|----------------------|---------|
| **IAM Role** | **Kubernetes Secret** | AWS credentials for Bedrock access |
| **AWS EFS** | **PersistentVolumeClaim** | Data persistence across restarts |
| **ECS Task** | **Kubernetes Pod** | Container orchestration unit |
| **ALB/ECS Service** | **Kubernetes Service** | Network access and load balancing |

## Design Comparison

### Original Terraform Fargate
```
Internet → ALB (Port 80) → ECS Service → Fargate Tasks
                                        ├── OpenWebUI (Port 8080)
                                        └── Bedrock Gateway (Port 80)
                                        
IAM Task Role → Automatic AWS credentials
EFS Volume → Persistent data storage
```

### Migrated Kubernetes
```
Internet → Service (Port 80) → Pod
                               ├── OpenWebUI (Port 8080)
                               └── Bedrock Gateway (Port 80)
                               
Secret → Manual AWS credentials injection
PVC → Local persistent storage
```

## Key Migration Adaptations

### 1. Authentication: IAM Role → Kubernetes Secret
**Fargate (Automatic):**
```hcl
task_role_arn = aws_iam_role.ecs_task_role.arn
# Automatic credential injection via AWS IAM
```

**Kubernetes (Manual):**
```yaml
envFrom:
- secretRef:
    name: aws-credentials  # Manual credential management
```

### 2. Storage: EFS → PersistentVolumeClaim
**Fargate (Managed):**
```hcl
efs_volume_configuration {
  file_system_id = aws_efs_file_system.openwebui_data.id
}
```

**Kubernetes (Local):**
```yaml
persistentVolumeClaim:
  claimName: openwebui-data  # Local storage via minikube
```

### 3. Networking: ALB → Service
**Fargate (Cloud Load Balancer):**
```hcl
aws_lb.openwebui_alb → aws_lb_target_group → ECS Service
```

**Kubernetes (Service Discovery):**
```yaml
type: LoadBalancer  # Minikube service tunneling
```

### 4. Container Communication (Unchanged)
Both environments use **localhost** communication between containers:
- OpenWebUI → Bedrock Gateway: `http://localhost:80/api/v1`
- Same pod networking in Kubernetes = Same task networking in Fargate

## Deployment

### Prerequisites
- Minikube running
- AWS credentials (Access Key + Secret Key)
- DockerHub image: Update `openwebui-deployment.yaml`

### Steps
1. **Configure AWS credentials** in `aws-credentials-secret.yaml`
2. **Update container image** in `openwebui-deployment.yaml`
3. **Deploy:**
   ```bash
   ./deploy.sh
   ```
4. **Access:**
   ```bash
   minikube service openwebui-service --url
   ```

## Files Structure
```
k8s-manifests/
├── aws-credentials-secret.yaml    # AWS credentials (replaces IAM role)
├── persistent-volume-claim.yaml   # Local storage (replaces EFS)
├── openwebui-deployment.yaml      # Pod definition (replaces ECS task)
├── openwebui-service.yaml         # Network access (replaces ALB)
├── deploy.sh                      # Deployment script
└── validate-deployment.sh         # Health check script
```

## Benefits of This Migration

### Development Advantages
- **Local Development**: No AWS costs during development
- **Faster Iteration**: Immediate deployment without cloud provisioning
- **Offline Capability**: Work without internet connectivity
- **Resource Control**: Adjust CPU/memory limits easily

### Architecture Preservation
- **Same Container Images**: Identical application behavior
- **Same Port Configuration**: No application code changes
- **Same Inter-container Communication**: Localhost networking preserved
- **Same Data Persistence**: Volume mounts work identically

### Production Readiness
- **Cloud Migration Path**: Easy to deploy back to EKS/Fargate
- **Kubernetes Native**: Uses standard K8s resources
- **Scalability Ready**: Horizontal pod autoscaling available
- **Security Model**: Secret management follows K8s best practices

## Troubleshooting

### Common Issues
```bash
# Check deployment status
./validate-deployment.sh

# View container logs
kubectl logs -f deployment/openwebui-deployment -c openwebui
kubectl logs -f deployment/openwebui-deployment -c bedrock-gateway

# Debug networking
kubectl get svc,pods,pvc
```

This migration demonstrates how cloud-native applications can be effectively adapted to local Kubernetes environments while maintaining architectural integrity and operational behavior.
