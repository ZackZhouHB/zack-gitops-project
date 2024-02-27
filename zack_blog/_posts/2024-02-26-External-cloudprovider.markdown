---
layout: post
title:  " EC2 K8S Cluster with External Cloud Controller Manager "
date:   2024-02-26 11:15:29 +1100
categories: jekyll Cat2
---

<b>About AWS Cloud provider </b>

The AWS Cloud provider provides the interface between a self-built Kubernetes cluster and AWS service APIs. This project allows a Kubernetes cluster to provision, monitor and remove AWS resources necessary for operation of the cluster.


<b> Scenario and Challange</b>

In a Scenario when running K8S cluster on couples of EC2 instances instead of using AWS EKS, deploy k8s services by setup type = LoadBalancer, it will not create AWS loadbalancer compare in a EKS managed k8s cluster.


Here we need Kubernetes External Cloud Controller Manager, by configuring AWS Cloud Controller manager, it will create and update AWS loadbalancers (classic and NLB) while to expose k8s services externally and manage AWS service lifecycle accordingly.

<b> Steps</b>

There are a few steps need to be done, docs can be followed by bellow link:


https://github.com/kubernetes/cloud-provider-aws/blob/master/docs/getting_started.md



- Change EC2 hostname from ip to FQDN

To be able to communicate with AWS API, the k8s node should be changed to FQDN rather than default EC2 IP address

{% highlight shell %}

curl http://169.254.169.254/latest/meta-data/local-hostname
hostnamectl set-hostname

{% endhighlight %}

- Create and assign IAM roles to k8s nodes 

IAM role needed for EC2 running K8S nodes to have proper permission to interact with AWS APIs and create and maintain AWS service

{% highlight shell %}
# Roles for master and worker nodes can be found bellow link
https://github.com/kubernetes/cloud-provider-aws/blob/master/docs/prerequisites.md 

{% endhighlight %}


- Tag ec2 instances as owned

The K8S nodes need to be tagged as owned

{% highlight shell %}

tag kubernetes.io/cluster/your_cluster_id=owned


{% endhighlight %}

- AWS Cloud Controller manager need to be deployed into K8S, this will create a NetworkLoadbalancer in AWS

{% highlight shell %}

kubectl apply -k 'github.com/kubernetes/cloud-provider-aws/examples/existing-cluster/base/?ref=master

{% endhighlight %}

- Add the --cloud-provider=external to the kube-controller-manager config, kube apiserver config and kubelet's config

<b> Conclusion</b>

now when create a k8s deployment and service, it will automatically create AWS loadbalancer to route traffic from external into K8S internal pods



