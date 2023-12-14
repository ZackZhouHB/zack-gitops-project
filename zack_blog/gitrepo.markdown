---
layout: page
title: Github Repos
permalink: /gitrepo/
---

Lists of my github repos with devops concepts and tools used:

==================================================================

<b>[Gitops-Project]: </b>

Gitops project with Github Action workflow to create and practise CICD pipeline to build and deploy this <b>"Zack's Tech Stack"</b> website onto both AWS EC2 by docker and to AWS EKS managed nodegroup sync by ArgoCD, with route53 pubilsh zone to Godaddy DNS

Github action workflows: 

- <b>Zackweb image build CI pipeline</b> : 2 layer docker inamge build, tag, push to dockerhub

- <b>EC2 docker web depolyment</b> : ssh to EC2 instance, pull latest image and run

![image tooltip here](/assets/cicd.png)

- <b>Terraform-EKS-Argocd-pipeline</b> : Terraform create VPC & EKS (module), argocd install, web app deploy and sync

![image tooltip here](/assets/aws-ar.png)





<b>Tools</b>:  Git, Github Action workflow CI, Docker, ArgoCD, Terroform, AWS EKS, Route53 DNS, Godaddy

<b>Git repo URL</b>: [zack-gitops-project](https://github.com/ZackZhouHB/zack-gitops-project)

==================================================================

<b>[K8S-Project]:</b>

Self K8S project to deploy 3 demo applications onto both local lab k8s cluster and AWS EKS

- <b>Vprofile JAVA stack</b> (nginx, rabbitmq, memcached, mysql, JAVA tomcat)

- <b>Fleetman position tracker</b> (microservice application : api gateway, JAVA tomcat, mongoDB, rabbitmq)

- <b>Amazon retail store sample app</b> (microservice application : rabbitmq, mysql, redis, dynamodb) 

<b>Tools</b>:  k8s deployment, statefulset, AWS EBS, AWS EKS (Kops), rook-ceph

<b>Git repo URL</b>: [zz-k8s](https://github.com/ZackZhouHB/zz-k8s)

==================================================================

<b>[JAVA-Stack-DEVOPS-CICD-Project]:</b>

This is a full structural DEVOPS learning project follow by Udemy course to deploy a JAVA stack on:

"DevOps Beginners to Advanced with Projects - 2023"

https://www.udemy.com/course/decodingdevops/

- E1: Local java stack deployment (tomcat webapp, nginx, rabbitmq, memcached, mysql) onto VMware Workstation VMs 

- E2:  Cloud migration Lift & Shift Java stack to AWS using EC2

- E3:  AWS re-factor Java stack by (AWS Beabstalk, RDS, AmazonMQ, Elasticache)

- E3:  containerization for Java stack by building docker images and test local run on docker compose and deploy to AWS ECR & ECS

- E4:  Deploy JAVA stack to AWS EKS (Kops)

- E5:  Jenkins(ec2) with CI pipeline (Nexus, SonarQube, Slack) build artifact(.war) and upload to Nexus, create CD pipeline upload artifact to AWS S3 and deploy to Beanstalk 

- E6:  Jenkins CI add docker build, upload image to ECR, create CD pipeline deploy to ECS.

- E7:  Jenkins CI + CD pipeline add helm deploy to AWS EKS

<b>Tools</b>: VMware, AWS managed services (IAM, VPC, EC2, S3, Beabstalk, RDS, AmazonMQ, Elasticache, CodePipeline, ECR, ECS, EKS, KOPS), Docker, Jenkins, Github webhook, SonarQube, Nexus, Slack  

<b>Git repo URL</b>: [JAVA-Stack-CICD-DEVOPS](https://github.com/ZackZhouHB/redo20git)

==================================================================

<b>[Terraform-Project]:</b>

Terraform full practise project to deploy :

- Provision and deploy single web on AWS

- Use Terrafom VPC mudole

- Use provisioner "file" and "exec" function to upload ansible playbook deploy application on AWS

- Terraform create alb and asg

- Terraform create beanstalk staging and Prod with blue and green deployment

<b>Tools</b>: Terraform, AWS, Ansible 

<b>Git repo URL</b>: [zackz-terraform](https://github.com/ZackZhouHB/zackz-terraform)


==================================================================

<b>[Ansible-Project]:</b>

Ansible practise project for :

- Playbook for AWS simple resrouce (EC2, VPC) provision

- JAVA stack provision using Ansible AWS module

- Playbook for mutiple FreeNas (FreeBSD) device upgrade

<b>Tools</b>: Ansible roles and mudules, AWS 

<b>Git repo URL</b>: [zzansible](https://github.com/ZackZhouHB/zzansible)

