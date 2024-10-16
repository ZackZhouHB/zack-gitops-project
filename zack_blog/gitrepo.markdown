---
layout: page
title: Github Repos
permalink: /gitrepo/
---

Lists of my github repos with devops concepts and tools used:

==================================================================

<b>[Zack-blog-Gitops-Project]: </b>

Gitops project with Github Action workflow to create and practise CICD pipeline to build and deploy this <b>"Zack's Blog"</b> website onto both AWS EC2 by docker and to AWS EKS managed nodegroup sync by ArgoCD, with route53 public zone to Godaddy DNS

![image tooltip here](/assets/aws-ar.png)

Github action workflows: 

- <b>Zackweb image build CI pipeline</b> : 2 layer docker image build, tag, push to dockerhub

- <b>Stagging depolyment</b> : ssh to EC2 instance, pull latest image and docker run

- <b>Terraform-EKS-Argocd-pipeline for Prod</b> : Terraform create VPC & EKS (module), argocd install, web app deploy and sync

![image tooltip here](/assets/cicd.png)




<b>Tools</b>:  Git, Github Action workflow CI, Docker, ArgoCD, Terroform, AWS EKS, Route53 DNS, Godaddy

<b>Git repo URL</b>: [zack-gitops-project](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/zack_blog) 

==================================================================

<b>[MLOps-Project]:</b>

Self MLOps practice on both local and AWS to gain complete ML pipeline using MLOps tools, with hands-on experience for larger ML workflows. 

- <b>Lab setup</b> (CODA, Pytorch, PiP, Jupyter Notebook)

- <b>ML project</b> (DVC, MLflow, Docker, Apache Airflow, Jenkins)

- <b>AWS ML practice</b> (Amazon SageMaker, AWS S3, AWS CodePipeline, AWS Step Functions) 

<b>Tools</b>:  ML tools, AWS

<b>Git repo URL</b>: [mlops-project](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/mlops-project)

==================================================================


<b>[Jenkins-Project]:</b>

Jenkins project to deploy CICD pipeline to  build and deploy a zack blog app with Universal CI Pipeline with Ansible & Terraform and Multi-Destination Continuous Deployment with Terraform onto AWS EC2, ECS and EKS.


- <b>Universal CI Pipeline</b> (multi-language artifact build, Security Integration, advanced Jenkins pipeline structuring)

- <b>Multi-Destination CD Pipeline</b> (Multi-Destination on AWS, Advanced Terraform with Modularization, Integration with Trivy Ansible )

- <b>Amazon retail store sample app</b> (microservice application : rabbitmq, mysql, redis, dynamodb) 

<b>Tools</b>:  Jenkins, Terraform, AWS ec2 ECS EKS, Ansible, Docker, Kubenetes

<b>Git repo URL</b>: [Jenkins-CI](https://github.com/ZackZhouHB/zack-gitops-project/tree/jenkins/) and [Jenkins-CD](https://github.com/ZackZhouHB/zack-gitops-project/tree/jenkins-cd)

==================================================================


<b>[Terraform-Project]:</b>

Terraform full practise project to deploy :

- Provision and deploy single web on AWS

- Use Terrafom VPC mudole

- Provisioner "file" and "exec" to upload ansible playbook deploy application on AWS

- Terraform create ALB and ASG

- Terraform create beanstalk staging and Prod with blue and green deployment

<b>Tools</b>: Terraform, AWS, Ansible 

<b>Git repo URL</b>: [zackz-terraform](https://github.com/ZackZhouHB/zackz-terraform)


==================================================================

<b>[Ansible-Project]:</b>

Ansible practise project for :

- Playbook for AWS simple resrouce (EC2, VPC) provision

- JAVA stack provision using Ansible AWS module

- Playbook for mutiple FreeNas (FreeBSD) device upgrade

- Advanced with Ansible roles, modules, directives, valut, vars, handlers, templates  

<b>Tools</b>: Ansible, AWS 

<b>Git repo URL</b>: [zzansible](https://github.com/ZackZhouHB/zzansible)

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
