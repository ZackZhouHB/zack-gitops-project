---
layout: post
title:  "Ingress-nginx Routing for local DNS"
date:   2023-11-06 11:15:29 +1100
categories: jekyll Cat2
---

Topic
Ingress-nginx Routing for local DNS (zz.local)

- helm install ingress controller ingress-nginx

{% highlight yaml %}
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm -n ingress-nginx install ingress-nginx ingress-nginx/ingress-nginx --create-namespace
{% endhighlight %}


- create localhost dns zz.local
- create ingress 
{% highlight yaml %}
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: nginx-ingress
spec:
  rules:
  - host: zz.local 
    http:
      paths:
      - path: /
        pathType: ImplementationSpecific
        backend:
          service:
            name: zackweb-service
            port:
              number: 80
{% endhighlight %}



This is the design of CICD pipeline in GitHub Action workflow to auto build docker images for this website every time I make code change and commit to my git repo  [zack-gitops-project](https://github.com/ZackZhouHB/zack-gitops-project)  [Branch : editing]

![image tooltip here](/assets/cicd.png)
