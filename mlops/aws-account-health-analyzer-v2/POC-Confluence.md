# POC - Multi-Account AWS Health Analyzer with AI

**Author:** Zack Zhou  
**Date:** January 2026  
**Status:** Proposed  
**Read time:** ~8 min

---

## Executive Summary

This Proof of Concept proposes an AI-powered AWS account health monitoring solution to replace the current manual, reactive approach to cloud governance. The solution uses Amazon Bedrock's generative AI capabilities to automatically collect, analyse, and report on cost trends, security findings, and platform alerts across multiple AWS accounts.

The objective is to validate technical feasibility, demonstrate value to stakeholders, and establish a foundation for organisation-wide cloud governance automation.

---

## 1. Background

### 1.1 Current State

Today, our AWS account monitoring relies heavily on manual processes and reactive responses:

- **Ad-hoc cost reviews** where engineers log into each AWS console individually to check billing
- **Reactive security responses** where issues are discovered after incidents rather than proactively
- **No consolidated view** across multiple AWS accounts managed by different teams
- **Trusted Advisor ignored** because reviewing 500+ checks manually per account is impractical
- **AWS Health notifications missed** as they arrive via email and get buried in inboxes

This approach introduces several risks:

- Cost anomalies go unnoticed until monthly bills arrive
- Security misconfigurations remain undetected for extended periods
- Scheduled AWS maintenance catches teams off-guard
- No executive visibility into overall cloud health posture
- Knowledge silos where only specific engineers understand specific accounts

### 1.2 Business Impact

The current manual approach:

- Makes it difficult to maintain **consistent governance** across AWS accounts
- Prevents timely identification of **cost optimisation opportunities**
- Creates **compliance gaps** when security findings are not addressed promptly
- Limits **executive visibility** into cloud operations health
- Increases **operational risk** as the number of AWS accounts grows

As our AWS footprint expands across more teams and projects, the numbers of AWS accounts reach 41 at the moment, this manual approach does not scale.

### 1.3 Why AI Integration?

Traditional monitoring tools generate alerts and dashboards, but still require humans to:
- Correlate findings across multiple data sources
- Prioritise what matters from hundreds of data points
- Write summaries that non-technical stakeholders can understand
- Recommend specific actions with business context

Generative AI (specifically Amazon Bedrock with Claude models) can:
- Process large volumes of raw AWS data (cost, security, health) in seconds
- Extract only actionable items from noise
- Generate executive-friendly reports with prioritised recommendations
- Provide consistent analysis quality regardless of who runs it
- Scale to any number of accounts without additional human effort

---

## 2. Scope

### 2.1 In Scope

This Proof of Concept includes:

**Data Collection**
- Cost data from AWS Cost Explorer (3 months history + anomaly detection)
- Security and optimisation findings from AWS Trusted Advisor (all 537 checks)
- Platform alerts from AWS Health API (maintenance, outages, deprecations)

**AI Processing**
- Two-stage LLM pipeline using Amazon Bedrock
- Stage 1: Fast, cheap model (Claude Haiku 4.5) to filter raw data
- Stage 2: Powerful model (Claude Opus 4.5) to generate insights

**Multi-Account Support**
- Cross-account data collection via IAM role assumption
- Flexible account grouping (by team, project, or environment)
- Parallel processing for Lambda execution and performance

**Reporting**
- Monthly automated email reports
- Executive-friendly format (~2000 words)
- Per-account cost breakdown with top 5 drivers each
- Prioritised action items with owner and timeline suggestions

### 2.2 Out of Scope

The following items are explicitly out of scope for this POC:

- Real-time alerting or dashboards, AWS native reporting tools (QuickSight)
- Automated remediation of findings
- Integration with ticketing systems (ServiceNow, Jira and MSP)
- Custom compliance frameworks beyond AWS Trusted Advisor
- Historical trend analysis beyond 3 months
- Cost allocation tags analysis

### 2.3 Key Assumptions

- All target accounts have **AWS Business or Enterprise Support** (required for Trusted Advisor and Health API access)
- Amazon Bedrock model access is enabled in the deployment region
- Email recipients will confirm SNS subscription
- Monthly reporting frequency is sufficient for initial rollout

---

## 3. Objectives & Success Criteria

### 3.1 POC Objectives

The objectives of this Proof of Concept are to validate that the proposed solution can:

1. Automatically collect cost, security, and health data from multiple AWS accounts
2. Use latest AWS Bedrock AI models to filter noise and extract actionable insights
3. Generate executive-readable reports without manual intervention
4. Operate at minimal cost (target: under $1 per monthly run)
5. Scale to all 41+ AWS accounts without architecture changes

### 3.2 Success Criteria

| Category | Success Metric |
|----------|----------------|
| Data Collection | Cost, Trusted Advisor, and Health data retrieved from all configured accounts |
| AI Processing | Two-stage pipeline completes within 5 minutes for up to 4 accounts |
| Report Quality | Report covers cost trends, security findings, platform alerts, and prioritised actions |
| Accuracy | Findings in report match manual console verification |
| Cost Efficiency | Total run cost under $0.50 for 2 accounts, under $1.00 for 6 accounts |
| Scalability | Adding new account requires only configuration change, no code modification |

---

## 4. POC Approach & Methodology

### 4.1 Approach

The POC will be delivered using an **incremental, staged approach**:

**Stage 1: Single Account, Single AWS Bedrock LLM**
- Build data collection for one account (Cost Explorer, Trusted Advisor, Health API)
- Use single powerful model (Claude Opus 4.5) for analysis
- Validate report quality and completeness
- Establish baseline for comparison

**Stage 2: Single Account, Two-Stage LLM Pipeline**
- Introduce Claude Haiku 4.5 as filtering layer
- Compare output quality against Stage 1 baseline
- Measure cost reduction from tiered approach
- Tune prompts for optimal filtering

**Stage 3: Multi-Account Support**
- Implement cross-account IAM role assumption
- Add parallel data collection
- Test with 2-4 accounts across different teams
- Validate aggregated reporting

**Stage 4: Production Rollout**
- Deploy to all target account based on defined project/groups/environments
- Configure monthly schedules via EventBridge
- Document operational procedures

### 4.2 Methodology

| Step | Method |
|------|--------|
| Architecture design | Iterative refinement with platform team |
| Development | Infrastructure-as-Code using AWS CDK |
| Testing | Compare AI-generated reports against manual analysis |
| Validation | Stakeholder review of report usefulness |
| Feedback loop | Weekly check-ins during POC phase |

---

## 5. Architecture & Design

### 5.1 Solution Overview

The proposed solution is a **serverless, AI-powered monitoring pipeline** using:

- **AWS Lambda** for compute (no servers to manage)
- **Amazon Bedrock** for generative AI analysis
- **Amazon EventBridge** for monthly scheduling
- **Amazon SNS** for email delivery
- **AWS IAM** for secure cross-account access

### 5.2 Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    MONTHLY TRIGGER (EventBridge)                │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PARALLEL DATA COLLECTION                     │
│                                                                 │
│   Account A          Account B          Account C               │
│       │                  │                  │                   │
│   Cost Explorer      Cost Explorer      Cost Explorer           │
│   Trusted Advisor    Trusted Advisor    Trusted Advisor         │
│   Health API         Health API         Health API              │
│       │                  │                  │                   │
│       └──────────────────┴──────────────────┘                   │
│                          │                                      │
│                    Raw Data (~50KB per account)                 │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│              STAGE 1: FILTER (Claude Haiku - Fast & Cheap)      │
│                                                                 │
│   "Extract only items requiring attention"                      │
│   - Cost anomalies and top services per account                 │
│   - Security issues (ERROR/WARNING only)                        │
│   - Upcoming maintenance events                                 │
│   - Service limit warnings                                      │
│                                                                 │
│   Output: Filtered JSON (~5KB)                                  │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│            STAGE 2: ANALYSE (Claude Opus - Powerful)            │
│                                                                 │
│   "Generate executive report with prioritised recommendations"  │
│   - Executive summary (30-second read)                          │
│   - Cost analysis with per-account breakdown                    │
│   - Platform alerts table                                       │
│   - Security findings summary                                   │
│   - Top 5 recommended actions                                   │
│                                                                 │
│   Output: Markdown report (~2000 words)                         │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EMAIL DELIVERY (SNS)                         │
│                                                                 │
│   Subject: [team-name] AWS Health Report - 2026-01-22           │
│   To: team-leads@company.com                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Why Two-Stage LLM Pipeline?

Sending raw data directly to a powerful (expensive) model is wasteful:

| Approach | Input to Expensive Model | Cost |
|----------|-------------------------|------|
| Single model | ~200KB raw data | ~$0.80/run |
| Two-stage | ~5KB filtered data | ~$0.40/run |

The cheap model (Haiku) handles the "grunt work" of filtering. The powerful model (Opus) focuses on generating insights from high-signal data only.

### 5.4 Core Design Principles

| Principle | Implementation |
|-----------|----------------|
| Serverless | Lambda, EventBridge, SNS - no infrastructure to manage |
| Cost Efficient | Two-stage LLM pipeline, pay-per-use compute |
| Scalable | Parallel processing, account groups |
| Secure | IAM roles with least-privilege, no credentials stored |
| Maintainable | Infrastructure-as-Code, configuration-driven |

---

## 6. AWS Services Used

| Service | Purpose |
|---------|---------|
| AWS Lambda | Runs the data collection and AI processing logic |
| Amazon Bedrock | Provides Claude AI models for analysis |
| Amazon EventBridge | Triggers monthly execution |
| Amazon SNS | Delivers reports via email |
| AWS Cost Explorer | Provides cost and usage data |
| AWS Trusted Advisor | Provides security, cost, and performance findings |
| AWS Health | Provides platform alerts and maintenance notices |
| AWS IAM | Enables secure cross-account access |
| AWS CloudWatch | Logging and monitoring |

---

## 7. Cost Estimation

### 7.1 Per-Run Cost Breakdown

| Component | Usage | Unit Price | Cost |
|-----------|-------|------------|------|
| Lambda | 4 min × 512MB | $0.0000166667/GB-s | ~$0.002 |
| Bedrock Haiku (Stage 1) | ~35K input tokens | $0.001/1K tokens | ~$0.04 |
| Bedrock Opus (Stage 2) | ~8K input tokens | $0.015/1K tokens | ~$0.35 |
| SNS Email | 1 email | $0.00 | $0.00 |
| **Total per run** | | | **~$0.40** |

### 7.2 Monthly Cost by Scale

| Accounts | Groups | Runs/Month | Monthly Cost | Yearly Cost |
|----------|--------|------------|--------------|-------------|
| 2 | 1 | 1 | $0.40 | $5 |
| 6 | 2 | 2 | $0.80 | $10 |
| 12 | 3 | 3 | $1.20 | $15 |

**Note:** Costs are indicative and will be refined based on actual token usage during POC execution.


## 8. Risks & Limitations

### 8.1 Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Bedrock model availability | Low | High | Use cross-region inference profiles |
| API rate limits | Low | Medium | Implement retry logic with backoff |
| Lambda timeout | Medium | Medium | Parallel processing, 15-min timeout |
| AI hallucination | Low | Medium | Validate sample reports against console |

### 8.2 Limitations

- **Requires Business/Enterprise Support**: Trusted Advisor and Health API access requires paid AWS support plan
- **Monthly granularity**: Not suitable for real-time alerting use cases
- **English only**: Reports generated in English
- **No automated remediation**: Reports identify issues but do not fix them
- **AI interpretation**: Recommendations are AI-generated and should be reviewed by humans before action

### 8.3 Dependencies

- Amazon Bedrock Claude models enabled in target region
- SNS email subscription confirmed by recipients
- IAM roles deployed to all member accounts
- Network connectivity from Lambda to AWS APIs

---

## 9. Implementation Timeline

### 9.1 Proposed Schedule

| Phase | Duration | Activities | Deliverables |
|-------|----------|------------|--------------|
| **Stage 1** | 2-4 week | Single account, single LLM, validate data collection and report quality | Working prototype, baseline report |
| **Stage 2** | 1-2 week | Add two-stage pipeline, compare quality, measure cost savings | Cost-optimised pipeline, quality comparison |
| **Stage 3** | 1-2 week | Multi-account support, parallel processing, test with 4 accounts | Multi-account deployment, performance metrics |
| **Stage 4** | 4-6 week | Production rollout, documentation, handover | Production deployment, runbook, training |

**Total POC Duration: 4 weeks**

### 9.2 Resource Requirements

| Role | Effort | Responsibility |
|------|--------|----------------|
| Cloud Engineer | 12 weeks | Development, testing, deployment |

---

## 10. Next Steps

If this POC is approved:

1. **Week 1**: Set up development environment, implement Stage 1
2. **Week 2**: Implement two-stage pipeline, validate quality
3. **Week 3**: Add multi-account support, test with pilot accounts
4. **Week 4**: Production deployment, documentation, handover

### 10.1 Approval Required

- [ ] Platform team approval for IAM role deployment
- [ ] Budget approval for Bedrock usage (~$10/year)
- [ ] Stakeholder commitment for weekly feedback sessions

### 10.2 Questions for Discussion

1. Which AWS account / groups should be included in the initial rollout?
2. Who should receive the monthly reports for each group?
3. Are there specific findings or metrics that must be included?
4. What is the preferred report delivery time (e.g., 1st of month, 9 AM)?

---

## Appendix A: Sample Report Structure

```
[sandbox-lab] AWS Health Report - 2026-01-22

## Executive Summary
Brief overview of key findings across all accounts...

## Cost Analysis
| Account | Current Month | Previous Month | Change |
|---------|---------------|----------------|--------|
| dev | $1,234 | $1,100 | +12% |
| prod | $567 | $590 | -4% |
| TOTAL | $1,801 | $1,690 | +7% |

### Top 5 Cost Drivers - dev
| Service | Cost | % of Total |
|---------|------|------------|
| EC2 | $500 | 40% |
| S3 | $300 | 24% |
...

## Platform Alerts
| Priority | Service | Date | Action Required |
|----------|---------|------|-----------------|
| High | RDS | Feb 15 | MySQL 5.7 EOL migration |
...

## Security Findings
| Severity | Count | Top Issue |
|----------|-------|-----------|
| Critical | 2 | Public S3 buckets |
| High | 5 | Open security groups |
...

## Top 5 Recommended Actions
| Priority | Action | Owner | Timeline |
|----------|--------|-------|----------|
| 1 | Fix public S3 buckets | Security | 24 hours |
| 2 | Migrate RDS to MySQL 8 | DBA | 2 weeks |
...
```

---

## Appendix B: Account Group Configuration

Account groups are defined in a simple configuration file:

```python
account_groups = {
    "platform-team": {
        "accounts": [
            {"id": "111111111111", "name": "sandbox"},
            {"id": "222222222222", "name": "production"}
        ],
        "email": "platform-leads@company.com"
    },
    "data-team": {
        "accounts": [
            {"id": "333333333333", "name": "data-dev"},
            {"id": "444444444444", "name": "data-prod"}
        ],
        "email": "data-leads@company.com"
    }
}
```

Adding a new account group requires:
1. Deploy IAM role to member accounts (one-time, 5 minutes each)
2. Add entry to configuration file
3. Run deployment command

No code changes required.

---

**Document Version:** 1.0  
**Last Updated:** January 2026
