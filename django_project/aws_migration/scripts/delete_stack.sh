#!/usr/bin/env bash
set -euo pipefail

PROFILE="default"
REGION="ap-southeast-2"
STACK_NAME="zackblog-migration-ec2"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile) PROFILE="$2"; shift 2 ;;
    --region) REGION="$2"; shift 2 ;;
    --stack-name) STACK_NAME="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: delete_stack.sh [--profile default] [--region ap-southeast-2] [--stack-name zackblog-migration-ec2]"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 1 ;;
  esac
done

aws cloudformation delete-stack \
  --profile "$PROFILE" \
  --region "$REGION" \
  --stack-name "$STACK_NAME"

echo "Delete requested for stack: $STACK_NAME"
echo "Track status:"
echo "aws cloudformation describe-stacks --profile $PROFILE --region $REGION --stack-name $STACK_NAME"
