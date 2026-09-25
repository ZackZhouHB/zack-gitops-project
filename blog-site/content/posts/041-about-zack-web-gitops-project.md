---
title: "About Zack-web Gitops project!"
date: 2022-11-02T14:22:08Z
slug: about-zack-web-gitops-project
categories: ["General"]
aliases: ["/post/41/"]
legacy_id: 41
---
**Project Introduction**

This is my first web blog using Jekyll, as a practical way by following [Cloud Resume Challenge](https://cloudresumechallenge.dev/docs/the-challenge/aws/) to build my cloud and devops concept and technical skillsets. ~~

**The Design**

By design, I will create:

- a web blog [Zack's Blog](https://zackblog.work/): with content and details to introduce myself
- a github repo [zack-gitops-project](https://github.com/ZackZhouHB/zack-gitops-project): to source control all code that I build and run locally by "jekyll serve", validate site and pages, then push the source code to github.
- a Dockerfile to build jekyll code into a docker image running by nginx/alpine
- 3 folders with manifests for staging and prod webapp deploy:
  - <ins>/terraform</ins> for creating AWS VPC and EKS to host the website as the production environment;
  - <ins>/k8s-local-deploy</ins> for website image deployment to local K8S as testing;
  - <ins>/eks-deploy</ins> for prod deployment with ArgoCD application manifest
- a EC2 instance: as staging environment for AWS with Godaddy domain hosting test
- a EKS cluster: as PROD environment to validate ArgoCD sync for web deployment

**The Architecture**

[![image tooltip here](/images/aws-ar.png)](/images/aws-ar.png)

This is the design of the CICD pipeline in GitHub Action workflow to auto build docker images for this website every time I make a code change and commit to my git repo [zack-gitops-project](https://github.com/ZackZhouHB/zack-gitops-project) [Branch: editing]

[![image tooltip here](/images/cicd.png)](/images/cicd.png)

[Zack's Blog](https://zackblog.work/)

```python
def hello_world():
    print("Hello, world!")

hello_world()
```
