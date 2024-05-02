---
layout: post
title:  " Two options for AWS Serverless web hosting  "
date:   2024-04-30 11:15:29 +1100
categories: jekyll Cat2
---

<b> Time to move "zackweb" from existing docker and containerization on EC2 and K8S to AWS Serverless with S3 </b>

In this article, I will see how to host "zackweb" as a static web application using bellow AWS serverless options:

- S3 static webhosting

- AWS CDK + CloudFront 


<b> Prerequisite </b>

- Add one more step in existing Github Action workflow to copy the static web content to newly created S3 bucket

{% highlight shell %}

# edit github action workflow
aws s3 cp ~/zack-gitops-project/zack_blog/_site/* s3://zackweb-serverless/ --recursive

# validate content in s3 bucket
ubuntu@ip-172-31-26-78:~$ aws s3 ls s3://zackweb-serverless --summarize
                           PRE aboutme/
                           PRE assets/
                           PRE certificate/
                           PRE gitrepo/
                           PRE jekyll/
                           PRE pro/
                           PRE skillroadmap/
2024-04-30 14:55:05       4455 404.html
2024-04-30 14:55:05        504 Dockerfile
2024-04-30 14:55:06      80555 feed.xml
2024-04-30 14:55:06       7760 index.html
2024-04-30 14:55:06          0 nginx.conf

Total Objects: 5
   Total Size: 93274

{% endhighlight %}

<b> Option 1: S3 static webhosting </b>

Go AWS console, under S3 bucket "zackweb-serverless" properties, enable static website hosting, update the bucket website endpoint address to Godaddy DNS record.

![image tooltip here](/assets/serverless2.png)

<b> Option 2: using AWS CDK + CDN </b>

With AWS CDK and CDN, the "zackweb" can be straightforward distributed from an S3 bucket accessible to the public by using CloudFront.

![image tooltip here](/assets/serverless3.png)

the steps will be:

1. Enable AWS CDK on EC2 bastion host.

2. S3 bucker ready and copy static web content into it (done above with modification of existing github action workflow)

3. Establish a CloudFront distribution to host a static To-Do web application.

4. Deploy the AWS CDK solution to host the To-do application.

- install AWS CDK on bastion EC2 host

{% highlight shell %}

# AWS CDK requires nodejs newer version
ubuntu@ip-172-31-26-78:~$ sudo apt-get install nodejs -y
ubuntu@ip-172-31-26-78:~$ sudo npm cache clean -f
ubuntu@ip-172-31-26-78:~$ sudo npm install -g n
ubuntu@ip-172-31-26-78:~$ sudo n stable
ubuntu@ip-172-31-26-78:~$ nodejs --version
v12.22.9

# install aws-cdk cli
ubuntu@ip-172-31-26-78:~$ npm install -g aws-cdk
ubuntu@ip-172-31-26-78:~$ cdk --version
2.139.1 (build b88f959)

# check aws credential and bootstrap CDK
ubuntu@ip-172-31-26-78:~$ aws sts get-caller-identity
{
    "UserId": "AIDxxxxxxxxx7ZV",
    "Account": "8xxxxxx342",
    "Arn": "arn:aws:iam::8xxxxx342:user/zackcdk"
}

# bootstrap CDK
ubuntu@ip-172-31-26-78:~$ sudo cdk bootstrap aws://8xxxxxxx2/ap-southeast-2

# init app
ubuntu@ip-172-31-26-78:~$  mkdir cdk
ubuntu@ip-172-31-26-78:~$ cd cdk
ubuntu@ip-172-31-26-78:~/cdk# cdk init app --language=typescript
Initializing a new git repository...
Executing npm install...
✅ All done!

# create CDK code

ubuntu@ip-172-31-26-78:~/cdk/lib# vim cdk-stack.ts

import * as cdk from '@aws-cdk/core';
import * as cloudfront from '@aws-cdk/aws-cloudfront';
import * as origins from '@aws-cdk/aws-cloudfront-origins';

export class ZackWebStack extends cdk.Stack {
  constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // existing S3 bucket
    const existingBucketName = 'zackweb-serverless';

    // Create a CloudFront distribution
    const distribution = new cloudfront.Distribution(this, 'MyDistribution', {
      defaultBehavior: {
        origin: new origins.S3OriginFromBucketName(existingBucketName)
      },
      defaultRootObject: 'index.html' // default root object
    });

    // Output the CloudFront distribution domain name
    new cdk.CfnOutput(this, 'CloudFrontDomainName', {
      value: distribution.distributionDomainName
    });
  }
}

# install required module

ubuntu@ip-172-31-26-78:~/cdk/lib# npm install @aws-cdk/core
ubuntu@ip-172-31-26-78:~/cdk/lib# npm install @aws-cdk/aws-cloudfront
ubuntu@ip-172-31-26-78:~/cdk/lib# npm install @aws-cdk/aws-cloudfront-origins

# Deploy stack
ubuntu@ip-172-31-26-78:~/cdk/lib# cd ..
ubuntu@ip-172-31-26-78:~/cdk/# cdk deploy

{% endhighlight %}

- The "zackweb" is now hosted on the AWS with serverless deployment !

![image tooltip here](/assets/serverless4.png)

<b> Conclusion</b>

Now we move the blog onto AWS with serverless website hosting, using both S3 static webhosting and AWS CDK plus Cloudfront. 