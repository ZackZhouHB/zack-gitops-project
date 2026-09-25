---
title: "Ingress controller for Subdomain based Routing"
date: 2022-11-18T22:01:55Z
slug: ingress-controller-for-subdomain-based-routing
categories: ["Kubernetes"]
aliases: ["/post/44/"]
legacy_id: 44
---
In this post I will run the steps required to set up MetalLB for LoadBalancer IP allocation, the NGINX Ingress Controller for routing traffic based on subdomains, and how to configure local DNS to enable subdomain-based routing for Kubernetes services.

**Ingress-nginx install**

We will use Helm to install our ingress controller `ingress-nginx`, which will be used to route traffic based on subdomains.

```bash
# install  ingress controller ingress-nginx
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm -n ingress-nginx install ingress-nginx ingress-nginx/ingress-nginx --create-namespace

# check for ingressclasses
kubectl get ingressclasses.networking.k8s.io
NAME    CONTROLLER             PARAMETERS   AGE
nginx   k8s.io/ingress-nginx   <none>      149m
```

**MetalLB for loadbalancing**

Then we will set up MetalLB in local K8s cluster, to enable LoadBalancer service.

MetalLB works in two modes: Layer 2 (simpler for home labs) or BGP (more complex, used in production environments), here we will deploy MetalLB manifest and create MetalLB ConfigMap For a Layer 2 configuration, assign a range of IP addresses on local network that MetalLB will use for load balancers.

```yaml
# install metallb manifest
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.7/config/manifests/metallb-native.yaml

root@asb:~# kubectl get all -n metallb-system
NAME                                 READY   STATUS    RESTARTS   AGE
pod/controller-fbf54885d-skzkl       1/1     Running   0         174m
pod/speaker-49m7r                    1/1     Running   0         174m
pod/speaker-5zvfk                    1/1     Running   0         174m
pod/speaker-gdm26                    1/1     Running   0         174m

NAME                          TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/webhook-service       ClusterIP   10.101.12.65   <none>        443/TCP   174m

NAME                        DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR            AGE
daemonset.apps/speaker      3         3         3       3            3           kubernetes.io/os=linux   174m

NAME                                 READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/controller           1/1     1            1           174m

NAME                                         DESIRED   CURRENT   READY   AGE
replicaset.apps/controller-fbf54885d         1         1         1       174m

# Create a IP range for loadbalancer IP pool
vim metalab-pool.yaml
apiVersion: metallb.io/v1beta1
kind: IPAddressPool
metadata:
  name: my-ip-pool
  namespace: metallb-system
spec:
  addresses:
    - 11.0.1.240-11.0.1.252

# verify IP pool
kubectl describe ipaddresspool my-ip-pool -n metallb-system
kubectl get ipaddresspool -n metallb-system
NAME         AUTO ASSIGN   AVOID BUGGY IPS   ADDRESSES
my-ip-pool   true          false             ["11.0.1.240-11.0.1.252"]

# Loadbalancer auto assigned for Ingress Controller and joesite service with LoadBalancer
kubectl get svc -A | grep Load
ingress-nginx       ingress-nginx-controller                               LoadBalancer   10.106.123.55    11.0.1.242    80:32279/TCP,443:31291/TCP      157m
joesite-argo        joesite-service                                       LoadBalancer   10.111.85.29     11.0.1.240    80:30500/TCP                     23d
```

**Local DNS setup**

I want to replace all the NodePort services with a subdomain for simplicity, so I need to edit both local PC and kubeconfig VM's host file to point all subdomains to the Ingress Controller LoadBalancer IP (11.0.1.242)

```bash
vim /etc/hosts
11.0.1.242      pm.tina.place am.tina.place gf.tina.place lh.tina.place ag.tina.place
```

**Ingress rules for traffic control**

Now we can create a list of Ingress rules to route the K8S services to subdomains. As those services come with different namespaces, we need to split each Ingress rule for services in different namespaces, also need to pay attention to TLS setting for https requests to avoid too many redirects.

```yaml
vim monitoring-ingress.yaml

apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: monitoring-ingress
  namespace: monitoring
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
spec:
  ingressClassName: nginx
  rules:
  - host: gf.tina.place
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: prometheus-stack-grafana
            port:
              number: 80
  - host: am.tina.place
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: prometheus-stack-kube-prom-alertmanager
            port:
              number: 9093
  - host: pm.tina.place
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: prometheus-stack-kube-prom-prometheus
            port:
              number: 9090
```

```bash
kubectl apply -f monitoring-ingress.yaml
kubectl apply -f other-ingress.yaml
root@asb:~/path-based# kubectl get ingress -A
NAMESPACE         NAME                   CLASS   HOSTS                                 ADDRESS     PORTS     AGE
argocd            argocd-ingress         nginx   ag.tina.place                         11.0.1.242  80, 443
```
