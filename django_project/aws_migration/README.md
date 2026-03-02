# AWS Migration Infra (Reusable)

This folder contains reusable infrastructure assets to create a new EC2 origin host for the Django app in `ap-southeast-2`.

It is designed for your March 2026 migration to a new AWS free-tier account.

## What this creates

- 1 EC2 instance (Ubuntu)
- 1 security group with ingress rules matching current setup:
  - `22/tcp` from configurable CIDR
  - `80/tcp` from `0.0.0.0/0`
  - `443/tcp` from `0.0.0.0/0`
  - `8000/tcp` from `0.0.0.0/0`
- EC2 user-data bootstrap:
  - installs Docker and Git
  - enables Docker service
  - clones this repo to `/home/ubuntu/zack-gitops-project` (branch configurable)

## Files

- `cloudformation/ec2-django-origin.yaml`: CloudFormation template
- `scripts/deploy_stack.sh`: Deploy/update stack
- `scripts/delete_stack.sh`: Delete stack

## Prerequisites

- New AWS account created
- IAM user with permissions for EC2 + CloudFormation
- Local AWS profile configured (can still use `default`)
- Existing key pair created in target account/region
- VPC and subnet IDs selected (usually default VPC/subnet)

## Quick usage

```bash
cd django_project/aws_migration

./scripts/deploy_stack.sh \
  --profile default \
  --region ap-southeast-2 \
  --stack-name zackblog-migration-ec2 \
  --key-name <your-keypair-name> \
  --vpc-id <vpc-xxxxxxxx> \
  --subnet-id <subnet-xxxxxxxx> \
  --ssh-cidr <your-public-ip/32>
```

After deployment, get outputs:

```bash
aws cloudformation describe-stacks \
  --profile default \
  --region ap-southeast-2 \
  --stack-name zackblog-migration-ec2 \
  --query "Stacks[0].Outputs" \
  --output table
```

## Notes

- Template defaults to Ubuntu 24.04 LTS AMI via SSM public parameter.
- Template default instance type is `t3.micro` for current free-tier compatibility in this account.
- If needed, override with `--instance-type`.
- You can later tighten security group rules after cutover.
