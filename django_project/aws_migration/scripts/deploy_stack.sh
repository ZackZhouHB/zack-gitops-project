#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  deploy_stack.sh --key-name NAME --vpc-id VPC --subnet-id SUBNET [options]

Required:
  --key-name         EC2 key pair name
  --vpc-id           VPC ID
  --subnet-id        Subnet ID

Optional:
  --profile          AWS CLI profile (default: default)
  --region           AWS region (default: ap-southeast-2)
  --stack-name       CloudFormation stack name (default: zackblog-migration-ec2)
  --project-name     Name tag for EC2 (default: zackblog)
  --instance-type    EC2 type (default: t3.micro)
  --ssh-cidr         SSH source CIDR (default: 0.0.0.0/0)
  --root-volume-size Root EBS size in GiB (default: 20)
  --repo-url         Git repository URL
  --repo-branch      Repository branch (default: editing)
EOF
}

PROFILE="default"
REGION="ap-southeast-2"
STACK_NAME="zackblog-migration-ec2"
PROJECT_NAME="zackblog"
INSTANCE_TYPE="t3.micro"
SSH_CIDR="0.0.0.0/0"
ROOT_VOLUME_SIZE="20"
REPO_URL="https://github.com/ZackZhouHB/zack-gitops-project.git"
REPO_BRANCH="editing"

KEY_NAME=""
VPC_ID=""
SUBNET_ID=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --stack-name) STACK_NAME="$2"; shift 2 ;;
    --project-name) PROJECT_NAME="$2"; shift 2 ;;
    --instance-type) INSTANCE_TYPE="$2"; shift 2 ;;
    --ssh-cidr) SSH_CIDR="$2"; shift 2 ;;
    --root-volume-size) ROOT_VOLUME_SIZE="$2"; shift 2 ;;
    --repo-url) REPO_URL="$2"; shift 2 ;;
    --repo-branch) REPO_BRANCH="$2"; shift 2 ;;
    --key-name) KEY_NAME="$2"; shift 2 ;;
    --vpc-id) VPC_ID="$2"; shift 2 ;;
    --subnet-id) SUBNET_ID="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage; exit 1 ;;
  esac
done

if [[ -z "$KEY_NAME" || -z "$VPC_ID" || -z "$SUBNET_ID" ]]; then
  echo "Missing required args." >&2
  usage
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="${SCRIPT_DIR}/../cloudformation/ec2-django-origin.yaml"

aws cloudformation deploy \
  --profile "$PROFILE" \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --template-file "$TEMPLATE_FILE" \
  --parameter-overrides \
    ProjectName="$PROJECT_NAME" \
    KeyName="$KEY_NAME" \
    InstanceType="$INSTANCE_TYPE" \
    VpcId="$VPC_ID" \
    SubnetId="$SUBNET_ID" \
    SshCidr="$SSH_CIDR" \
    RootVolumeSize="$ROOT_VOLUME_SIZE" \
    RepoUrl="$REPO_URL" \
    RepoBranch="$REPO_BRANCH"

echo
echo "Stack deployed: $STACK_NAME"
aws cloudformation describe-stacks \
  --profile "$PROFILE" \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs" \
  --output table
