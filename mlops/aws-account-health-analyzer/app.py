#!/usr/bin/env python3
import aws_cdk as cdk
from serverless.billing_analyzer_stack import BillingAnalyzerStack

app = cdk.App()
BillingAnalyzerStack(app, "BillingAnalyzerStack",
    env=cdk.Environment(region='ap-southeast-2')
)

app.synth()
