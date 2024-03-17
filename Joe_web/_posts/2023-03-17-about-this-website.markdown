---
layout: post
title:  "Welcome to my website !!"
date:   2024-3-17 19:15:29 +1100
categories: jekyll Cat2
---

<b>Project Introduction</b>

This is my first web blog using Jekyll, as an pratical way by following [Cloud Resume Challange](https://cloudresumechallenge.dev/docs/the-challenge/aws/) to build my cloud and devops concept and technical skillsets. 

<b>The Design</b>

By design, I will create:

- a web blog [Zack's Blog] [Zack's Blog] : with content and details to introduce myself 

- a github repo [zack-gitops-project](https://github.com/ZackZhouHB/zack-gitops-project): to source control all code that I build and run locally by "jekyll serve", validate site and pages, then push the source code to github.

- a Dockerfile to build jekyll code into a docker image running by nginx/alpine

- 3 folder with manifest for staging and prod webapp deploy: 

 <ins> /terrafom</ins>  for create AWS VPC and EKS to host website as production environment;
 
 <ins> /k8s-local-deploy</ins>  for website image deploy to local K8S as testing;
 
 <ins> /eks-deploy</ins>  for prod deployment with ArgoCD application manifest

- a EC2 instance: as staging env for AWS with Godaddy domain hosting test

- a EKS cluster:  as PROD environment to validate ArgoCD sync for web deployment 

<b>The Archetecture</b>




[Zack's Blog]: http://zackdevops.online