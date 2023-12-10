---
layout: page
title: Github Repos
permalink: /about/
---

Listing some of my github repos while I was practising devops concepts and tools:

==================================================================

<b>[Gitops-Project]: </b>

This is a self learning project using Github Action with CICD workflow to publish this <b>"Zack's Tech Stack"</b> website onto AWS EKS

Tools:  Git, Github Action workflow CI, Docker, ArgoCD, Terroform, AWS EKS, Route53 DNS, Godaddy

Git repo URL: [zack-gitops-project](https://github.com/ZackZhouHB/zack-gitops-project)

==================================================================

<b>[K8S-Project]:</b>

This is a k8s learning project to deploy 3 demo applications onto both local lab k8s cluster and AWS EKS

- Vprofile JAVA stack

- Fleetman position tracker (microservice application)

- AWS retail store sample app (microservice application) 

Tools:  k8s deployment, statefulset, AWS EBS, AWS EKS (Kops), rook-ceph

Git repo URL: [zz-k8s](https://github.com/ZackZhouHB/zz-k8s)

==================================================================

<b>[JAVA-Stack-DEVOPS-CICD-Project]:</b>

This is a full structural DEVOPS learning project follow by Udemy course to deploy a JAVA stack on:

"DevOps Beginners to Advanced with Projects - 2023"

https://www.udemy.com/course/decodingdevops/

- eipsode1: Local java stack deployment (tomcat webapp, nginx, rabbitmq, memcached, mysql) onto VMware Workstation VMs 

- eipsode2: Cloud migration Lift & Shift Java stack to AWS using EC2

- eipsode3: AWS re-factor Java stack by (AWS Beabstalk, RDS, AmazonMQ, Elasticache)

- eipsode3: containerization for Java stack by building docker images and test local run on docker compose and deploy to AWS ECR & ECS

- eipsode4: Deploy JAVA stack to AWS EKS (Kops)

- eipsode5: Jenkins(ec2) with CI pipeline (Nexus, SonarQube, Slack) build artifact(.war) and upload to Nexus, create CD pipeline upload artifact to AWS S3 and deploy to Beanstalk 

- eipsode6: Jenkins CI add docker build, upload image to ECR, create CD pipeline deploy to ECS.

- eipsode7: Jenkins CI + CD pipeline add helm deploy to AWS EKS

Git repo URL: [JAVA-Stack-CICD-DEVOPS](https://github.com/ZackZhouHB/redo20git)

==================================================================

<b>[Terraform-Project]:</b>

Terraform full practise project to deploy :

- Provision and deploy single web on AWS

- Use Terrafom VPC mudole

- Use provisioner "file" and "exec" function to upload ansible playbook deploy application on AWS

- Terraform create alb and asg

- Terraform create beanstalk staging and Prod with blue and green deployment

Git repo URL: [zackz-terraform](https://github.com/ZackZhouHB/zackz-terraform)


==================================================================

<b>[Ansible-Project]:</b>

Ansible practise project for :

- Playbook for AWS simple resrouce (EC2, VPC) provision

- JAVA stack provision using Ansible AWS module

- Playbook for mutiple FreeNas (FreeBSD) device upgrade

Git repo URL: [zzansible](https://github.com/ZackZhouHB/zzansible)

