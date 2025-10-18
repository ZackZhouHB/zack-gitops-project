# AI-Powered AWS Serverless Billing & Health Analyzer with Bedrock

This project provides an automated way to get monthly reports on your AWS account's costs, performance, and security. It uses a serverless setup and AI to give you smart recommendations.

For a deep dive into the project's architecture, implementation details, and technical breakdown, please see [SOLUTION.md](SOLUTION.md).

## 🚀 Getting Started

Follow these steps to get the billing and health analyzer up and running in your own AWS account.

### Prerequisites

*   An AWS account
*   [Node.js and npm](https://nodejs.org/en/download/) installed
*   [AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) installed (`npm install -g aws-cdk`)
*   [Python 3.12](https://www.python.org/downloads/) installed
*   AWS credentials configured in your environment
*   Amazon Bedrock model access granted

### 1. Set Up the Project

First, clone the repository and install the necessary Python packages.

```bash
# Clone the repository
git clone <repository-url>
cd serverless

# Create a virtual environment and activate it
python3 -m venv .venv
source .venv/bin/activate

# Install the required Python packages
pip install -r requirements.txt
```

### 2. Configure the Email Recipient

You need to specify where the monthly reports should be sent.

1.  Open the `serverless/billing_analyzer_stack.py` file.
2.  Find the following line of code:

    ```python
    topic.add_subscription(subscriptions.EmailSubscription("your-email@example.com"))
    ```

3.  Replace `"your-email@example.com"` with your own email address.

### 3. Deploy the Stack

Now you can deploy the entire application to your AWS account using the AWS CDK.

```bash
# Bootstrap your AWS account for CDK (only needs to be done once per account/region)
cdk bootstrap aws://ACCOUNT-ID/REGION --profile YOUR-PROFILE

# Deploy the stack
cdk deploy --profile YOUR-PROFILE
```

Replace `ACCOUNT-ID`, `REGION`, and `YOUR-PROFILE` with your specific AWS account ID, region, and AWS CLI profile name.

### 4. Confirm Your Subscription

After the deployment is complete, you will receive an email from AWS Notification to confirm your subscription to the SNS topic. Click the link in the email to confirm.

You are now all set up! You will receive your first report at the beginning of next month.

## Manual Test (Optional)

If you want to test the function immediately, you can invoke the Lambda function manually.

```bash
aws lambda invoke \
  --function-name BillingAnalyzerStack-BillingAnalyzer* \
  --profile YOUR-PROFILE \
  --region YOUR-REGION \
  /tmp/test.json
```

This will trigger the analysis and send a report to your email.