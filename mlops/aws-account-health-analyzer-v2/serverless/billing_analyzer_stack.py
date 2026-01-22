from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_events as events,
    aws_events_targets as targets,
    aws_iam as iam,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
)
from constructs import Construct
from typing import List
import json


class BillingAnalyzerStack(Stack):
    def __init__(
        self, 
        scope: Construct, 
        construct_id: str,
        group_name: str = "default",
        member_accounts: List[str] = None,
        account_names: dict = None,
        notification_email: str = None,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        member_accounts = member_accounts or []
        account_names = account_names or {}
        local_account = member_accounts[0] if member_accounts else ""
        other_accounts = ",".join(member_accounts[1:]) if len(member_accounts) > 1 else ""

        # SNS Topic for email notifications
        topic = sns.Topic(self, "HealthAnalysisTopic")
        if notification_email:
            topic.add_subscription(subscriptions.EmailSubscription(notification_email))

        # Lambda function
        analyzer_function = _lambda.Function(
            self, "HealthAnalyzer",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="billing_analyzer.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(900),
            memory_size=512,
            environment={
                "STAGE1_MODEL_ID": "au.anthropic.claude-haiku-4-5-20251001-v1:0",
                "STAGE2_MODEL_ID": "global.anthropic.claude-opus-4-5-20251101-v1:0",
                "LOCAL_ACCOUNT_ID": local_account,
                "MEMBER_ACCOUNTS": other_accounts,
                "MEMBER_ROLE_NAME": "HealthAnalyzerReadOnly",
                "SNS_TOPIC_ARN": topic.topic_arn,
                "GROUP_NAME": group_name,
                "ACCOUNT_NAMES": json.dumps(account_names)
            }
        )

        # STS permissions for cross-account role assumption
        analyzer_function.add_to_role_policy(iam.PolicyStatement(
            actions=["sts:AssumeRole"],
            resources=["arn:aws:iam::*:role/HealthAnalyzerReadOnly"]
        ))

        # Cost Explorer permissions
        analyzer_function.add_to_role_policy(iam.PolicyStatement(
            actions=["ce:GetCostAndUsage", "ce:GetAnomalies"],
            resources=["*"]
        ))
        
        # Bedrock permissions
        analyzer_function.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
            resources=["*"]
        ))
        
        # Marketplace permissions for Bedrock models
        analyzer_function.add_to_role_policy(iam.PolicyStatement(
            actions=["aws-marketplace:ViewSubscriptions", "aws-marketplace:Subscribe"],
            resources=["*"]
        ))
        
        # Trusted Advisor permissions
        analyzer_function.add_to_role_policy(iam.PolicyStatement(
            actions=["support:DescribeTrustedAdvisorChecks", "support:DescribeTrustedAdvisorCheckResult"],
            resources=["*"]
        ))
        
        # AWS Health API permissions
        analyzer_function.add_to_role_policy(iam.PolicyStatement(
            actions=["health:DescribeEvents", "health:DescribeEventDetails", "health:DescribeAffectedEntities"],
            resources=["*"]
        ))
        
        topic.grant_publish(analyzer_function)

        # EventBridge rule - monthly on 1st at 9 AM AEST (23:00 UTC previous day)
        events.Rule(
            self, "MonthlyHealthRule",
            schedule=events.Schedule.cron(minute="0", hour="23", day="1", month="*"),
            targets=[targets.LambdaFunction(analyzer_function)]
        )
