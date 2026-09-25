---
title: "Serverless Billing & Health Analyzer with Bedrock"
date: 2025-10-18T11:42:05Z
slug: serverless-billing-health-analyzer-with-bedrock
categories: ["Machine Learning"]
aliases: ["/post/157/"]
legacy_id: 157
---
I constantly rely on AWS Billing and Cost Management and Trusted Advisor to monitor costs and security. However, manual billing reviews are time-consuming, and raw Cost Explorer data doesn’t provide the full picture. What if an intelligent program could proactively call the Billing and Trusted Advisor APIs, retrieve the raw data, and pass it to an LLM for in-depth analysis of account health—then deliver actionable insights and AI-powered recommendations? That would save a significant amount of time and effort.

This post documents building a serverless billing and health analyzer powered by Amazon Bedrock — the challenges faced, solutions implemented, and what this means for modern cloud operations.

**Why Serverless + AI-Powered?**

**Serverless architecture** combined with **AI-powered analysis** creates intelligent automation with zero infrastructure management, pay-per-execution pricing (~$0.50/month), automatic scaling and high availability, natural language insights beyond raw metrics, and proactive monitoring with minimal operational overhead.

```bash
# Architecture
┌─────────────────────────────────────────────────────────────────────┐
│  EventBridge (Monthly) → Lambda Function                           │
│                          ├─ Cost Explorer API (Billing Data)        │
│                          ├─ Trusted Advisor API (Recommendations)   │
│                          ├─ Bedrock API (AI Analysis)               │
│                          └─ SNS Topic (Email Delivery)              │
└─────────────────────────────────────────────────────────────────────┘

# Tech Stack
- Infrastructure as Code: AWS CDK (Python)
- Compute: AWS Lambda (Python 3.12)
- AI/ML: Amazon Bedrock (Claude Sonnet 4 via Inference Profile)
- APIs: Cost Explorer, Trusted Advisor, Bedrock Runtime
- Notifications: Amazon SNS
- Scheduling: Amazon EventBridge

# Folder Structure
root@zack:/mnt/f/zack-gitops-project/mlops/aws-account-health-analyzer# tree
.
├── README.md
├── SOLUTION.md
├── app.py
├── cdk.json
├── cdk.out
│   ├── BillingAnalyzerStack.assets.json
│   ├── BillingAnalyzerStack.template.json
│   ├── cdk.out
│   ├── manifest.json
│   └── tree.json
├── lambda
│   └── billing_analyzer.py
├── requirements-dev.txt
├── requirements.txt
├── serverless
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── __init__.cpython-312.pyc
│   │   └── billing_analyzer_stack.cpython-312.pyc
│   ├── billing_analyzer_stack.py
│   └── serverless_stack.py
├── source.bat
└── tests
    ├── __init__.py
    └── unit
        ├── __init__.py
        └── test_serverless_stack.py

# Monthly Operating Cost: ~$0.50
- Lambda: ~$0.10 (1 execution/month, 20s duration)
- Bedrock: ~$0.30 (Claude Sonnet 4, ~2000 tokens)
- SNS: ~$0.01 (1 email/month)
```

**Implementation Journey: Challenges & Solutions**

- **Lambda Timeout and Bedrock Token**
  Lambda timed out after 159 seconds when iterating through all 537 Trusted Advisor checks. **Solution:** Bedrock API tokens optimized to check only `Trust Advisor action recommended checks` (Security, Service limits and Fault tolerance) instead of 358 checks, reducing Bedrock API token and Lambda execution time to ~20 seconds.
[![[Conversation Example Screenshot]](/images/cdk2.png)](/images/cdk2.png)- **Bedrock Inference Profile Access**
  Needed to upgrade from Claude Haiku to Claude Sonnet 4 for better analysis quality. **Solution:** Used inference profile `apac.anthropic.claude-sonnet-4-20250514-v1:0` with updated IAM permissions matching existing EKS workload patterns.

**Deployment with AWS CDK**

```bash
# Setup
$ npm install -g aws-cdk
$ cdk init app --language python
$ source .venv/bin/activate
$ pip install -r requirements.txt

# Configure email in serverless/billing_analyzer_stack.py
topic.add_subscription(subscriptions.EmailSubscription("your-email@example.com"))

# Deploy
$ cdk bootstrap aws://ACCOUNT-ID/ap-southeast-2 --profile YOUR-PROFILE
$ cdk deploy --profile YOUR-PROFILE

# Test manually
$ aws lambda invoke \
  --function-name BillingAnalyzerStack-BillingAnalyzer* \
  --profile YOUR-PROFILE \
  /tmp/test.json

# Cleanup
$ cdk destroy --profile YOUR-PROFILE --force
```

**Sample Report Output**

The AI-powered report combines billing data with Trusted Advisor recommendations:

[![[Conversation Example Screenshot]](/images/cdk1.png)](/images/cdk1.png)

**Validation & Accuracy**

To ensure AI recommendations were accurate, I asked Amazon Q to validate Bedrock API generated findings against actual AWS resources and issues — achieving 100% accuracy. The AI-Powered solution correctly identified 1 Elastic IP, 1 EBS volume, 4 security group violations, and proper MFA configuration, with appropriate prioritization of the critical security risk.

[![[Conversation Example Screenshot]](/images/cdk3.png)](/images/cdk3.png)

**Next Step Enhencement**

At this moment, Amazon Q is my best partner, as I copied the email findings and asked Amazon Q to cross-check and validate them, then requested Amazon Q to take appropriate actions to remove the EIP, EBS and SG ports.

This can also be achieved by integrating with AI tools and agents—for example, using a Bedrock model to generate scripts or AWS CLI commands directly from the email, or passing the task to a Lambda function to perform the mitigation. This enables a fully automated workflow. Additionally, I can later integrate Cost Anomaly Detection into the Lambda function to fetch and analyze cost data, allowing me to be notified immediately whenever an unusual cost spike pattern occurs.

**Conclusion**

Building a serverless billing analyzer with Amazon Bedrock demonstrates how modern cloud engineers can leverage serverless + AI to create intelligent automation that provides real business value for ~$0.50/month.

The complete implementation — including CDK stack definitions, Lambda code, and comprehensive documentation — is available at [my GitHub repository](https://github.com/ZackZhouHB/zack-gitops-project/tree/editing/mlops/aws-account-health-analyzer). Special thanks to Amazon Q for assistance throughout this journey.
