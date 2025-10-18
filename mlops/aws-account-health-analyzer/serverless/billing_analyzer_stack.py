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

class BillingAnalyzerStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # SNS Topic for email notifications
        topic = sns.Topic(self, "BillingAnalysisTopic")
        topic.add_subscription(subscriptions.EmailSubscription("your-email@example.com"))

        # Lambda function
        billing_function = _lambda.Function(
            self, "BillingAnalyzer",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="billing_analyzer.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(300),
            memory_size=512,
            environment={
                "BEDROCK_MODEL_ID": "apac.anthropic.claude-sonnet-4-20250514-v1:0",
                "SNS_TOPIC_ARN": topic.topic_arn
            }
        )

        # IAM permissions
        billing_function.add_to_role_policy(iam.PolicyStatement(
            actions=["ce:GetCostAndUsage"],
            resources=["*"]
        ))
        
        billing_function.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "bedrock:InvokeModel",
                "bedrock:InvokeModelWithResponseStream",
                "bedrock:ListInferenceProfiles",
                "bedrock:GetInferenceProfile"
            ],
            resources=["*"]
        ))
        
        billing_function.add_to_role_policy(iam.PolicyStatement(
            actions=[
                "support:DescribeTrustedAdvisorChecks",
                "support:DescribeTrustedAdvisorCheckResult"
            ],
            resources=["*"]
        ))
        
        topic.grant_publish(billing_function)

        # EventBridge rule - monthly on 1st at 9 AM
        rule = events.Rule(
            self, "MonthlyBillingRule",
            schedule=events.Schedule.cron(minute="0", hour="9", day="1", month="*")
        )
        
        rule.add_target(targets.LambdaFunction(billing_function))
