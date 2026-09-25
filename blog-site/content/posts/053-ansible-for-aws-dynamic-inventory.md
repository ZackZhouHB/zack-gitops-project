---
title: "Ansible for AWS Dynamic Inventory"
date: 2023-01-22T23:26:07Z
slug: ansible-for-aws-dynamic-inventory
categories: ["DevOps"]
aliases: ["/post/53/"]
legacy_id: 53
---
When using Ansible with AWS, maintaining the inventory file will be a hectic task as AWS has frequently changed IPs, autoscaling instances, and much more.

Here we will install and apply ansible plugin for AWS dynamic inventory which makes an API call to AWS to get the instance information in the run time. It gives the EC2 instance details dynamically to manage the AWS infrastructure.

It supports most of the public and private cloud platforms not limited to just AWS.

**The Dynamic Inventory Topology:**
[![image tooltip here](/images/ansible-inventory.png)](/images/ansible-inventory.png)

**Setup Ansible AWS Dynamic Inventory**

```bash
# Ensure python3 & pip3 installed in Ansible server
python3 --version
sudo apt-get install python3 -y
sudo apt-get install python3-pip -y

# Install the boto3 library for ansible boot core to make API calls to AWS to retrieve ec2 instance details
sudo pip3 install boto3

fix error
ERROR! The ec2 dynamic inventory plugin requires boto3 and botocore.

# Create an inventory directory under /opt and cd into the directory
sudo mkdir -p /opt/ansible/inventory
cd /opt/ansible/inventory
sudo vi aws_ec2.yaml

---
plugin: aws_ec2

aws_access_key: <xxx-AWS-ACCESS-KEY-HERE>
aws_secret_key: <xx-AWS-SECRET-KEY-HERE>

regions:
  - us-west-2

keyed_groups:
  - key: tags
    prefix: tag
  - prefix: instance_type
    key: instance_type
  - key: placement.region
    prefix: aws_region

# edit ansible config file to enable AWS plugin and set inventory as above yaml
sudo vi /etc/ansible/ansible.cfg

[inventory]
enable_plugins = aws_ec2

inventory      = /opt/ansible/inventory/aws_ec2.yaml
```

[![image tooltip here](/images/ec2-inventory.png)](/images/ec2-inventory.png)

**Test if Ansible is able to ping all the machines returned by the dynamic inventory**

```bash
ansible-inventory -i /opt/ansible/inventory/aws_ec2.yaml --list
ansible all -m ping
```

**Execute Ansible Commands With ec2 Dynamic Inventory**

```bash
ansible-inventory --graph
```

List all instances grouped under tags, zones, and regions with dynamic group names like:

- aws\_region\_ap\_southeast\_2
- instance\_type\_t2\_micro
- tag\_Name

[![image tooltip here](/images/list-aws-ec2.png)](/images/list-aws-ec2.png)
