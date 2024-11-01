---
layout: post
title:  " K8S with External Cloud Controller Manager "
date:   2023-05-26 11:15:29 +1100
categories: jekyll Cat2
---

<b> Scenario and Challange </b>

In last post I was able to automate and create a self-owned K8S cluster on AWS EC2 instances by using Ansible and Terraform.

In this Scenario when deploying k8s pods and services in this K8S cluster, it will not create AWS loadbalancer even mentioned type = LoadBalancer, but this can be eaily achieved when in a AWS managed EKS cluster.

By searching online, Kubernetes actually provides such solution called <b>“cloud-provider-aws”</b>, which provides interface between a self-owned AWS Kubernetes cluster and AWS APIs. This allows EC2 instances running Kubernetes node to be able to provision AWS NLB or ELB resources during service deployment by mentioning “LoadBalancer”..


<b></b>

To enable the Kubernetes External Cloud Controller Manager, a <b>AWS Cloud Controller manager</b> need to be deployed into cluster, by doing so, it will create and a AWS loadbalancers (NLB), then self-owned K8S cluster can expose services externally by creating ELB.

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



