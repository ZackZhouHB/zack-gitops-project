# AWS Account Health Analyzer v2 - Design Document

> **Purpose**: This document captures the design decisions, implementation approach, and progress tracking for the v2 solution.

## Background

### Original v1 Solution
Located at: `../aws-account-health-analyzer`

- Single AWS account analysis
- Limited data: 9 Trusted Advisor checks (out of 537), basic cost summary
- Single LLM model (Claude Sonnet 4) for all processing
- Works but doesn't scale cost-effectively for multi-account or richer data

### Why v2?
Cloud engineers managing multiple AWS accounts need:
1. **Cost oversight**: Summary, trends, anomalies, month-over-month comparison
2. **Platform alerts**: Planned maintenance, service outages, EOL/deprecation notices
3. **Security**: Security findings and vulnerabilities
4. **Performance**: Resource optimization, service limits

The challenge: Richer data = more input tokens = higher LLM costs. Need a smarter architecture.

---

## Environment

- **AWS Profile**: Your AWS CLI profile
- **Region**: `ap-southeast-2` (configurable)
- **Support Level**: Business/Enterprise (required for full Trusted Advisor + Health API access)
- **Bedrock Models**: Claude Haiku 4.5, Claude Opus 4.5

---

## Architecture

### Two-Stage LLM Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                 STAGE 1: Filter & Summarize                     │
│                 Model: Claude Haiku 4.5 (~cheap)                │
├─────────────────────────────────────────────────────────────────┤
│   Raw data from all sources (potentially large)                 │
│                      ↓                                          │
│   Haiku: "Extract only items requiring attention"               │
│                      ↓                                          │
│   Filtered data (small, high-signal)                            │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                 STAGE 2: Deep Analysis                          │
│                 Model: Claude Opus 4.5 (powerful)               │
├─────────────────────────────────────────────────────────────────┤
│   Pre-filtered data                                             │
│                      ↓                                          │
│   Opus: "Strategic analysis, prioritized recommendations"       │
│                      ↓                                          │
│   Executive Report → SNS Email                                  │
└─────────────────────────────────────────────────────────────────┘
```

#### Model Selection

| Stage | Model | Model ID | Input Cost | Output Cost |
|-------|-------|----------|------------|-------------|
| Stage 1 (Filter) | Claude Haiku 4.5 | `au.anthropic.claude-haiku-4-5-20251001-v1:0` | $0.001/1K | $0.005/1K |
| Stage 2 (Analysis) | Claude Opus 4.5 | `global.anthropic.claude-opus-4-5-20251101-v1:0` | $0.015/1K | $0.075/1K |

---

## Data Sources

### 1. Cost Explorer API
- Current month, previous month, two months ago (trend detection)
- Cost anomalies from last 90 days

### 2. AWS Health API
- Scheduled maintenance events
- Ongoing service issues
- Account notifications (EOL, deprecations)

### 3. Trusted Advisor API
- All 537 checks (not just 9 like v1)
- Filters out "ok" status
- Includes flagged resource details and estimated savings

---

## Implementation Phases

### Phase 1: Enrich Single Account Data ✅
- Expand Cost Explorer: add previous month, anomalies
- Add AWS Health API integration
- Expand Trusted Advisor: all categories
- Test with single powerful model (Opus)

### Phase 2: Add Tiered Model Processing ✅
- Add Haiku as Stage 1 filter
- Compare output quality vs Phase 1 baseline
- Measure cost savings

### Phase 3: Multi-Account Aggregation ✅
- Cross-account IAM role assumption
- Parallel data collection
- Account groups configuration
- Single email output per group

---

## Multi-Account Setup

### Member Account IAM Role

Deploy `member-role.yaml` to each member account:
```bash
aws cloudformation deploy \
  --template-file member-role.yaml \
  --stack-name HealthAnalyzerRole \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides TrustedAccountId=<MAIN_ACCOUNT_ID> \
  --profile <MEMBER_PROFILE>
```

### Lambda Environment Variables
- `LOCAL_ACCOUNT_ID`: Main account where Lambda runs
- `MEMBER_ACCOUNTS`: Comma-separated member account IDs
- `MEMBER_ROLE_NAME`: HealthAnalyzerReadOnly
- `GROUP_NAME`: Group identifier
- `ACCOUNT_NAMES`: JSON mapping of account IDs to names
- `STAGE1_MODEL_ID`: Haiku model for filtering
- `STAGE2_MODEL_ID`: Opus model for analysis

---

## Execution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: PARALLEL DATA COLLECTION                                │
│ ThreadPoolExecutor (max 4 workers)                              │
├─────────────────────────────────────────────────────────────────┤
│ All accounts in group run SIMULTANEOUSLY:                       │
│   Account 1 ─┐                                                  │
│   Account 2 ─┼── Cost Explorer + Health API + Trusted Advisor   │
│   Account 3 ─┤   (537 checks per account)                       │
│   Account 4 ─┘                                                  │
│                                                                 │
│ Time: ~160s (regardless of account count, up to 4)              │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: STAGE 1 - HAIKU FILTER                                  │
├─────────────────────────────────────────────────────────────────┤
│ Input: Combined raw data from all accounts                      │
│ Output: Filtered JSON with actionable items only                │
│ Time: ~20-30s                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: STAGE 2 - OPUS ANALYSIS                                 │
├─────────────────────────────────────────────────────────────────┤
│ Input: Filtered data from Stage 1                               │
│ Output: Executive report (markdown)                             │
│ Time: ~40-60s                                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: SNS EMAIL                                               │
├─────────────────────────────────────────────────────────────────┤
│ Subject: [group-name] AWS Health Report - YYYY-MM-DD            │
│ Single consolidated report for all accounts in group            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cost Analysis

### Per-Run Cost Estimate
| Component | Usage | Cost |
|-----------|-------|------|
| Lambda | 215s × 512MB | ~$0.002 |
| Haiku 4.5 (Stage 1) | ~35K tokens | ~$0.06 |
| Opus 4.5 (Stage 2) | ~8K tokens | ~$0.35 |
| **Total per run** | | **~$0.41** |

### Scaling Cost Projection
| Accounts | Est. Cost/Run | Yearly (monthly) |
|----------|---------------|------------------|
| 2 | $0.41 | $5 |
| 4 | $0.55 | $7 |
| 6 | $0.70 | $8 |

---

## Configuration

### Account Groups (app.py)
```python
account_groups = {
    "team-a": {
        "accounts": [
            {"id": "111111111111", "name": "dev"},
            {"id": "222222222222", "name": "prod"}
        ],
        "email": "team-a@example.com"
    },
}
```

### Adding New Account Groups
1. Add entry to `account_groups` in `app.py`
2. Deploy IAM role to new member accounts
3. Run `cdk deploy --all`

---

## Enhancements

### Account Names & Group Identification
- Each account has a friendly name alongside account ID
- Email subject includes group name: `[team-a] AWS Health Report - 2026-01-22`
- Report shows accounts as: `dev (111111111111), prod (222222222222)`

### Cost Analysis Per Account
- Top 5 cost drivers shown separately for each account
- Enables comparison of spending patterns across accounts

---

## Files Structure

```
aws-account-health-analyzer-v2/
├── README.md                    # User-facing documentation
├── DESIGN.md                    # This file - design & progress tracking
├── SOLUTION.md                  # Technical deep-dive
├── HOW-TO.md                    # Step-by-step operational guide
├── POC-Confluence.md            # POC proposal document
├── app.py                       # CDK app entry point (account groups config)
├── member-role.yaml             # CloudFormation template for member accounts
├── serverless/
│   └── billing_analyzer_stack.py   # CDK stack definition
└── lambda/
    └── billing_analyzer.py      # Lambda handler (two-stage pipeline)
```
