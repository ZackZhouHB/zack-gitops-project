---
title: "Claude Code with Kubernetes MCP Server"
date: 2025-09-23T01:40:11Z
slug: claude-code-with-kubernetes-mcp-server
categories: ["Kubernetes"]
aliases: ["/post/152/"]
legacy_id: 152
---
In this post, I’ll demonstrate how to install and use the Kubernetes MCP server [GitHub repo](https://github.com/Flux159/mcp-server-kubernetes) with Claude Code , and then show how I migrated the previous [AWS serverless OpenWebUI + Bedrock solution](/posts/aws-bedrock-with-open-webui/) to run locally on Minikube. Finally, we’ll explore how to use this Kubernetes MCP server to inspect and troubleshoot the deployment.

**Installation & Usage**

Before getting started, make sure you have the following prerequisites installed:

- `kubectl` installed and available in your `PATH`
- A valid `kubeconfig` file with contexts configured
- Access to a Kubernetes cluster (e.g., Minikube, Rancher Desktop, GKE)
- Helm v3 installed and in your `PATH` (optional if you don’t plan to use Helm)

By default, the server loads `kubeconfig` from `~/.kube/config`.

**Adding the MCP Server to Claude Code**

Add the Kubernetes MCP server with the built-in command:

```text
claude mcp add kubernetes -- npx mcp-server-kubernetes
```

This will automatically configure the MCP server in the Claude Code settings.

[![[Image Placeholder 01: MCP Installation]](/images/k8smcp1.png)](/images/k8smcp1.png)

We can now test basic operations such as listing and creating resources using our connected Kubernetes cluster.

[![[Image Placeholder 03: Migration Steps]](/images/k8smcp2.png)](/images/k8smcp2.png)

**Migrating AWS Serverless OpenWebUI + Bedrock to Minikube**

Next, I converted my AWS-based deployment to run locally on Minikube. After migration, the Kubernetes MCP server provided an easy way to monitor and troubleshoot the setup.

```yaml
root@zack:/mnt/f/zack-gitops-project/mlops/terraform-fargate-bedrock-openwebui/k8s-manifests# tree
.
├── README.md
├── aws-credentials-secret.yaml
├── deploy.sh
├── openwebui-deployment.yaml
├── openwebui-service.yaml
├── persistent-volume-claim.yaml
└── validate-deployment.sh

1 directory, 7 files
root@zack:/mnt/f/zack-gitops-project/mlops/terraform-fargate-bedrock-openwebui/k8s-manifests# cat openwebui-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: openwebui-deployment
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: openwebui
  template:
    metadata:
      labels:
        app: openwebui
    spec:
      containers:
      - name: openwebui
        image: ghcr.io/open-webui/open-webui:main
        ports:
        - containerPort: 8080
        volumeMounts:
        - name: data-volume
          mountPath: /app/backend/data
        env:
        - name: DATA_DIR
          value: "/app/backend/data"
        - name: WEBUI_SECRET_KEY_FILE
          value: "/app/backend/data/.webui_secret_key"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"

      - name: bedrock-gateway
        image: zackz001/openwebui-bedrock-gateway:v1  # Update with my DockerHub image
        ports:
        - containerPort: 80
        envFrom:
        - secretRef:
            name: aws-credentials
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"

      volumes:
      - name: data-volume
        persistentVolumeClaim:
          claimName: openwebui-data
```

[![[Image Placeholder 04: Local Web Console Running]](/images/k8smcp3.png)](/images/k8smcp3.png)

Now the web console is running locally—migration achieved 🎉. A local deployed openwebui using AWS Bedrock `apac.anthropic.claude-sonnet-4-20250514-v1:0`  as model, connecting via AWS Bedrock Gateway via AWS credentials from K8S secret, persistent volume to store chat history using k8s pv, expose service to local potal access

[![[Image Placeholder 04: Local Web Console Running]](/images/k8smcp4.png)](/images/k8smcp4.png)

**Key Migration Mappings**

- AWS IAM Role → Kubernetes Secret (for credentials)
- AWS EFS → PersistentVolumeClaim (for data persistence)
- ECS Task → Kubernetes Pod (for container orchestration)
- ALB/ECS Service → Kubernetes Service (for network access)

**Architecture Comparison**

- Side-by-side Terraform vs Kubernetes diagrams
- Detailed component mapping table
- Preserved networking behavior (localhost communication)

**Migration Benefits**

- Development advantages: local, faster, offline-friendly
- Architecture preservation: same containers, ports, and communication
- Production readiness: clear cloud migration path with Kubernetes-native tooling

The full manifests are now available at [my GitHub repo](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/mlops/terraform-fargate-bedrock-openwebui/k8s-manifests).
