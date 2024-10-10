---
layout: post
title:  "Ingress controller for Subdomain based Routing"
date:   2022-11-18 11:15:29 +1100
categories: jekyll Cat2
---


<b>Ingress-nginx Routing for local DNS (tina.place)</b>

In this post I will run the steps required to set up MetalLB for LoadBalancer IP allocation, the NGINX Ingress Controller for routing traffic based on subdomains, and how to configure local DNS to enable subdomain-based routing for Kubernetes services.

<b>Ingress-nginx install</b>

We will use Helm to install our ingress controller `ingress-nginx`, which will be used to route traffic based on subdomains.

{% highlight shell %}

# install  ingress controller ingress-nginx
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm -n ingress-nginx install ingress-nginx ingress-nginx/ingress-nginx --create-namespace

# check for ingressclasses
kubectl get ingressclasses.networking.k8s.io 
NAME    CONTROLLER             PARAMETERS   AGE
nginx   k8s.io/ingress-nginx   <none> 149m
{% endhighlight %}

<b>MetalLB for loadbalancing</b>

Then we will set up MetalLB in local K8s cluster, to enable LoadBalancer service.

MetalLB works in two modes: Layer 2 (simpler for home labs) or BGP (more complex, used in production environments), here we will deploy MetalLB manifest and create MetalLB ConfigMap For a Layer 2 configuration, assign a range of IP addresses on local network that MetalLB will use for load balancers.

{% highlight shell %}
# install metallb manifest
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.7/config/manifests/metallb-native.yaml

root@asb:~# kubectl get all -n metallb-system 
NAME                             READY   STATUS    RESTARTS   AGE
pod/controller-fbf54885d-skzkl   1/1     Running   0          174m
pod/speaker-49m7r                1/1     Running   0          174m
pod/speaker-5zvfk                1/1     Running   0          174m
pod/speaker-gdm26                1/1     Running   0          174m

NAME                      TYPE        CLUSTER-IP     EXTERNAL-IP   PORT(S)   AGE
service/webhook-service   ClusterIP   10.101.12.65   <none> 443/TCP   174m

NAME                     DESIRED   CURRENT   READY   UP-TO-DATE   AVAILABLE   NODE SELECTOR            AGE
daemonset.apps/speaker   3         3         3       3            3           kubernetes.io/os=linux   174m

NAME                         READY   UP-TO-DATE   AVAILABLE   AGE
deployment.apps/controller   1/1     1            1           174m

NAME                                   DESIRED   CURRENT   READY   AGE
replicaset.apps/controller-fbf54885d   1         1         1       174m

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
NAME         AUTO ASSIGN   AVOID BUGGY IPS   ADDRESSES
my-ip-pool   true          false             ["11.0.1.240-11.0.1.252"]

# Loadbalancer auto assigned for Ingress Controller and joesite service with LoadBalancer  
kubectl get svc -A | grep Load
ingress-nginx       ingress-nginx-controller                             LoadBalancer   10.106.123.55    11.0.1.242    80:32279/TCP,443:31291/TCP      157m
joesite-argo        joesite-service                                      LoadBalancer   10.111.85.29     11.0.1.240    80:30500/TCP                    23d
{% endhighlight %}

<b>Local DNS setup</b>

I want to replace all the NodePort services with a subdomain for simplicity, so I need to edit both local PC and kubeconfig VM's host file to point all subdomains to the Ingress Controller LoadBalancer IP (11.0.1.242)

{% highlight shell %}
vim /etc/hosts
11.0.1.242      pm.tina.place am.tina.place gf.tina.place lh.tina.place ag.tina.place
{% endhighlight %}

<b>Ingress rules for traffic control</b>

Now we can create a list of Ingress rules to route the K8S services to subdomains. As those services come with different namespaces, we need to split each Ingress rule for services in different namespaces, also need to pay attention to TLS setting for https requests to avoid too many redirects.

{% highlight yaml %}

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
{% endhighlight %}

{% highlight yaml %}
vim other-ingress.yaml

apiVersion: networking.k8s.io/v1

kind: Ingress
metadata:
 name: longhorn-ingress
 namespace: longhorn-system
 annotations:
 nginx.ingress.kubernetes.io/rewrite-target: /
spec:
 ingressClassName: nginx
 rules:
  - host: lh.tina.place
 http:
 paths:
      - path: /
 pathType: Prefix
 backend:
 service:
 name: longhorn-frontend
 port:
 number: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
 name: ui-ingress
 namespace: retail
 annotations:
 nginx.ingress.kubernetes.io/rewrite-target: /
spec:
 ingressClassName: nginx
 rules:
  - host: ui.tina.place
 http:
 paths:
      - path: /
 pathType: Prefix
 backend:
 service:
 name: ui
 port:
 number: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
 name: zackblog-ingress
 namespace: zackapp-argo
 annotations:
 nginx.ingress.kubernetes.io/rewrite-target: /
spec:
 ingressClassName: nginx
 rules:
  - host: z.tina.place
 http:
 paths:
      - path: /
 pathType: Prefix
 backend:
 service:
 name: zack-web-zackblog-helm
 port:
 number: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
 name: joesite-ingress
 namespace: joesite-argo
 annotations:
 nginx.ingress.kubernetes.io/rewrite-target: /
spec:
 ingressClassName: nginx
 rules:
  - host: j.tina.place
 http:
 paths:
      - path: /
 pathType: Prefix
 backend:
 service:
 name: joesite-service
 port:
 number: 80
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
 name: argocd-ingress
 namespace: argocd
 annotations:
 nginx.ingress.kubernetes.io/ssl-redirect: "true"  # Redirect HTTP to HTTPS
 nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"  # Ensure HTTPS for the backend
spec:
 ingressClassName: nginx
 rules:
  - host: ag.tina.place
 http:
 paths:
      - path: /
 pathType: Prefix
 backend:
 service:
 name: argocd-server
 port:
 number: 443  # Forward traffic to ArgoCD on HTTPS
 tls:
  - hosts:
    - ag.tina.place
 secretName: argocd-tls-secret  # Optional, if we need TLS configured
{% endhighlight %}

{% highlight shell %}
kubectl apply -f monitoring-ingress.yaml
kubectl apply -f other-ingress.yaml
root@asb:~/path-based# kubectl get ingress -A
NAMESPACE         NAME                 CLASS   HOSTS                                       ADDRESS      PORTS     AGE
argocd            argocd-ingress       nginx   ag.tina.place                               11.0.1.242   80, 443   85s
joesite-argo      joesite-ingress      nginx   j.tina.place                                11.0.1.242   80        85s
longhorn-system   longhorn-ingress     nginx   lh.tina.place                               11.0.1.242   80        85s
monitoring        monitoring-ingress   nginx   gf.tina.place,am.tina.place,pm.tina.place   11.0.1.242   80        8m48s
retail            ui-ingress           nginx   ui.tina.place                               11.0.1.242   80        85s
zackapp-argo      zackblog-ingress     nginx   z.tina.place                                11.0.1.242   80        85s
{% endhighlight %}

Validate from Browser to visit each subdomain for the ingress routed K8S services, those websites used to be very hard by input `NodePort` every time, see now the corresponding application running on the subdomain makes my access much easier.

`ArgoCD`:  https://ag.tina.place/

`Prometheus`:   http://pm.tina.place/

`Grafana`: http://gf.tina.place

`AlertManager`: http://am.tina.place

`LongHorn`:  http://lh.tina.place/

`Retail UI`:  http://ui.tina.place/

`ZackBlog`:   http://z.tina.place/

`Joe's Site`: http://j.tina.place/

![image tooltip here](/assets/subdomain1.png)

![image tooltip here](/assets/subdomain2.png)

![image tooltip here](/assets/subdomain3.png)

<b>Conclusion</b>

By using MetalLB and the NGINX Ingress Controller, we can achieve subdomain-based routing for K8s services. The key steps involve configuring MetalLB for IP allocation, deploying the Ingress controller, creating services with Ingress rules for routing, and setting up local DNS.


