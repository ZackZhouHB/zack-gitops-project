---
title: "Python: Boto3 for AWS"
date: 2024-05-16T03:19:36Z
slug: python-boto3-for-aws
categories: ["Python"]
aliases: ["/post/70/"]
legacy_id: 70
---
Boto3 is the Amazon Web Services (AWS) Software Development Kit (SDK) for Python. It enables developers to build software that uses Amazon services like EC2, S3, RDS, etc.

I will build a portable Python3.9 + Boto3 Docker environment to test some AWS automation tasks.

 **Build and run a docker with Python3.9 + Boto3**

As I do not want to install Python, Boto3, and AWScli on my local PC, creating a Docker image with all software ready as a portable env is the best way to start.

```bash
root@ubt-server:~# vim Dockerfile
# Build from python:3.9.19-alpine3.19
From python:3.9.19-alpine3.19
# install boto3 and awscli
RUN pip install --upgrade pip && \
    pip install --upgrade awscli && \
    pip install --upgrade boto3
# set work dir
WORKDIR /work
# run Python
CMD "python"
# build a docker image from the above Dockerfile
root@ubt-server:~# docker image build -t zack_aws_boto3 .
# ls docker images
root@ubt-server:~# docker image ls
REPOSITORY               TAG             IMAGE ID       CREATED         SIZE
zack_aws_boto3           v1              07a13f7801ed   1 days ago     998MB
zackpy                   latest          287ba6873741   4 days ago     48.2MB
zackz001/gitops-jekyll   latest          d92894f7be6d   6 days ago     70.9MB
postgres                 15.0            027eba2e8939   19 months ago  377MB

# run docker and mount local python work dir
root@ubt-server:~/pythonwork# docker run -ti -v ${PWD}:/work zack_aws_boto3:v1 bash
root@c04670a43564:/#
root@c04670a43564:/# cd work && ls

# configure aws in the container
root@c04670a43564:/work# aws configure
AWS Access Key ID [****************GFNW]:
AWS Secret Access Key [****************Db7O]:
Default region name [ap-southeast-2]:
Default output format [None]:

# validate aws cred by listing ec2 instance id
root@c04670a43564:/work# aws ec2 describe-instances --query "Reservations[*].Instances[*].InstanceId" --output json
[
    [
        "i-076226daa5aaf7cf2"
    ]
]
```

 **Manage AWS resource with Python Boto3 script**

Here we have Python and boto3 env ready; I will list some AWS tasks that I want to be achieved by Python scripts.

- List EC2 instance name, instanceID, and state

```python
root@ubt-server:~/pythonwork# vim app.py
# import boto3 library
import boto3

def list_ec2_instances():
    # Create a session using default AWS profile
    session = boto3.Session()
    # Create an EC2 client
    ec2_client = session.client('ec2')

    # Describe EC2 instances
    response = ec2_client.describe_instances()

    # Iterate over the instances
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            # Get the instance ID
            instance_id = instance['InstanceId']

            # Get the instance state
            instance_state = instance['State']['Name']

            # Get the instance Name tag if exists
            instance_name = 'No Name'
            if 'Tags' in instance:
                for tag in instance['Tags']:
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break

            # Print instance ID, Name, and State
            print(f"Instance ID: {instance_id}, Name: {instance_name}, State: {instance_state}")

if __name__ == "__main__":
    list_ec2_instances()

root@c04670a43564:/work# python app.py
Instance ID: i-076226daa5aaf7cf2, Name: zack-blog, State: stopped
```

- Filter EC2 instance without tag "owner"

```python
# create app-untagged.py
root@ubt-server:~/pythonwork# vim app-untagged.py
import boto3

def get_untagged_ec2_instances():
    ec2_client = boto3.client('ec2')
    response = ec2_client.describe_instances()

    untagged_instances = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            has_owner_tag = False
            if 'Tags' in instance:
                for tag in instance['Tags']:
                    if tag['Key'].lower() == 'owner':
                        has_owner_tag = True
                        break

            if not has_owner_tag:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                untagged_instances.append({'InstanceId': instance_id, 'State': instance_state})

    return untagged_instances

untagged_instances = get_untagged_ec2_instances()
print("Untagged Instances:", untagged_instances)

# run script to filter untagged "owner" ec2
root@c04670a43564:/work# python app-untagged.py
Untagged Instances: [{'InstanceId': 'i-076226daa5aaf7cf2', 'State': 'stopped'}]
```

- Create lambda function to list EBS volume snapshots older than 30 days and delete them

To achieve this we need:

1. Create lambda IAM role for lambda to manage EBS volume snapshot
2. Create below Python lambda function
3. Zip and upload zip function
4. Create CloudWatch Event to Trigger and run it every 30 days

```python
# create lambda function to delete snapshots older than 30 days
root@ubt-server:~/pythonwork# vim app-snapshot-older-30days.py
import boto3
from datetime import datetime, timezone, timedelta

def lambda_handler(event, context):
    ec2_client = boto3.client('ec2')

    # Get the current time
    now = datetime.now(timezone.utc)

    # Define the time threshold
    time_threshold = now - timedelta(days=30)

    # Describe snapshots
    snapshots = ec2_client.describe_snapshots(OwnerIds=['self'])['Snapshots']

    # Filter snapshots older than 30 days
    old_snapshots = [snap for snap in snapshots if snap['StartTime'] < time_threshold]

    # Delete old snapshots
    for snapshot in old_snapshots:
        snapshot_id = snapshot['SnapshotId']
        ec2_client.delete_snapshot(SnapshotId=snapshot_id)
        print(f"Deleted snapshot: {snapshot_id}")

    return {
        'statusCode': 200,
        'body': f"Deleted {len(old_snapshots)} snapshots."
    }

# zip Package for the Lambda Function
root@ubt-server:~/pythonwork# zip function.zip app-snapshot-older-30days.py
```

- Email me when a security group allows inbound SSH (port 22) from everywhere (0.0.0.0/0)

To achieve this, we need:

1. AWS CloudTrail enable
2. Create CloudWatch Event Rule to capture AWS CloudTrail logs for security group changes
3. Create below Lambda Function if inbound allows port 22 from everywhere are met
4. Allow CloudWatch Events to Invoke the Lambda Function
5. Add the Lambda Function as a Target for the CloudWatch Event Rule

 **Conclusion**

There are many ways to automate AWS tasks using Python Boto3 script. Together with Lambda and trigger, many resource tasks can be scheduled and managed in a scripted way.
