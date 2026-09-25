---
title: "GitOps with Argo CD"
date: 2022-11-07T21:46:56Z
slug: gitops-with-argo-cd
categories: ["DevOps"]
aliases: ["/post/42/"]
legacy_id: 42
---
Argo CD is a declarative, GitOps continuous delivery tool for Kubernetes applications. This is a post to show how to enable Argo CD on local k8s and AWS EKS, deploy applications and sync with GitHub manifests.

- Argo CD install ingress controller ingress-nginx

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
```

- Download and install Argo CD CLI

```bash
curl -sSL -o argocd-linux-amd64 https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
sudo install -m 555 argocd-linux-amd64 /usr/local/bin/argocd
rm argocd-linux-amd64
```

- Configure Argo CD API Server and deploy zackweb

Change the argocd-server service type to NodePort, initialize admin password, and deploy "zackweb" via Argo CD application manifests (argo-zackweb-application.yaml).

```bash
kubectl patch svc argocd-server -n argocd -p '{"spec": {"type": "NodePort"}}'
argocd admin initial-password -n argocd
kubectl create -f argo-zackweb-application.yaml
```

argo-zackweb-application.yaml

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: zackweb
  namespace: argocd
spec:
  destination:
    namespace: 'zackweb'
    server: 'https://kubernetes.default.svc'
  source:
    path: eks-deploy
    repoURL: 'https://github.com/ZackZhouHB/zack-gitops-project'
    targetRevision: editing
  project: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
    - CreateNamespace=true
```

- Access the Argo CD UI to check for sync

[![image tooltip here](/images/argo-demo.png)](/images/argo-demo.png)
