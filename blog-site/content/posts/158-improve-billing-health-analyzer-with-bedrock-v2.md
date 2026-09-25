---
title: "Improve Billing & Health Analyzer with Bedrock v2"
date: 2026-01-21T04:50:08Z
slug: improve-billing-health-analyzer-with-bedrock-v2
categories: ["Machine Learning"]
aliases: ["/post/158/"]
legacy_id: 158
---
I constantly rely on AWS Billing and Cost Management and Trusted Advisor to monitor costs and security. However, manual billing reviews are time-consuming, and raw Cost Explorer data doesn't provide the full picture. What if an intelligent program could proactively call the Billing and Trusted Advisor APIs, retrieve the raw data, and pass it to an LLM for in-depth analysis of account health—then deliver actionable insights and AI-powered recommendations? That would save a significant amount of time and effort.

This post documents building a **multi-account** serverless billing and health analyzer powered by Amazon Bedrock — evolving from a single-account prototype to a production-ready solution that analyses multiple AWS accounts with a cost-optimised two-stage LLM pipeline.

**The Evolution: From v1 to v2**

The original v1 solution worked well for a single account, but faced challenges when scaling:

- **Limited data coverage:** Only 9 Trusted Advisor checks out of 537 available
- **Single account only:** No cross-account visibility
- **Expensive for rich data:** Sending all raw data to a powerful model is wasteful

The v2 solution addresses these with a **two-stage LLM pipeline** and **multi-account support**:

```bash
# v2 Architecture: Two-Stage LLM Pipeline

EventBridge (Monthly 1st @ 9AM)
       │
       ▼
Lambda (per account group)
  ├── PARALLEL DATA COLLECTION (up to 4 accounts simultaneously)
  │   ├── Cost Explorer (3 months + anomalies)
  │   ├── AWS Health API (maintenance, outages, deprecations)
  │   └── Trusted Advisor (ALL 537 checks per account)
  │
  ├── STAGE 1: Claude Haiku 4.5 (cheap & fast)
  │   └── Filter raw data → extract only actionable items
  │
  ├── STAGE 2: Claude Opus 4.5 (powerful)
  │   └── Generate executive report with prioritised recommendations
  │
  └── SNS Email with [group-name] subject

# Why Two Stages?
┌─────────────────────────────────────────────────────────────────┐
│ Raw Data (~200KB)  →  Haiku Filter  →  Filtered (~5KB)  →  Opus │
│                                                                 │
│ Cost: ~$0.80/run (single model)  vs  ~$0.40/run (two-stage)    │
└─────────────────────────────────────────────────────────────────┘

Haiku handles the "grunt work" of filtering noise.
Opus focuses on generating strategic insights from high-signal data.
```

**Key Improvements in v2**

- **Multi-Account Support:** Analyse 2-10+ accounts per group with parallel data collection via cross-account IAM roles
- **Full Trusted Advisor Coverage:** All 537 checks instead of just 9 — no blind spots
- **AWS Health API Integration:** Scheduled maintenance, ongoing issues, EOL/deprecation notices
- **Cost Anomaly Detection:** Automatic detection of unusual spending patterns
- **Account Groups:** Deploy separate stacks per team/project with independent schedules
- **Executive-Friendly Reports:** ~2000 words, tables, per-account cost breakdown, prioritised actions

```bash
# Account Groups Configuration (app.py)
account_groups = {
    "platform-team": {
        "accounts": [
            {"id": "111111111111", "name": "dev"},
            {"id": "222222222222", "name": "staging"},
            {"id": "333333333333", "name": "prod"}
        ],
        "email": "platform-leads@example.com"
    },
    "data-team": {
        "accounts": [
            {"id": "444444444444", "name": "data-dev"},
            {"id": "555555555555", "name": "data-prod"}
        ],
        "email": "data-leads@example.com"
    }
}

# Each group gets its own Lambda, SNS topic, and monthly schedule
# Adding a new group = edit config + deploy IAM role to member accounts + cdk deploy
```

**Implementation Journey: Challenges & Solutions**

- **Bedrock Marketplace Permissions**
  New Bedrock models (Haiku 4.5, Opus 4.5) failed with `AccessDeniedException` on first Lambda invoke. **Solution:** Manually invoke each model once via CLI to enable account-wide access — Lambda role cannot be the "first invoker" for Marketplace models.
- **Trusted Advisor Timeout with Multiple Accounts**
  Sequential API calls for 537 checks × N accounts caused Lambda timeouts. **Solution:** Implemented parallel data collection using `ThreadPoolExecutor` with max 4 workers — 4 accounts now complete in ~160s (same as 1 account).
- **Cost Drivers Combined Instead of Per-Account**
  Stage 1 prompt was aggregating costs across all accounts. **Solution:** Updated prompt to explicitly preserve per-account `top_5_services` structure — now shows separate cost breakdown for each account.
- **Model Selection: Sonnet vs Opus**
  Tested both Claude Sonnet 4.5 and Opus 4.5 for Stage 2 analysis. **Decision:** Selected Opus for better formatting, effort estimates, and business impact statements — marginal cost increase (~$0.02/run) is negligible for monthly runs.

**Deployment with AWS CDK**

```bash
# 1. Deploy IAM role to each member account
$ aws cloudformation deploy \
  --template-file member-role.yaml \
  --stack-name HealthAnalyzerRole \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides TrustedAccountId=<MAIN_ACCOUNT_ID> \
  --profile <MEMBER_ACCOUNT_PROFILE>

# 2. Configure account groups in app.py

# 3. Deploy all stacks
$ cdk deploy --all --profile <YOUR_PROFILE>

# 4. Confirm SNS email subscription

# 5. Test manually
$ aws lambda invoke \
  --function-name HealthAnalyzer-<GROUP_NAME>-HealthAnalyzer* \
  --invocation-type Event \
  --profile <YOUR_PROFILE> \
  /tmp/test.json

# Check completion (~4 minutes later)
$ aws logs filter-log-events \
  --log-group-name /aws/lambda/HealthAnalyzer-<GROUP>-* \
  --filter-pattern "\"AWS Health Analyzer Complete\"" \
  --profile <YOUR_PROFILE>
```

**Sample Report Output**

The AI-powered report now covers multiple accounts with per-account breakdown:

```text
Subject: [platform-team] AWS Health Report - 2026-01-22

## Executive Summary
Brief overview of key findings across all 3 accounts...

## Cost Analysis
| Account | Current Month | Previous Month | Change |
|---------|---------------|----------------|--------|
| dev     | $1,234        | $1,100         | +12%   |
| staging | $567          | $590           | -4%    |
| prod    | $2,100        | $2,050         | +2%    |
| TOTAL   | $3,901        | $3,740         | +4%    |

### Top 5 Cost Drivers - dev
| Service | Cost | % of Total |
|---------|------|------------|
| EC2     | $500 | 40%        |
| S3      | $300 | 24%        |
...

### Top 5 Cost Drivers - staging
...

## Platform Alerts
| Priority | Service | Date   | Action Required          |
|----------|---------|--------|--------------------------|
| High     | RDS     | Feb 15 | MySQL 5.7 EOL migration  |
...

## Security Findings
| Severity | Count | Top Issue           |
|----------|-------|---------------------|
| Critical | 2     | Public S3 buckets   |
| High     | 5     | Open security groups|
...

## Top 5 Recommended Actions
| Priority | Action                  | Owner    | Timeline |
|----------|-------------------------|----------|----------|
| 1        | Fix public S3 buckets   | Security | 24 hours |
| 2        | Migrate RDS to MySQL 8  | DBA      | 2 weeks  |
...
```

**Cost Comparison**

| Metric | v1 (Single Account) | v2 (Multi-Account) |
| --- | --- | --- |
| Accounts | 1 | 2-10+ |
| Trusted Advisor Checks | 9 | 537 per account |
| AWS Health API | ❌ | ✅ |
| Cost Anomalies | ❌ | ✅ |
| LLM Pipeline | Single model | Two-stage (Haiku→Opus) |
| Cost per Run (2 accounts) | ~$0.50 | ~$0.41 |
| Annual Cost (monthly runs) | ~$6 | ~$5-10 |

**Lessons Learned**

- **Two-stage LLM pipelines** reduce costs while maintaining quality — use cheap models for filtering, expensive models for insights
- **Parallel execution** is essential for multi-account scaling — ThreadPoolExecutor makes 4 accounts as fast as 1
- **Account groups** provide flexibility — different teams get independent reports and schedules
- **Prompt engineering matters** — explicit structure in prompts prevents unwanted aggregation
- **Cross-account IAM** with least-privilege enables secure multi-account access

**Conclusion**

Building a multi-account health analyzer with Amazon Bedrock demonstrates how modern cloud engineers can leverage serverless + AI to create intelligent automation that scales. The two-stage LLM pipeline (Haiku for filtering, Opus for analysis) provides enterprise-grade insights at ~$0.40 per run — less than a cup of coffee for comprehensive health reports across multiple AWS accounts.

The complete implementation — including CDK stack definitions, Lambda code, member account IAM role template, and comprehensive documentation — is available at [my GitHub repository](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/mlops/aws-account-health-analyzer-v2). Special thanks to Amazon Q for assistance throughout this journey.
