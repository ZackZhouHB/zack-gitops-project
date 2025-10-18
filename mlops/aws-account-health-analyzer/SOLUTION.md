# AWS Serverless Billing & Health Analyzer with AI

An intelligent AWS account monitoring solution that combines serverless architecture with AI-powered analysis to deliver comprehensive monthly reports on costs, performance, and security.

## 💡 The Idea

As cloud engineers, we need proactive insights into our AWS accounts - not just raw billing data, but intelligent analysis that identifies issues and recommends actions. This solution automates monthly account health checks by:

- Fetching billing data from AWS Cost Explorer
- Collecting Trusted Advisor recommendations (Cost, Performance, Security)
- Using Amazon Bedrock (Claude Sonnet 4) to analyze and synthesize insights
- Delivering actionable reports via email

## 🏗️ Architecture

```
EventBridge (Monthly Trigger)
    ↓
Lambda Function
    ├─→ Cost Explorer API (Billing Data)
    ├─→ Trusted Advisor API (Recommendations)
    ├─→ Bedrock API (AI Analysis)
    └─→ SNS Topic (Email Delivery)
```

**Tech Stack:**
- **IaC**: AWS CDK (Python)
- **Compute**: AWS Lambda (Python 3.12)
- **AI**: Amazon Bedrock (Claude Sonnet 4 via Inference Profile)
- **APIs**: Cost Explorer, Trusted Advisor, Bedrock
- **Notifications**: Amazon SNS
- **Scheduling**: Amazon EventBridge

## 🚀 Implementation Steps

### 1. Project Setup
```bash
# Install CDK
npm install -g aws-cdk

# Initialize CDK project
cdk init app --language python
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Bootstrap CDK
```bash
cdk bootstrap aws://ACCOUNT-ID/ap-southeast-2 --profile sandboxtest
```

### 3. Deploy Infrastructure
```bash
cdk deploy --profile sandboxtest
```

### 4. Confirm SNS Subscription
Check your email and confirm the SNS subscription to receive reports.

### 5. Manual Test
```bash
aws lambda invoke \
  --function-name BillingAnalyzerStack-BillingAnalyzer* \
  --profile sandboxtest \
  --region ap-southeast-2 \
  /tmp/test.json
```

## 🐛 Issues Encountered & Solutions

### Issue 1: SES DMARC Rejection
**Problem**: SES couldn't send emails from `@nesa.nsw.edu.au` domain due to DMARC policy rejection.

**Solution**: Switched from SES to SNS for email delivery - simpler and no DMARC issues.

### Issue 2: Lambda Timeout with Trusted Advisor
**Problem**: Lambda timed out (159 seconds) when iterating through all 537 Trusted Advisor checks.

**Solution**: Optimized to check only key checks (10 instead of 358):
- Cost: Elastic IPs, EBS volumes, Load Balancers
- Performance: EC2 utilization, EBS IOPS
- Security: Security Groups, MFA, IAM

**Result**: Execution time reduced from 159s to ~20s.

### Issue 3: Bedrock Model Access
**Problem**: Initial model (Claude Haiku) needed upgrade for better analysis quality.

**Solution**: Used inference profile `apac.anthropic.claude-sonnet-4-20250514-v1:0` with proper IAM permissions matching existing EKS workloads.

## ✅ What We Achieved

### Automated Monthly Reports Including:
1. **Cost Analysis**
   - Total monthly spend
   - Top 10 services by cost
   - Cost trends and anomalies
   - AI-generated optimization recommendations

2. **Trusted Advisor Insights**
   - Cost optimization opportunities (unused resources)
   - Performance issues (underutilized instances)
   - Security vulnerabilities (open security groups)

3. **AI-Powered Recommendations**
   - Prioritized action items
   - Context-aware suggestions
   - Cost savings estimates

### Example Output:
```
Total Cost: $1,776.87
- CloudHSM: $1,505.69 (84.7%) ⚠️
- Security Groups: 4 critical violations
- Unused Resources: 1 Elastic IP, 1 EBS volume

Priority Actions:
1. Fix security group rules (CRITICAL)
2. Review CloudHSM usage (84% of costs)
3. Clean up unused resources ($5-25/month savings)
```

## 🎯 Value for Cloud Engineers

### 1. **Proactive Monitoring**
- Automated monthly health checks
- No manual data gathering
- Consistent reporting schedule

### 2. **AI-Powered Insights**
- Beyond raw metrics - get actionable recommendations
- Context-aware analysis combining multiple data sources
- Natural language summaries for stakeholders

### 3. **Cost Optimization**
- Identify waste automatically
- Quantified savings opportunities
- Track spending trends over time

### 4. **Security Posture**
- Continuous security monitoring
- Immediate alerts for critical issues
- Compliance-ready reporting

### 5. **Serverless Benefits**
- Zero infrastructure management
- Pay-per-execution pricing (~$0.50/month)
- Scales automatically
- High availability built-in

### 6. **Skills Development**
- Modern IaC with CDK
- Serverless architecture patterns
- AI/ML integration with Bedrock
- AWS API orchestration

## 📊 Cost Breakdown

**Monthly Operating Costs:**
- Lambda: ~$0.10 (1 execution/month, 20s duration)
- Bedrock: ~$0.30 (Claude Sonnet 4, ~2000 tokens)
- SNS: ~$0.01 (1 email/month)
- Cost Explorer API: Free
- Trusted Advisor API: Free (with Business/Enterprise Support)

**Total: ~$0.50/month**

## 🔧 Configuration

### Update Email Recipient
Edit `serverless/billing_analyzer_stack.py`:
```python
topic.add_subscription(subscriptions.EmailSubscription("your-email@example.com"))
```

### Change Schedule
Edit `serverless/billing_analyzer_stack.py`:
```python
# Monthly on 1st at 9 AM
schedule=events.Schedule.cron(minute="0", hour="9", day="1", month="*")

# Weekly on Monday at 9 AM
schedule=events.Schedule.cron(minute="0", hour="9", day_of_week="MON")
```

### Switch Bedrock Model
Edit `serverless/billing_analyzer_stack.py`:
```python
environment={
    "BEDROCK_MODEL_ID": "anthropic.claude-3-haiku-20240307-v1:0"  # Cheaper option
}
```

## 📁 Project Structure

```
serverless/
├── app.py                              # CDK app entry point
├── cdk.json                            # CDK configuration
├── requirements.txt                    # CDK dependencies
├── serverless/
│   ├── __init__.py
│   └── billing_analyzer_stack.py       # Stack definition
└── lambda/
    └── billing_analyzer.py             # Lambda handler
```

## 🚀 Future Enhancements

- [ ] Store historical data in S3 for trend analysis
- [ ] Add DynamoDB for tracking month-over-month changes
- [ ] Create CloudWatch dashboard with key metrics
- [ ] Add Slack/Teams integration
- [ ] Multi-account support with AWS Organizations
- [ ] Custom Trusted Advisor check selection via parameters
- [ ] Cost anomaly detection with ML

## 🎓 Key Learnings

1. **Serverless + AI = Powerful Automation**: Combining AWS serverless services with Bedrock creates intelligent automation with minimal code.

2. **API Optimization Matters**: Always profile API calls - 358 checks vs 10 checks made the difference between timeout and success.

3. **Infrastructure as Code**: CDK makes complex architectures reproducible and maintainable.

4. **AI Context is Key**: Providing structured data (billing + Trusted Advisor) to AI generates far better insights than raw data alone.

5. **Cost-Effective Intelligence**: For $0.50/month, you get enterprise-grade monitoring and AI analysis.

## 📚 Resources

- [AWS CDK Documentation](https://docs.aws.amazon.com/cdk/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [AWS Cost Explorer API](https://docs.aws.amazon.com/cost-management/latest/APIReference/)
- [AWS Trusted Advisor](https://aws.amazon.com/premiumsupport/technology/trusted-advisor/)
- [Claude on Bedrock](https://docs.anthropic.com/en/api/claude-on-amazon-bedrock)

## 🤝 Contributing

This is a learning project demonstrating serverless + AI patterns. Feel free to fork and adapt for your needs!

## 📝 License

MIT License - Use freely for personal and commercial projects.

---

**Built with ❤️ using AWS CDK, Lambda, Bedrock, and Claude Sonnet 4**
