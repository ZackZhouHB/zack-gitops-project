# AWS Multi-Account Health Analyzer - Technical Solution

An intelligent multi-account AWS monitoring solution using a two-stage LLM pipeline for cost-effective executive reporting.

## 💡 The Problem

Cloud engineers managing multiple AWS accounts need:
- **Cost oversight**: Trends, anomalies, month-over-month comparison
- **Platform alerts**: Maintenance, outages, EOL notices
- **Security**: Vulnerabilities and misconfigurations
- **Performance**: Resource optimization, service limits

The challenge: More data = better insights, but also higher LLM costs. A single Claude Opus call with 6 accounts of raw data would be expensive.

## 🏗️ Architecture

```
EventBridge (Monthly 1st @ 9AM AEST)
       ↓
Lambda (per account group)
  ├── PARALLEL DATA COLLECTION (ThreadPoolExecutor, max 4)
  │   ├── Cost Explorer (3 months + anomalies)
  │   ├── AWS Health API (maintenance, issues, notifications)
  │   └── Trusted Advisor (all 537 checks per account)
  │
  ├── STAGE 1: Haiku 4.5 Filter
  │   └── Extract actionable items, per-account cost breakdown
  │
  ├── STAGE 2: Opus 4.5 Analysis
  │   └── Generate executive report (~2000 words)
  │
  └── SNS Email with [group-name] subject
```

## 🔑 Key Design Decisions

### Two-Stage LLM Pipeline

| Stage | Model | Purpose | Cost |
|-------|-------|---------|------|
| Filter | Haiku 4.5 | Extract actionable items from raw data | $0.001/1K input |
| Analysis | Opus 4.5 | Generate strategic insights | $0.015/1K input |

**Why?** Haiku handles bulk filtering cheaply. Opus focuses on high-value analysis of pre-filtered data.

### Account Groups

Instead of one Lambda for all accounts, deploy separate stacks per team/project:

```python
# app.py
account_groups = {
    "team-a": {
        "accounts": [
            {"id": "111111111111", "name": "dev"},
            {"id": "222222222222", "name": "prod"}
        ],
        "email": "team-a@example.com"
    },
    "team-b": {
        "accounts": [
            {"id": "333333333333", "name": "sandbox"},
            {"id": "444444444444", "name": "production"}
        ],
        "email": "team-b@example.com"
    }
}
```

**Benefits:**
- Teams receive only their relevant accounts
- Independent schedules per group
- Easy to add/remove groups

### Parallel Data Collection

```python
with ThreadPoolExecutor(max_workers=min(len(accounts), 4)) as executor:
    future_to_account = {executor.submit(collect_account_data, acc): acc for acc in accounts}
    for future in as_completed(future_to_account):
        all_accounts_data.append(future.result())
```

**Result:** 4 accounts in ~160s (same as 1 account), not 640s sequential.

### Cross-Account IAM

Lambda in main account assumes `HealthAnalyzerReadOnly` role in member accounts:

```yaml
# member-role.yaml (deploy to each member account)
AssumeRolePolicyDocument:
  Statement:
    - Effect: Allow
      Principal:
        AWS: !Sub "arn:aws:iam::111111111111:root"  # Main account
      Action: sts:AssumeRole
```

## 📊 Data Sources

### Cost Explorer
- Current month, previous month, two months ago (trend detection)
- Cost anomalies from last 90 days
- Per-service breakdown

### AWS Health API
- Scheduled maintenance events
- Ongoing service issues
- Account notifications (EOL, deprecations)

### Trusted Advisor
- All 537 checks (not just 9 like v1)
- Filters out "ok" status
- Includes flagged resource details and estimated savings

## 📧 Report Output

**Email Subject:** `[sandbox-lab] AWS Health Report - 2026-01-22`

**Sections:**
1. Executive Summary (30-second read)
2. Cost Analysis (per-account top 5 drivers)
3. Platform Alerts (table format)
4. Security Findings (severity summary)
5. Top 5 Recommended Actions (prioritized across all findings)

**Format:** Tables, ~2000 words, dollar amounts included

## 💰 Cost Analysis

### Per-Run Cost
| Component | Cost |
|-----------|------|
| Lambda (215s × 512MB) | ~$0.002 |
| Haiku 4.5 (Stage 1) | ~$0.06 |
| Opus 4.5 (Stage 2) | ~$0.35 |
| **Total** | **~$0.41** |

### Scaling
| Accounts | Per Run | Yearly (monthly runs) |
|----------|---------|----------------------|
| 2 | $0.41 | $5 |
| 4 | $0.55 | $7 |
| 6 | $0.70 | $8 |

## 🚀 Deployment

### Prerequisites
- AWS Business/Enterprise Support (for Trusted Advisor + Health API)
- Bedrock model access enabled (Haiku 4.5, Opus 4.5)

### Steps

```bash
# 1. Deploy IAM role to member accounts
aws cloudformation deploy \
  --template-file member-role.yaml \
  --stack-name HealthAnalyzerRole \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile <MEMBER_ACCOUNT>

# 2. Configure account groups in app.py

# 3. Deploy CDK stacks
cdk deploy --all --profile <MAIN_ACCOUNT>

# 4. Confirm SNS email subscription

# 5. Test manually
aws lambda invoke \
  --function-name HealthAnalyzer-<group>-HealthAnalyzer* \
  --invocation-type Event \
  --profile <MAIN_ACCOUNT> \
  --region ap-southeast-2 \
  /tmp/test.json
```

## 🐛 Issues & Solutions

### Marketplace Permissions for New Models
**Problem:** Haiku 4.5 failed with `AccessDeniedException` on first Lambda invoke.

**Solution:** Manually invoke model once via CLI to enable account-wide access:
```bash
aws bedrock-runtime invoke-model \
  --model-id au.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --body $(echo '{"anthropic_version":"bedrock-2023-05-31","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}' | base64 -w0) \
  --content-type application/json \
  --profile <YOUR_PROFILE> \
  --region ap-southeast-2 \
  /dev/stdout
```

### Trusted Advisor Timeout
**Problem:** Sequential API calls for 537 checks × N accounts caused timeouts.

**Solution:** Parallel data collection with ThreadPoolExecutor.

### Cost Drivers Combined Instead of Per-Account
**Problem:** Stage 1 prompt aggregated costs across all accounts.

**Solution:** Updated Stage 1 prompt to preserve per-account `top_5_services` structure.

## 📁 Files

```
aws-account-health-analyzer-v2/
├── app.py                      # Account groups config (edit this)
├── member-role.yaml            # IAM role for member accounts
├── DESIGN.md                   # Detailed design & progress tracking
├── serverless/
│   └── billing_analyzer_stack.py   # CDK stack (parameterized)
└── lambda/
    └── billing_analyzer.py     # Two-stage pipeline
```

## 🎯 Key Learnings

1. **Two-stage LLM pipelines** reduce costs while maintaining quality
2. **Parallel execution** is essential for multi-account scaling
3. **Account groups** provide flexibility for different teams
4. **Prompt engineering** matters - explicit structure prevents aggregation
5. **Cross-account IAM** with minimal permissions enables secure access

## 📚 Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [AWS Cost Explorer API](https://docs.aws.amazon.com/cost-management/latest/APIReference/)
- [AWS Health API](https://docs.aws.amazon.com/health/latest/APIReference/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)

---

**Built with AWS CDK, Lambda, Bedrock (Haiku 4.5 + Opus 4.5), and parallel processing**
