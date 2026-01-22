# AWS Multi-Account Health Analyzer

Monthly executive health reports for AWS account groups using a two-stage LLM pipeline (Haiku filtering → Opus analysis).

## Features

- **Multi-Account**: Analyze 2-10+ accounts per group with parallel data collection
- **Cost-Efficient**: Haiku filters raw data, Opus generates insights (~$0.41/run)
- **Executive Reports**: Concise ~2000 word reports for senior management
- **Flexible Groups**: Deploy separate stacks per team/project

## Architecture

```
EventBridge (Monthly 1st)
       ↓
Lambda (per group)
  ├── Parallel data collection (up to 4 accounts)
  │   ├── Cost Explorer (3 months + anomalies)
  │   ├── AWS Health API (maintenance, issues)
  │   └── Trusted Advisor (all 537 checks)
  ├── Stage 1: Haiku 4.5 filters to actionable items
  ├── Stage 2: Opus 4.5 generates executive report
  └── SNS Email with group-specific subject
```

## Quick Start

```bash
# 1. Configure account groups in app.py
account_groups = {
    "my-team": {
        "accounts": [
            {"id": "111111111111", "name": "dev"},
            {"id": "222222222222", "name": "prod"}
        ],
        "email": "team@company.com"
    }
}

# 2. Deploy IAM role to member accounts
aws cloudformation deploy \
  --template-file member-role.yaml \
  --stack-name HealthAnalyzerRole \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile <MEMBER_ACCOUNT>

# 3. Deploy CDK stacks
cdk deploy --all --profile <MAIN_ACCOUNT>
```

## Report Output

- **Subject**: `[group-name] AWS Health Report - YYYY-MM-DD`
- **Sections**: Executive Summary, Cost Analysis (per-account top 5), Platform Alerts, Security Findings, Top 5 Actions
- **Format**: Tables, prioritized by impact, includes dollar amounts

## Cost

| Accounts | Per Run | Monthly | Yearly |
|----------|---------|---------|--------|
| 2 | $0.41 | $0.41 | $5 |
| 4 | $0.55 | $0.55 | $7 |
| 6 | $0.70 | $0.70 | $8 |

## Models

| Stage | Model | Purpose |
|-------|-------|---------|
| Filter | Claude Haiku 4.5 | Extract actionable items from raw data |
| Analysis | Claude Opus 4.5 | Generate executive insights |

## Files

```
├── app.py                      # Account groups config
├── member-role.yaml            # IAM role for member accounts
├── serverless/
│   └── billing_analyzer_stack.py
└── lambda/
    └── billing_analyzer.py
```

## Adding Account Groups

1. Edit `account_groups` in `app.py`
2. Deploy `member-role.yaml` to new member accounts
3. Run `cdk deploy --all`

See [DESIGN.md](DESIGN.md) for detailed implementation notes.
