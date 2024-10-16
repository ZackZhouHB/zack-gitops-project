---
layout: post
title:  " Lambda for AMI patching with Cloudformation "
date:   2024-04-04 11:15:29 +1100
categories: jekyll Cat2
---

<b> Rancher Golden AMI patching challange </b>

The team running rancher cluster in AWS EC2 facing compliance challange for the  golden AMI patching. The team want to automate the process of patching the golden AMI so they can  ensure the compliance of the rancher cluster. The team want to use Cloudformation to automate the process, to have the latest AMI ready every month. 

<b> Overview of workflow with Lambda and Cloudformation </b>

This CloudFormation template sets up an automated process for patching Amazon Machine Images (AMIs) on a monthly schedule using AWS services such as Lambda, EventBridge, SNS, and Parameter Store. Here's a workflow by design: 

- The Lambda function is triggered on the 1st of every month to automate the creation of a patched AMI for Rancher. It interacts with EC2 to create the AMI, update the SSM Parameter Store with the new AMI ID, and terminate any temporary EC2 instances used for the patching process

- The AMI ID of the latest patched image is stored in the AWS Systems Manager (SSM) Parameter Store (/ami/latest), ensuring that the latest AMI can be referenced easily in other systems.

- An SNS Topic is used to send email notifications, informing stakeholders about the status of the AMI patching process.

- The template sets up IAM roles and policies with least privilage for EC2 instances and the Lambda function, ensuring that the required actions can be performed securely within AWS.

<b> The Cloudformation Template</b>

Bellow resources will be created by this cnf template. 

- SSM Parameter Store:

- A Parameter (/ami/latest) is created to store the ID of the latest patched AMI. The initial AMI ID is set to ami-0375ab65ee943a2a6.
SNS Topic:

- An SNS Topic is created for sending notifications about the AMI patching process. It is configured to send notifications via email (hongbo.zhou@nesa.nsw.edu.au).
EC2 Instance Role and Profile:

- An IAM role (EC2InstanceRole) is created with permissions for various EC2 and SSM actions, including updating instance information, sending commands, and listing associations.
An instance profile (EC2InstanceProfile-for-AMI-Patching) is associated with this role, which allows EC2 instances to assume the role for patching purposes.
Lambda Execution Role:

- A Lambda execution role (LambdaExecutionRole) is created with permissions to manage EC2 instances (create, run, terminate), interact with SSM and SNS, and log activities to CloudWatch Logs. It also allows the Lambda function to pass the necessary roles (iam:PassRole).
Lambda Function:

- A Lambda function (Rancher-AMI-Patching-Function) is defined to handle the actual AMI patching process. The function code is stored in an S3 bucket (lab-lambda-rancher-golden-ami) as a zip file (lambda_function.zip).
The Lambda function uses Python 3.9, has a 15-minute timeout (max allowed), and is allocated 256 MB of memory. It reads the SNS topic ARN and AMI parameter name from environment variables.
EventBridge Rule:

- An EventBridge rule is created to trigger the Lambda function on the 1st of every month at midnight (UTC) using a cron expression (cron(0 0 1 * ? *)).
Lambda Invoke Permission:

- A Lambda permission is added to allow the EventBridge rule to invoke the Lambda function.

{% highlight shell %}
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
#        - Protocol: email
#          Endpoint: xxxxxx  # test email address2         

  # IAM Role for EC2 Instance
  EC2InstanceRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: ec2.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: SSMPolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - ssm:UpdateInstanceInformation
                  - ssm:ListAssociations
                  - ssm:ListInstanceAssociations
                  - ssm:ListCommandInvocations
                  - ssm:SendCommand
                  - ssm:GetCommandInvocation
                Resource: "*"

  # Instance Profile for the EC2 Role
# Instance Profile for the EC2 Role
  EC2InstanceProfile:
    Type: AWS::IAM::InstanceProfile
    Properties:
      Roles:
        - !Ref EC2InstanceRole
      InstanceProfileName: EC2InstanceProfile-for-AMI-Patching  # Set a specific name for clarity


  # Lambda Execution Role
  LambdaExecutionRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement:
          - Effect: Allow
            Principal:
              Service: lambda.amazonaws.com
            Action: sts:AssumeRole
      Policies:
        - PolicyName: LambdaAMIUpdatePolicy
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - Effect: Allow
                Action:
                  - ec2:CreateImage
                  - ec2:RunInstances
                  - ec2:TerminateInstances
                  - ec2:DescribeInstances
                  - ec2:DescribeInstanceStatus
                  - ssm:SendCommand
                  - ssm:GetCommandInvocation
                  - ssm:PutParameter
                  - ssm:GetParameter
                  - sns:Publish
                  - logs:CreateLogGroup          
                  - logs:CreateLogStream         
                  - logs:PutLogEvents           
                  - iam:PassRole  # Add this line
                Resource: "*"


  # Lambda Function
  AMIPatchingLambda:
    Type: AWS::Lambda::Function
    Properties:
      Description: 'Lambda Function to patch Rancher golden AMI'
      FunctionName: Rancher-AMI-Patching-Function
      Handler: lambda_function.lambda_handler
      Role: !GetAtt LambdaExecutionRole.Arn
      Code:
        S3Bucket: lab-lambda-rancher-golden-ami
        S3Key: lambda_function.zip  # Lambda zip file in S3
      Runtime: python3.9
      Timeout: 900  # 15 minutes (max for Lambda)
      MemorySize: 256
      Environment:
        Variables:
          SNS_TOPIC_ARN: !Ref SNSTopic
          AMI_PARAMETER_NAME: "/ami/latest"

  # EventBridge Rule to trigger Lambda every month
  AMIPatchingEventRule:
    Type: AWS::Events::Rule
    Properties:
      Description: 'event role to triger lambda function to patch rancher golden AMI monthly'
      ScheduleExpression: 'cron(0 0 1 * ? *)'  # Runs on the 1st of every month
      Targets:
        - Arn: !GetAtt AMIPatchingLambda.Arn
          Id: "AMIPatchingLambda"

  # EventBridge permissions for Lambda
  LambdaInvokePermission:
    Type: AWS::Lambda::Permission
    Properties:
      Action: lambda:InvokeFunction
      FunctionName: !GetAtt AMIPatchingLambda.Arn
      Principal: events.amazonaws.com
{% endhighlight %}

<b> The lambda function: </b>

This AWS Lambda function automates the process of patching an Amazon Machine Image (AMI) used for a Rancher cluster or similar workloads. It is designed to run on a schedule (e.g., triggered monthly by an EventBridge rule) and performs the following key tasks:

- Retrieve the Latest AMI ID:

The Lambda function starts by fetching the latest AMI ID from the AWS Systems Manager (SSM) Parameter Store. This ID is used to launch an EC2 instance for patching.

- Launch an EC2 Instance:

An EC2 instance is launched using the retrieved AMI. The instance type is set to t2.medium, and it is associated with an IAM instance profile that grants necessary permissions for patching and AMI creation.

- Wait for Instance Readiness:

The function waits for the EC2 instance to be fully initialized and ready to receive commands using SSM (AWS Systems Manager).

- Apply Patches via SSM:

The function sends a command to the EC2 instance via SSM to run system updates and apply patches. Specifically, it runs sudo apt-get update and sudo apt-get upgrade -y on the instance.

- Create a New Patched AMI:

After the patching process is complete, the function creates a new AMI from the patched instance. The new AMI is given a name that includes the current date and time for identification.

- Update the AMI ID in Parameter Store:

Once the new AMI is created, its ID is stored back into the SSM Parameter Store, replacing the previous AMI ID. This ensures that the latest AMI can be tracked and used for future patching or deployments.

- Send Notifications:

A notification is sent via SNS (Simple Notification Service) to inform the relevant team members about the successful creation of the new AMI. The notification includes the new AMI ID and a message advising the team to test the AMI before rolling it out to production.

- Terminate the EC2 Instance:

After the AMI is created, the EC2 instance used for patching is terminated to avoid unnecessary costs.

- Error Handling:

If any error occurs during the process, it is logged, and the EC2 instance is terminated regardless of success or failure, ensuring proper cleanup.

{% highlight shell %}
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

    instance_id = instance['Instances'][0]['InstanceId']
    logger.info(f"Launched EC2 instance: {instance_id}")
    
    try:
        # Wait for the instance to be in a valid state for SSM commands
        ec2.get_waiter('instance_status_ok').wait(InstanceIds=[instance_id])
        logger.info(f"Instance {instance_id} is now ready for SSM commands")

        # Run SSM Command to apply patches
        command = ssm.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'commands': ['sudo apt-get update', 'sudo apt-get upgrade -y']}
        )

        command_id = command['Command']['CommandId']
        logger.info(f"SSM command {command_id} sent for patching")
        
        # Wait for the command to finish
        time.sleep(120)  # You can improve this by checking status
        
        # Create a new AMI from the instance with a unique name
        current_time = datetime.now().strftime('%Y%m%d-%H%M%S')
        new_ami_name = f"Patched-AMI-{current_time}"
        
        new_ami = ec2.create_image(
            InstanceId=instance_id,
            Name=new_ami_name,
            NoReboot=True
        )
        new_ami_id = new_ami['ImageId']
        logger.info(f"New AMI created: {new_ami_id}")
        
        # Update the new AMI ID in Parameter Store
        parameter_store.put_parameter(
            Name=parameter_name,
            Value=new_ami_id,
            Type='String',
            Overwrite=True
        )
        logger.info(f"Updated Parameter Store with new AMI ID: {new_ami_id}")

        # Send SNS notification with the new AMI ID
        current_date = datetime.now().strftime('%Y-%m-%d')
        current_month = datetime.now().strftime('%B')
        
        sns_topic_arn = os.environ['SNS_TOPIC_ARN']
        sns.publish(
            TopicArn=sns_topic_arn,
            Message=f"Dear team, This is a notification for the newly patched AMI on {current_date}. Please use this AMI: {new_ami_id} to test. If the AMI works well, proceed to rollout to production. Contact us if there are any issues.",
            Subject=f"New AMI Created After Monthly Patching on {current_month}"
        )
        logger.info(f"Sent SNS notification for new AMI: {new_ami_id}")
    
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
    
    finally:
        # Terminate the EC2 instance regardless of success or failure
        ec2.terminate_instances(InstanceIds=[instance_id])
        logger.info(f"Terminated EC2 instance: {instance_id}")

    return {
        'statusCode': 200,
        'body': f"New AMI created: {new_ami_id}"
    }

{% endhighlight %}

![image tooltip here](/assets/cnf1.png)

<b> Conclusion</b>:

This setup ensures that the team's AMIs are always up to date with the latest patches, improving security and reliability for the applications or environments that use them.

- Automated AMI Patching: The function automates the entire process of launching an EC2 instance, applying patches, creating a new AMI, and updating the parameter store.

- Cost Optimization: By terminating the EC2 instance after the patching process, it ensures resources are only used when necessary.

- Ease of Management: The function updates the SSM Parameter Store with the latest AMI ID, which simplifies the tracking of the most recent patched AMI.

- Team Notification: Through SNS, it keeps the team informed about the newly patched AMI, streamlining communication for testing and production rollouts.
