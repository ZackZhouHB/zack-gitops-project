---
title: "Automate AMI patching with Lambda and Cloudformation"
date: 2024-02-01T03:14:05Z
slug: automate-ami-patching-with-lambda-and-cloudformation
categories: ["AWS"]
aliases: ["/post/67/"]
legacy_id: 67
---
The application team managing Rancher clusters in AWS EC2 faced a compliance challenge with their Rancher node template golden AMI. To meet security and compliance requirements, they needed to ensure that this AMI is patched regularly with the latest updates. This process had to be automated to guarantee that a newly patched AMI is available every month.

 **Overview of workflow with Lambda and Cloudformation**

I developed this CloudFormation template to set up an automated process for patching Amazon Machine Images (AMIs) on a monthly schedule using AWS services such as Lambda, EventBridge, SNS, and Parameter Store. Here's a workflow by design:

- The Lambda function is triggered on the 1st of every month to automate the creation of a patched AMI for Rancher. It interacts with EC2 to create the AMI, update the SSM Parameter Store with the new AMI ID, and terminate any temporary EC2 instances used for the patching process.
- The AMI ID of the latest patched image is stored in the AWS Systems Manager (SSM) Parameter Store (/ami/latest), ensuring that the latest AMI can be referenced easily in other systems.
- An SNS Topic is used to send email notifications, informing stakeholders about the status of the AMI patching process.
- The template sets up IAM roles and policies with least privilege for EC2 instances and the Lambda function, ensuring that the required actions can be performed securely within AWS.

 **The Cloudformation Template**

Bellow resources will be created by this CloudFormation template:

- **SSM Parameter Store**: A Parameter (/ami/latest) is created to store the ID of the latest patched AMI. The initial AMI ID is set to Ubuntu 20.04 TLS (ami-03xxxxxxxxxa6).
- **SNS Topic**: A SNS Topic is created for sending notifications about the AMI patching process. It is configured to send notifications via email (zhbsoftboy1@gmail).
- **EC2 Instance Role and Profile**: An IAM role (EC2InstanceRole) is created with permissions for various EC2 and SSM actions, including updating instance information, sending commands, and listing associations. An instance profile (EC2InstanceProfile-for-AMI-Patching) is associated with this role, which allows EC2 instances to assume the role for patching purposes.
- **Lambda Execution Role**: A Lambda execution role (LambdaExecutionRole) is created with permissions to manage EC2 instances (create, run, terminate), interact with SSM and SNS, and log activities to CloudWatch Logs. It also allows the Lambda function to pass the necessary roles (iam:PassRole).
- **Lambda Function**: A Lambda function (Rancher-AMI-Patching-Function) is defined to handle the actual AMI patching process. The function code is stored in an S3 bucket as a zip file (lambda\_function.zip). The Lambda function uses Python 3.9, has a 15-minute timeout (max allowed), and is allocated 256 MB of memory. It reads the SNS topic ARN and AMI parameter name from environment variables.
- **EventBridge Rule**: An EventBridge rule is created to trigger the Lambda function on the 1st of every month at midnight (UTC) using a cron expression (cron(0 0 1 \* ? \*)).
- **Lambda Invoke Permission**: A Lambda permission is added to allow the EventBridge rule to invoke the Lambda function.

```bash
# cnf-ami-lab.yaml

AWSTemplateFormatVersion: '2010-09-09'
Description: >
  This template deploys a Lambda function for automating AMI patching,
  along with a Parameter Store to track the AMI IDs, and a monthly
  EventBridge rule to trigger the Lambda.

Resources:

  # Parameter Store to store AMI ID
  AMIIDParameter:
    Type: AWS::SSM::Parameter
    Properties:
      Name: /ami/latest
      Description: 'Stores the ID of the latest patched AMI'
      Type: String
      Value: ami-xxxxxxxxxxxxx  # initial AMI ID

  # SNS Topic for notifications
  SNSTopic:
    Type: AWS::SNS::Topic
    Properties:
      DisplayName: Rancher AMI Patching Notifications
      Subscription:
        - Protocol: email
          Endpoint: zhbsoftboy1@gmail  # test email address
```

 **The lambda function:**

This AWS Lambda function automates the process of patching an Amazon Machine Image (AMI) used for a Rancher cluster or similar workloads. It is designed to run on a schedule (e.g., triggered monthly by an EventBridge rule) and performs the following key tasks:

- **Retrieve the Latest AMI ID:** The Lambda function starts by fetching the latest AMI ID from the AWS Systems Manager (SSM) Parameter Store. This ID is used to launch an EC2 instance for patching.
- **Launch an EC2 Instance:** An EC2 instance is launched using the retrieved AMI. The instance type is set to t2.medium, and it is associated with an IAM instance profile that grants necessary permissions for patching and AMI creation.
- **Wait for Instance Readiness:** The function waits for the EC2 instance to be fully initialized and ready to receive commands using SSM (AWS Systems Manager).
- **Apply Patches via SSM:** The function sends a command to the EC2 instance via SSM to run system updates and apply patches. Specifically, it runs sudo apt-get update and sudo apt-get upgrade -y on the instance.
- **Create a New Patched AMI:** After the patching process is complete, the function creates a new AMI from the patched instance. The new AMI is given a name that includes the current date and time for identification.
- **Update the AMI ID in Parameter Store:** Once the new AMI is created, its ID is stored back into the SSM Parameter Store, replacing the previous AMI ID. This ensures that the latest AMI can be tracked and used for future patching or deployments.
- **Send Notifications:** A notification is sent via SNS (Simple Notification Service) to inform the relevant team members about the successful creation of the new AMI. The notification includes the new AMI ID and a message advising the team to test the AMI before rolling it out to production.
- **Terminate the EC2 Instance:** After the AMI is created, the EC2 instance used for patching is terminated to avoid unnecessary costs.
- **Error Handling:** If any error occurs during the process, it is logged, and the EC2 instance is terminated regardless of success or failure, ensuring proper cleanup.

```python
import boto3
import time
import os
import logging
from datetime import datetime

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

ec2 = boto3.client('ec2')
ssm = boto3.client('ssm')
sns = boto3.client('sns')
parameter_store = boto3.client('ssm')

def lambda_handler(event, context):
    logger.info("Lambda function started")

    # Retrieve last AMI ID from Parameter Store
    parameter_name = os.environ['AMI_PARAMETER_NAME']
    response = parameter_store.get_parameter(Name=parameter_name)
    old_ami_id = response['Parameter']['Value']

    logger.info(f"Using AMI ID: {old_ami_id} to launch the instance")

    instance = ec2.run_instances(
        ImageId=old_ami_id,
        InstanceType='t2.medium',
        MinCount=1,
        MaxCount=1,
        IamInstanceProfile={'Name': 'EC2InstanceProfile-for-AMI-Patching'}
    )
```

[![image tooltip here](/images/cnf1.png)](/images/cnf1.png)
 **Conclusion**

This setup ensures that the team's AMIs are always up to date with the latest patches, improving security and reliability for the applications or environments that use them.

- **Automated AMI Patching:** The function automates the entire process of launching an EC2 instance, applying patches, creating a new AMI, and updating the parameter store.
- **Cost Optimization:** By terminating the EC2 instance after the patching process, it ensures resources are only used when necessary.
- **Ease of Management:** The function updates the SSM Parameter Store with the latest AMI ID, which simplifies the tracking of the most recent patched AMI.
- **Team Notification:** Through SNS, it keeps the team informed about the newly patched AMI, streamlining communication for testing and production rollouts.
