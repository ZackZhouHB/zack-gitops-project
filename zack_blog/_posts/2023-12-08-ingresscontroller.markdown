---
layout: post
title:  "Ingress-nginx Routing for local DNS"
date:   2023-11-06 11:15:29 +1100
categories: jekyll Cat2
---

Topic

<b>Ingress-nginx Routing for local DNS (zz.local)</b>

- helm install ingress controller ingress-nginx

{% highlight shell %}
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm -n ingress-nginx install ingress-nginx ingress-nginx/ingress-nginx --create-namespace
{% endhighlight %}

- create ingress to route root path to "zz.local" for "zackweb-service" 

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

- Browser visit "zz.local"

![image tooltip here](/assets/web.png)

