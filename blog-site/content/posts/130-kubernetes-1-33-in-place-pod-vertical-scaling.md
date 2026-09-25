---
title: "Kubernetes 1.33: In-Place Pod Vertical Scaling"
date: 2025-05-30T02:01:03Z
slug: kubernetes-1-33-in-place-pod-vertical-scaling
categories: ["Kubernetes"]
aliases: ["/post/130/"]
legacy_id: 130
---
**Discover Kubernetes 1.33's In-Place Vertical Scaling. Learn how to resize pod CPU and memory on the fly without restarts, eliminating downtime and optimizing resource costs.**

Previously, adjusting the CPU or memory for Kubernetes pods necessitated a disruptive full restart, causing downtime particularly detrimental for critical and stateful applications.

However, Kubernetes 1.33 introduces "**In-Place Pod Vertical Scaling**" ([K8s.io docs](https://kubernetes.io/docs/tasks/configure-pod-container/resize-container-resources/)) as a default beta feature, revolutionizing this by allowing on-the-fly CPU and memory adjustments to running pods without any restarts. This game-changing capability eliminates downtime for resource changes, enables better cost optimization by avoiding over-provisioning, and significantly benefits stateful workloads like databases by allowing them to scale without interruption.

[![[Image Placeholder 01: Introduction Graphic]](/images/k8s133-1.png)](/images/k8s133-1.png)

Real-World Use Cases:

- Databases (e.g., PostgreSQL): Give it more RAM for a heavy query without stopping transactions.
- Node.js API Services: Handle traffic spikes by giving them more CPU/memory on the fly.
- ML Inference Services (e.g., TensorFlow Serving): Allocate more resources for larger models or batch sizes without disrupting requests.
- Service Mesh Sidecars (e.g., Envoy): Dynamically adjust resources based on traffic without affecting the main application.

---

**What’s Really Happening**

When we submit a patch, the kubelet quickly checks if the node has enough allocatable capacity to handle the new request. If it does, the kubelet communicates with the container runtime (containerd or CRI-O) via the Container Runtime Interface (CRI) to adjust CPU and memory resources on the fly—no container restarts needed. This update process is asynchronous and non-blocking, with clear status updates available to keep us informed.

**Key Points:**

- Resources.requests and resources.limits are now mutable on the fly([KEP-1287](https://github.com/kubernetes/enhancements/issues/1287/)).
- Kubelet verifies node capacity before applying resource changes.
- Kubelet uses CRI to instruct container runtimes to adjust cgroups without restarting containers.
- The resizing process is asynchronous and non-blocking.
- New pod conditions in `kubectl describe pod`:
  - PodResizePending — node is busy, retry later.
  - PodResizeInProgress — resizing is underway.

---

**Hands-On:**

Ensuer to have a k8s cluster with version 1.33 in hand, here I am going to create a test pod, with initial requested CPU and Memory resource, then try to patch the CPU and memory to see if this feature will work without pod restart.

```yaml
root@133-m1:~# kubectl get node
NAME     STATUS   ROLES           AGE     VERSION
133-m1   Ready    control-plane   3m55s   v1.33.1
133-w1   Ready    worker          3m28s   v1.33.1

root@133-m1:~# vim test.yaml

apiVersion: v1
kind: Pod
metadata:
  name: resize-demo
spec:
  containers:
  - name: resource-watcher
    image: ubuntu:22.04
    command:
    - "/bin/bash"
    - "-c"
    - |
      apt-get update && apt-get install -y procps bc
      echo "=== Pod Started: $(date) ==="

      # Functions to read container resource limits
      get_cpu_limit() {
        if [ -f /sys/fs/cgroup/cpu.max ]; then
          # cgroup v2
          local cpu_data=$(cat /sys/fs/cgroup/cpu.max)
          local quota=$(echo $cpu_data | awk '{print $1}')
          local period=$(echo $cpu_data | awk '{print $2}')

          if [ "$quota" = "max" ]; then
            echo "unlimited"
          else
            echo "$(echo "scale=3; $quota / $period" | bc) cores"
          fi
        else
          # cgroup v1
          local quota=$(cat /sys/fs/cgroup/cpu/cpu.cfs_quota_us)
          local period=$(cat /sys/fs/cgroup/cpu/cpu.cfs_period_us)

          if [ "$quota" = "-1" ]; then
            echo "unlimited"
          else
            echo "$(echo "scale=3; $quota / $period" | bc) cores"
          fi
        fi
      }

      get_memory_limit() {
        if [ -f /sys/fs/cgroup/memory.max ]; then
          # cgroup v2
          local mem=$(cat /sys/fs/cgroup/memory.max)
          if [ "$mem" = "max" ]; then
            echo "unlimited"
          else
            echo "$((mem / 1048576)) MiB"
          fi
        else
          # cgroup v1
          local mem=$(cat /sys/fs/cgroup/memory/memory.limit_in_bytes)
          echo "$((mem / 1048576)) MiB"
        fi
      }

      # Print resource info every 5 seconds
      while true; do
        echo "---------- Resource Check: $(date) ----------"
        echo "CPU limit: $(get_cpu_limit)"
        echo "Memory limit: $(get_memory_limit)"
        echo "Available memory: $(free -h | grep Mem | awk '{print $7}')"
        sleep 5
      done
    resizePolicy:
    - resourceName: cpu
      restartPolicy: NotRequired
    - resourceName: memory
      restartPolicy: NotRequired
    resources:
      requests:
        memory: "128Mi"
        cpu: "100m"
      limits:
        memory: "128Mi"
        cpu: "100m"
```

Explore the Pod’s Initial State:

```bash
kubectl describe pod resize-demo | grep -A8 Limits:

root@133-m1:~# kubectl describe pod resize-demo | grep -A8 Limits:
    Limits:
      cpu:     100m
      memory:  128Mi
    Requests:
      cpu:        100m
      memory:     128Mi

kubectl logs resize-demo --tail=8

=== Pod Started: Sat May 31 01:48:50 UTC 2025 ===
---------- Resource Check: Sat May 31 01:48:50 UTC 2025 ----------
CPU limit: .100 cores
Memory limit: 128 MiB
Available memory: 2.8Gi
```

Resize CPU:

```bash
kubectl patch pod resize-demo --subresource resize --patch \
  '{"spec":{"containers":[{"name":"resource-watcher", \
"resources":{"requests":{"cpu":"200m"}, "limits":{"cpu":"200m"}}}]}}'

root@133-m1:~# kubectl describe pod resize-demo | grep -A8 Limits:
    Limits:
      cpu:     200m
      memory:  128Mi
    Requests:
      cpu:        200m
      memory:     128Mi

kubectl logs resize-demo --tail=8
---------- Resource Check: Sat May 31 01:49:16 UTC 2025 ----------
CPU limit: .200 cores
Memory limit: 128 MiB
Available memory: 2.8Gi
```

Resize Memory:

```bash
kubectl patch pod resize-demo --subresource resize --patch \
  '{"spec":{"containers":[{"name":"resource-watcher", "\
resources":{"requests":
{"memory":"256Mi"}, "limits":{"memory":"256Mi"}}}]}}'

root@133-m1:~# kubectl describe pod resize-demo | grep -A8 Limits:
    Limits:
      cpu:     200m
      memory:  256Mi
    Requests:
      cpu:        200m
      memory:     256Mi

root@133-m1:~# kubectl logs resize-demo --tail=8
---------- Resource Check: Sat May 31 01:50:16 UTC 2025 ----------
CPU limit: .200 cores
Memory limit: 256 MiB
Available memory: 2.8Gi
```

Verify No Container Restarts Occurred:

```bash
kubectl get pod resize-demo -o jsonpath='{.status.containerStatuses[0].restartCount}'
0
```

---

**Cloud Provider Support 🌩️**

Before rush to try this in production, let’s look at support across major Kubernetes providers:

- Google Kubernetes Engine (GKE): Available on the Rapid channel in GKE ([GKE docs](https://cloud.google.com/kubernetes-engine/docs/release-notes)).
- Amazon EKS: Kubernetes 1.33 version is available since May 2025.
- Azure AKS: Kubernetes 1.33 version is now available for Preview ([AKS Release Notes](https://learn.microsoft.com/en-us/azure/aks/release-notes)).

---

**Limits with Default K8S VPA**

Current Status (K8s 1.33): VPA does not yet support in-place resizing — it still recreates pods when adjusting resources. This limitation is explicitly noted in the Kubernetes documentation: “As of Kubernetes 1.33, VPA does not support resizing pods in-place, but this integration is being worked on.”

Active development is happening in [kubernetes/autoscaler PR 7673](https://github.com/kubernetes/autoscaler/pull/7673) to integrate VPA with in-place resizing capability.

[![[Image Placeholder 01: Introduction Graphic]](/images/k8s133-2.png)](/images/k8s133-2.png)

---

**The Future Integration We Need:**

Kubernetes 1.33’s in-place pod resize marks a major step toward making vertical scaling as smooth and non-disruptive as horizontal autoscaling, but there’s more to come. Future improvements include deeper Vertical Pod Autoscaler (VPA) integration to minimize pod evictions, expansion beyond CPU and memory to resources like GPUs and ephemeral storage, better scheduler awareness to prevent unexpected evictions, integration with the Cluster Autoscaler for smarter node scaling, and advanced metrics-based resizing using application-level signals. Together, these developments aim to make vertical scaling fully dynamic, efficient, and interruption-free—inviting users to experiment and help shape this evolving capability.
