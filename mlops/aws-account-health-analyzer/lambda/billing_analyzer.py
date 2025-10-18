import json
import os
import boto3
from datetime import datetime, timedelta

ce_client = boto3.client('ce')
bedrock_client = boto3.client('bedrock-runtime')
sns_client = boto3.client('sns')
support_client = boto3.client('support', region_name='us-east-1')

# Key checks to monitor (most important ones)
KEY_CHECKS = {
    'cost_optimizing': ['Underutilized Amazon EBS Volumes', 'Idle Load Balancers', 'Unassociated Elastic IP Addresses'],
    'performance': ['High Utilization Amazon EC2 Instances', 'Amazon EBS Provisioned IOPS (SSD) Volume Attachment Configuration'],
    'security': ['Security Groups - Specific Ports Unrestricted', 'IAM Use', 'MFA on Root Account']
}

def get_trusted_advisor_summary():
    """Get Trusted Advisor recommendations for key checks only"""
    all_checks = support_client.describe_trusted_advisor_checks(language='en')
    
    categories = {
        'cost_optimizing': [],
        'performance': [],
        'security': []
    }
    
    for check in all_checks['checks']:
        category = check['category']
        if category not in KEY_CHECKS:
            continue
        
        # Only check if it's in our key checks list
        if not any(key in check['name'] for key in KEY_CHECKS[category]):
            continue
            
        try:
            result = support_client.describe_trusted_advisor_check_result(
                checkId=check['id'],
                language='en'
            )
            
            status = result['result']['status']
            flagged = result['result'].get('flaggedResources', [])
            
            categories[category].append({
                'name': check['name'],
                'status': status,
                'flagged_count': len(flagged)
            })
        except Exception as e:
            continue
    
    return categories

def handler(event, context):
    # Get last month's date range
    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    
    start_date = first_day_last_month.strftime('%Y-%m-%d')
    end_date = first_day_this_month.strftime('%Y-%m-%d')
    
    # Get cost data
    response = ce_client.get_cost_and_usage(
        TimePeriod={'Start': start_date, 'End': end_date},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )
    
    # Format cost data
    cost_data = []
    for result in response['ResultsByTime']:
        for group in result['Groups']:
            service = group['Keys'][0]
            cost = float(group['Metrics']['UnblendedCost']['Amount'])
            if cost > 0.01:
                cost_data.append({'service': service, 'cost': cost})
    
    cost_data.sort(key=lambda x: x['cost'], reverse=True)
    total_cost = sum(item['cost'] for item in cost_data)
    
    # Get Trusted Advisor recommendations
    ta_summary = get_trusted_advisor_summary()
    
    # Prepare prompt for Bedrock
    prompt = f"""Analyze this AWS account health report for {start_date} to {end_date}:

## BILLING DATA
Total Cost: ${total_cost:.2f}
Top Services: {json.dumps(cost_data[:10], indent=2)}

## TRUSTED ADVISOR KEY FINDINGS
Cost Optimization: {json.dumps(ta_summary['cost_optimizing'], indent=2)}
Performance: {json.dumps(ta_summary['performance'], indent=2)}
Security: {json.dumps(ta_summary['security'], indent=2)}

Provide a comprehensive report with:
1. Cost Analysis (summary, top drivers, trends)
2. Cost Optimization Recommendations (from billing data and Trusted Advisor)
3. Performance Summary (from Trusted Advisor findings)
4. Security Summary (from Trusted Advisor findings)
5. Top 3 Priority Actions"""
    
    # Call Bedrock
    bedrock_response = bedrock_client.invoke_model(
        modelId=os.environ['BEDROCK_MODEL_ID'],
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 3000,
            "messages": [{"role": "user", "content": prompt}]
        })
    )
    
    analysis = json.loads(bedrock_response['body'].read())['content'][0]['text']
    
    # Send via SNS
    sns_client.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Subject=f'AWS Health Report - {start_date}',
        Message=f"""AWS Account Health Report
Period: {start_date} to {end_date}
Total Cost: ${total_cost:.2f}

{analysis}

---
DETAILED DATA

Top 10 Services by Cost:
{json.dumps(cost_data[:10], indent=2)}

Trusted Advisor Summary:
- Cost Optimization Checks: {len(ta_summary['cost_optimizing'])}
- Performance Checks: {len(ta_summary['performance'])}
- Security Checks: {len(ta_summary['security'])}"""
    )
    
    return {'statusCode': 200, 'body': 'Health report sent via SNS'}
