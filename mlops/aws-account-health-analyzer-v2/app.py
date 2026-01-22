#!/usr/bin/env python3
import aws_cdk as cdk
from serverless.billing_analyzer_stack import BillingAnalyzerStack

app = cdk.App()

# Configure your account groups here
# Each group gets its own Lambda, SNS topic, and monthly schedule
account_groups = {
    "team-a": {
        "accounts": [
            {"id": "111111111111", "name": "dev"},
            {"id": "222222222222", "name": "staging"},
            {"id": "333333333333", "name": "prod"}
        ],
        "email": "team-a@example.com"
    },
    "team-b": {
        "accounts": [
            {"id": "444444444444", "name": "sandbox"},
            {"id": "555555555555", "name": "production"}
        ],
        "email": "team-b@example.com"
    },
}

# Deploy one stack per account group
for group_name, config in account_groups.items():
    BillingAnalyzerStack(
        app,
        f"HealthAnalyzer-{group_name}",
        group_name=group_name,
        accounts=config["accounts"],
        email=config["email"],
        env=cdk.Environment(
            account="111111111111",  # Main account where Lambda runs
            region="ap-southeast-2"
        )
    )

app.synth()
