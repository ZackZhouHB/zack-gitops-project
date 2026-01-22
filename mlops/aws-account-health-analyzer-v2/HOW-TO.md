# AWS Multi-Account Health Analyzer - How-To Guide

A step-by-step guide for setting up, running, and maintaining this solution.

## Prerequisites

Before starting, ensure you have:

1. **AWS CLI** installed and configured with profiles
2. **Node.js** (for CDK) - `npm install -g aws-cdk`
3. **Python 3.12+** with pip
4. **AWS Business/Enterprise Support** on the main account (required for Trusted Advisor + Health API)
5. **Bedrock model access** enabled for Claude Haiku 4.5 and Opus 4.5

---

## Initial Setup (One-Time)

### Step 1: Clone and Setup Environment

```bash
cd mlops/aws-account-health-analyzer-v2
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# or: .venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### Step 2: Bootstrap CDK (if not done before)

```bash
cdk bootstrap aws://<ACCOUNT_ID>/<REGION> --profile <YOUR_PROFILE>
```

### Step 3: Enable Bedrock Models

First-time model access requires manual invocation. Run once per model:

```bash
# Enable Haiku 4.5
aws bedrock-runtime invoke-model \
  --model-id au.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --body $(echo '{"anthropic_version":"bedrock-2023-05-31","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}' | base64 -w0) \
  --content-type application/json \
  --profile <YOUR_PROFILE> \
  --region ap-southeast-2 \
  /dev/stdout

# Enable Opus 4.5
aws bedrock-runtime invoke-model \
  --model-id global.anthropic.claude-opus-4-5-20251101-v1:0 \
  --body $(echo '{"anthropic_version":"bedrock-2023-05-31","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}' | base64 -w0) \
  --content-type application/json \
  --profile <YOUR_PROFILE> \
  --region ap-southeast-2 \
  /dev/stdout
```

---

## Adding a New Account

### Step 1: Get Account ID

```bash
# If using SSO, check your AWS config
grep -A2 "profile <PROFILE_NAME>" ~/.aws/config | grep sso_account_id
```

### Step 2: Deploy IAM Role to Member Account

```bash
aws cloudformation deploy \
  --template-file member-role.yaml \
  --stack-name HealthAnalyzerRole \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides TrustedAccountId=<MAIN_ACCOUNT_ID> \
  --profile <MEMBER_ACCOUNT_PROFILE> \
  --region ap-southeast-2
```

### Step 3: Add to Account Group in app.py

Edit `app.py`:

```python
account_groups = {
    "my-team": {
        "accounts": [
            {"id": "111111111111", "name": "dev"},
            {"id": "222222222222", "name": "prod"},
            {"id": "333333333333", "name": "new-account"},  # Add here
        ],
        "email": "team@example.com"
    },
}
```

### Step 4: Deploy

```bash
cdk deploy --all --profile <YOUR_PROFILE>
```

---

## Adding a New Account Group

### Step 1: Deploy IAM Roles to All Member Accounts

Repeat for each account in the new group:

```bash
aws cloudformation deploy \
  --template-file member-role.yaml \
  --stack-name HealthAnalyzerRole \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides TrustedAccountId=<MAIN_ACCOUNT_ID> \
  --profile <ACCOUNT_PROFILE> \
  --region ap-southeast-2
```

### Step 2: Add Group to app.py

```python
account_groups = {
    # Existing groups...
    
    "new-project": {
        "accounts": [
            {"id": "111111111111", "name": "dev"},
            {"id": "222222222222", "name": "staging"},
            {"id": "333333333333", "name": "prod"},
        ],
        "email": "new-team@example.com"
    },
}
```

### Step 3: Deploy

```bash
cdk deploy --all --profile <YOUR_PROFILE>
```

### Step 4: Confirm Email Subscription

Check the email address and click the confirmation link from AWS SNS.

---

## Running Manually (Testing)

### Invoke a Single Group

```bash
# Async invoke (returns immediately, runs in background)
aws lambda invoke \
  --function-name HealthAnalyzer-<GROUP_NAME>-HealthAnalyzer* \
  --invocation-type Event \
  --profile <YOUR_PROFILE> \
  --region ap-southeast-2 \
  /tmp/test.json

# Check logs after ~4 minutes
aws logs filter-log-events \
  --log-group-name /aws/lambda/HealthAnalyzer-<GROUP_NAME>-HealthAnalyzer* \
  --filter-pattern "\"AWS Health Analyzer Complete\"" \
  --start-time $(date -d '10 minutes ago' +%s)000 \
  --profile <YOUR_PROFILE> \
  --region ap-southeast-2
```

### Find Lambda Function Names

```bash
aws lambda list-functions \
  --query "Functions[?starts_with(FunctionName, 'HealthAnalyzer')].FunctionName" \
  --profile <YOUR_PROFILE> \
  --region ap-southeast-2
```

---

## Monitoring & Troubleshooting

### Check Lambda Logs

```bash
# Recent errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/HealthAnalyzer-<GROUP>-HealthAnalyzer* \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --profile <YOUR_PROFILE> \
  --region ap-southeast-2

# Completion status
aws logs filter-log-events \
  --log-group-name /aws/lambda/HealthAnalyzer-<GROUP>-HealthAnalyzer* \
  --filter-pattern "\"Duration\"" \
  --start-time $(date -d '1 hour ago' +%s)000 \
  --profile <YOUR_PROFILE> \
  --region ap-southeast-2
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| `AccessDeniedException` on Bedrock | Model not enabled | Run manual invoke (see Step 3 in Initial Setup) |
| `AccessDenied` on member account | IAM role missing | Deploy `member-role.yaml` to that account |
| Lambda timeout | Too many accounts | Increase timeout in CDK stack or split into groups |
| No email received | SNS subscription not confirmed | Check email spam, re-subscribe |

### Check IAM Role in Member Account

```bash
aws iam get-role \
  --role-name HealthAnalyzerReadOnly \
  --profile <MEMBER_ACCOUNT_PROFILE>
```

---

## Removing an Account

### Step 1: Remove from app.py

Edit `app.py` and remove the account entry.

### Step 2: Deploy

```bash
cdk deploy --all --profile <YOUR_PROFILE>
```

### Step 3: (Optional) Delete IAM Role from Member Account

```bash
aws cloudformation delete-stack \
  --stack-name HealthAnalyzerRole \
  --profile <MEMBER_ACCOUNT_PROFILE> \
  --region ap-southeast-2
```

---

## Removing an Account Group

### Step 1: Remove from app.py

Delete the entire group entry from `account_groups`.

### Step 2: Destroy the Stack

```bash
# CDK destroy won't work if group removed from app.py
# Use CloudFormation directly
aws cloudformation delete-stack \
  --stack-name HealthAnalyzer-<GROUP_NAME> \
  --profile <YOUR_PROFILE> \
  --region ap-southeast-2
```

### Step 3: (Optional) Clean Up Member Account Roles

For each account that's no longer needed:

```bash
aws cloudformation delete-stack \
  --stack-name HealthAnalyzerRole \
  --profile <MEMBER_ACCOUNT_PROFILE> \
  --region ap-southeast-2
```

---

## Changing Email Recipient

### Step 1: Update app.py

```python
"my-team": {
    "accounts": [...],
    "email": "new-email@example.com"  # Change here
},
```

### Step 2: Deploy

```bash
cdk deploy --all --profile <YOUR_PROFILE>
```

### Step 3: Confirm New Subscription

Check the new email and click confirmation link.

---

## Changing Schedule

Edit `serverless/billing_analyzer_stack.py`:

```python
# Monthly on 1st at 9 AM AEST (23:00 UTC previous day)
schedule=events.Schedule.cron(minute="0", hour="23", day="1", month="*")

# Weekly on Monday at 9 AM AEST
schedule=events.Schedule.cron(minute="0", hour="23", week_day="SUN")

# Daily at 9 AM AEST
schedule=events.Schedule.cron(minute="0", hour="23")
```

Then deploy:

```bash
cdk deploy --all --profile <YOUR_PROFILE>
```

---

## File Reference

| File | Purpose | When to Edit |
|------|---------|--------------|
| `app.py` | Account groups config | Adding/removing accounts or groups |
| `member-role.yaml` | IAM role template | Never (unless changing permissions) |
| `serverless/billing_analyzer_stack.py` | CDK stack | Changing schedule, timeout, memory |
| `lambda/billing_analyzer.py` | Lambda code | Changing prompts, data sources |

---

## Quick Reference Commands

```bash
# Activate environment
cd mlops/aws-account-health-analyzer-v2
source .venv/bin/activate

# Deploy all stacks
cdk deploy --all --profile <YOUR_PROFILE>

# List stacks
cdk list --profile <YOUR_PROFILE>

# Invoke Lambda manually
aws lambda invoke --function-name <FUNCTION_NAME> --invocation-type Event --profile <YOUR_PROFILE> --region ap-southeast-2 /tmp/test.json

# Check completion
aws logs filter-log-events --log-group-name /aws/lambda/<FUNCTION_NAME> --filter-pattern "Complete" --start-time $(date -d '10 minutes ago' +%s)000 --profile <YOUR_PROFILE> --region ap-southeast-2
```

---

## Support

- **Design decisions**: See `DESIGN.md`
- **Technical details**: See `SOLUTION.md`
