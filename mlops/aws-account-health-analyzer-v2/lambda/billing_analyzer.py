import json
import os
import boto3
import logging
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Global clients (for local account)
bedrock_client = boto3.client('bedrock-runtime')
sns_client = boto3.client('sns')
sts_client = boto3.client('sts')

STAGE1_MODEL = os.environ.get('STAGE1_MODEL_ID', 'au.anthropic.claude-haiku-4-5-20251001-v1:0')
STAGE2_MODEL = os.environ.get('STAGE2_MODEL_ID', 'global.anthropic.claude-opus-4-5-20251101-v1:0')
MEMBER_ACCOUNTS = os.environ.get('MEMBER_ACCOUNTS', '').split(',') if os.environ.get('MEMBER_ACCOUNTS') else []
MEMBER_ROLE_NAME = os.environ.get('MEMBER_ROLE_NAME', 'HealthAnalyzerReadOnly')
LOCAL_ACCOUNT_ID = os.environ.get('LOCAL_ACCOUNT_ID', '')
GROUP_NAME = os.environ.get('GROUP_NAME', 'default')
ACCOUNT_NAMES = json.loads(os.environ.get('ACCOUNT_NAMES', '{}'))


def get_clients_for_account(account_id):
    """Get boto3 clients for a specific account (assume role if not local)"""
    if not LOCAL_ACCOUNT_ID or account_id == LOCAL_ACCOUNT_ID:
        # Local account - use default credentials
        return {
            'ce': boto3.client('ce'),
            'support': boto3.client('support', region_name='us-east-1'),
            'health': boto3.client('health', region_name='us-east-1')
        }
    
    # Remote account - assume role
    logger.info(f"Assuming role in account {account_id}")
    role_arn = f"arn:aws:iam::{account_id}:role/{MEMBER_ROLE_NAME}"
    assumed = sts_client.assume_role(RoleArn=role_arn, RoleSessionName='HealthAnalyzer')
    creds = assumed['Credentials']
    
    return {
        'ce': boto3.client('ce',
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken']),
        'support': boto3.client('support', region_name='us-east-1',
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken']),
        'health': boto3.client('health', region_name='us-east-1',
            aws_access_key_id=creds['AccessKeyId'],
            aws_secret_access_key=creds['SecretAccessKey'],
            aws_session_token=creds['SessionToken'])
    }


def get_cost_data(ce_client):
    """Get current and previous month cost data for comparison"""
    logger.info("=== STAGE: Fetching Cost Explorer data ===")
    today = datetime.now()
    first_day_this_month = today.replace(day=1)
    last_day_last_month = first_day_this_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    first_day_two_months_ago = (first_day_last_month - timedelta(days=1)).replace(day=1)
    
    current_month = ce_client.get_cost_and_usage(
        TimePeriod={'Start': first_day_this_month.strftime('%Y-%m-%d'), 'End': today.strftime('%Y-%m-%d')},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )
    
    previous_month = ce_client.get_cost_and_usage(
        TimePeriod={'Start': first_day_last_month.strftime('%Y-%m-%d'), 'End': first_day_this_month.strftime('%Y-%m-%d')},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )
    
    two_months_ago = ce_client.get_cost_and_usage(
        TimePeriod={'Start': first_day_two_months_ago.strftime('%Y-%m-%d'), 'End': first_day_last_month.strftime('%Y-%m-%d')},
        Granularity='MONTHLY',
        Metrics=['UnblendedCost'],
        GroupBy=[{'Type': 'DIMENSION', 'Key': 'SERVICE'}]
    )
    
    def parse_costs(response):
        costs = {}
        for result in response['ResultsByTime']:
            for group in result['Groups']:
                service = group['Keys'][0]
                cost = float(group['Metrics']['UnblendedCost']['Amount'])
                if cost > 0.01:
                    costs[service] = round(cost, 2)
        return costs
    
    result = {
        'current_month': parse_costs(current_month),
        'previous_month': parse_costs(previous_month),
        'two_months_ago': parse_costs(two_months_ago),
        'periods': {
            'current': f"{first_day_this_month.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}",
            'previous': f"{first_day_last_month.strftime('%Y-%m-%d')} to {first_day_this_month.strftime('%Y-%m-%d')}",
        }
    }
    logger.info(f"Cost data fetched: current=${sum(result['current_month'].values()):.2f}, previous=${sum(result['previous_month'].values()):.2f}")
    return result


def get_cost_anomalies(ce_client):
    """Get cost anomalies from the last 90 days"""
    logger.info("=== STAGE: Fetching Cost Anomalies ===")
    today = datetime.now()
    start_date = (today - timedelta(days=90)).strftime('%Y-%m-%d')
    end_date = today.strftime('%Y-%m-%d')
    
    try:
        response = ce_client.get_anomalies(
            DateInterval={'StartDate': start_date, 'EndDate': end_date},
            MaxResults=10
        )
        return [{'service': a.get('DimensionValue', 'Unknown'),
                 'impact': round(float(a.get('Impact', {}).get('TotalImpact', 0)), 2)}
                for a in response.get('Anomalies', [])]
    except Exception:
        return []


def get_health_events(health_client):
    """Get AWS Health events"""
    logger.info("=== STAGE: Fetching AWS Health Events ===")
    events_data = {'scheduled': [], 'ongoing': [], 'notifications': []}
    
    try:
        response = health_client.describe_events(
            filter={'eventStatusCodes': ['open', 'upcoming']},
            maxResults=50
        )
        
        for event in response.get('events', []):
            event_info = {
                'service': event.get('service', 'Unknown'),
                'type': event.get('eventTypeCode', ''),
                'category': event.get('eventTypeCategory', ''),
                'region': event.get('region', 'global'),
                'start_time': event.get('startTime', '').isoformat() if event.get('startTime') else ''
            }
            
            if event.get('eventTypeCategory') == 'scheduledChange':
                events_data['scheduled'].append(event_info)
            elif event.get('eventTypeCategory') == 'issue':
                events_data['ongoing'].append(event_info)
            else:
                events_data['notifications'].append(event_info)
    except Exception:
        pass
    
    return events_data


def get_trusted_advisor_full(support_client):
    """Get all Trusted Advisor checks across all categories"""
    logger.info("=== STAGE: Fetching Trusted Advisor ===")
    all_checks = support_client.describe_trusted_advisor_checks(language='en')
    logger.info(f"Processing {len(all_checks['checks'])} checks")
    
    categories = {
        'cost_optimizing': [],
        'performance': [],
        'security': [],
        'fault_tolerance': [],
        'service_limits': []
    }
    
    for check in all_checks['checks']:
        category = check['category']
        if category not in categories:
            continue
        try:
            result = support_client.describe_trusted_advisor_check_result(checkId=check['id'], language='en')
            status = result['result']['status']
            
            if status in ['ok', 'not_available']:
                continue
                
            flagged = result['result'].get('flaggedResources', [])
            check_data = {
                'name': check['name'],
                'status': status,
                'flagged_count': len(flagged)
            }
            
            if flagged:
                check_data['flagged_resources'] = [r.get('metadata', [])[:4] for r in flagged[:5]]
            
            cost_estimate = result['result'].get('categorySpecificSummary', {}).get('costOptimizing', {})
            if cost_estimate.get('estimatedMonthlySavings'):
                check_data['estimated_monthly_savings'] = cost_estimate['estimatedMonthlySavings']
            
            categories[category].append(check_data)
        except Exception:
            continue
    
    logger.info(f"Trusted Advisor complete: {sum(len(v) for v in categories.values())} issues found")
    return categories


def invoke_bedrock(model_id, prompt, max_tokens=4000):
    """Helper to invoke Bedrock model"""
    response = bedrock_client.invoke_model(
        modelId=model_id,
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        })
    )
    return json.loads(response['body'].read())['content'][0]['text']


def stage1_filter(raw_data):
    """Stage 1: Use Haiku to filter and extract actionable items only"""
    logger.info(f"=== STAGE 1: Haiku Filter (model: {STAGE1_MODEL}) ===")
    logger.info(f"Input data size: {len(json.dumps(raw_data))} chars")
    
    prompt = f"""You are a data filter. Extract ONLY items requiring attention from this AWS data.

RAW DATA:
{json.dumps(raw_data)}

Return a JSON object with this exact structure:
{{
    "accounts": [
        {{
            "account_id": "<id>",
            "account_name": "<name>",
            "current_month": <number>,
            "previous_month": <number>,
            "mom_change_percent": <number>,
            "top_5_services": [{{"service": "<name>", "cost": <number>}}]
        }}
    ],
    "total_cost": {{"current": <number>, "previous": <number>}},
    "anomalies": [<only if any detected>],
    "health_events": {{
        "critical": [<events needing immediate attention>],
        "upcoming": [<scheduled maintenance>]
    }},
    "security_issues": [<only ERROR or WARNING status items with resource details>],
    "cost_optimization": [<items with savings potential, include estimated_monthly_savings>],
    "fault_tolerance": [<only ERROR status items>],
    "service_limits": [<only WARNING or ERROR status>],
    "filtered_summary": "<one sentence: X critical issues, Y warnings, $Z savings potential>"
}}

IMPORTANT: Keep cost data SEPARATE for each account. Return valid JSON only."""

    result = invoke_bedrock(STAGE1_MODEL, prompt, max_tokens=4000)
    logger.info(f"Stage 1 output size: {len(result)} chars")
    
    # Parse JSON from response
    try:
        # Handle potential markdown code blocks
        if '```json' in result:
            result = result.split('```json')[1].split('```')[0]
        elif '```' in result:
            result = result.split('```')[1].split('```')[0]
        return json.loads(result.strip())
    except json.JSONDecodeError as e:
        logger.error(f"Stage 1 JSON parse error: {e}")
        logger.error(f"Raw output: {result[:500]}...")
        return {'raw_fallback': raw_data, 'parse_error': True}


def stage2_analyze(filtered_data, cost_periods):
    """Stage 2: Use Opus for deep analysis on filtered data"""
    logger.info(f"=== STAGE 2: Opus Analysis (model: {STAGE2_MODEL}) ===")
    logger.info(f"Filtered data size: {len(json.dumps(filtered_data))} chars")
    
    prompt = f"""Analyze this AWS account health data and provide a concise executive report.

DATA:
{json.dumps(filtered_data, indent=2)}

PERIOD: {cost_periods.get('current', 'Current month')} vs {cost_periods.get('previous', 'Previous month')}

CONTEXT:
- These are INDEPENDENT AWS accounts analyzed together for consolidated reporting
- Do NOT compare accounts against each other - they are separate workloads
- Aggregate totals across all accounts for executive view

REPORT STRUCTURE:

1. **Executive Summary** (4-6 sentences for senior management)
   - Total spend across all accounts and trend direction
   - Number of critical risks requiring attention
   - Total savings opportunity (single dollar figure)
   - One key action needed this week
   - Keep high-level, no detailed metrics

2. **Cost Analysis**
   - Table format: Account | Current Month | Previous Month | Change %
   - One row per account, plus TOTAL row
   - Then for EACH account, show a separate "Top 5 Cost Drivers for [Account Name]" table
   - Note any anomalies

3. **Platform Alerts** (summary table: Priority, Service, Date, Action Required)

4. **Security Findings** (summary table with issue count by severity, top 3 critical items only)

5. **Top 5 Recommended Actions** (prioritized across ALL findings - security, cost, platform - with owner and timeline)

GUIDELINES:
- Keep total report under 2000 words
- Use tables instead of long lists
- Focus on actionable insights, not exhaustive details
- Include dollar amounts for cost/savings items
- Executive summary should be readable in 30 seconds"""

    result = invoke_bedrock(STAGE2_MODEL, prompt, max_tokens=4000)
    logger.info(f"Stage 2 output size: {len(result)} chars")
    return result


def collect_account_data(account_id):
    """Collect all data for a single account"""
    account_name = ACCOUNT_NAMES.get(account_id, account_id)
    logger.info(f"=== Collecting data for account {account_name} ({account_id}) ===")
    clients = get_clients_for_account(account_id)
    
    cost_data = get_cost_data(clients['ce'])
    anomalies = get_cost_anomalies(clients['ce'])
    health_events = get_health_events(clients['health'])
    ta_data = get_trusted_advisor_full(clients['support'])
    
    current_total = sum(cost_data['current_month'].values())
    previous_total = sum(cost_data['previous_month'].values())
    two_months_total = sum(cost_data['two_months_ago'].values())
    mom_change = ((previous_total - two_months_total) / two_months_total * 100) if two_months_total > 0 else 0
    
    return {
        'account_id': account_id,
        'account_name': account_name,
        'cost': {
            'current_month': round(current_total, 2),
            'previous_month': round(previous_total, 2),
            'two_months_ago': round(two_months_total, 2),
            'mom_change': round(mom_change, 1),
            'by_service': dict(sorted(cost_data['previous_month'].items(), key=lambda x: x[1], reverse=True)[:10])
        },
        'anomalies': anomalies,
        'health_events': health_events,
        'trusted_advisor': ta_data,
        'periods': cost_data['periods']
    }


def handler(event, context):
    logger.info("=== AWS Health Analyzer Started (Multi-Account Pipeline) ===")
    start_time = datetime.now()
    
    # Determine accounts to analyze
    accounts = [LOCAL_ACCOUNT_ID] if LOCAL_ACCOUNT_ID else []
    accounts.extend([a.strip() for a in MEMBER_ACCOUNTS if a.strip() and a.strip() != LOCAL_ACCOUNT_ID])
    
    if not accounts:
        accounts = [sts_client.get_caller_identity()['Account']]
    
    logger.info(f"Analyzing {len(accounts)} account(s) in parallel: {accounts}")
    
    # Collect data from all accounts IN PARALLEL
    all_accounts_data = []
    with ThreadPoolExecutor(max_workers=min(len(accounts), 4)) as executor:
        future_to_account = {executor.submit(collect_account_data, acc): acc for acc in accounts}
        for future in as_completed(future_to_account):
            account_id = future_to_account[future]
            try:
                data = future.result()
                all_accounts_data.append(data)
                logger.info(f"Completed data collection for account {account_id}")
            except Exception as e:
                logger.error(f"Failed to collect data for account {account_id}: {e}")
                all_accounts_data.append({'account_id': account_id, 'error': str(e)})
    
    # Aggregate for analysis
    raw_data = {'accounts': all_accounts_data}
    
    # Stage 1: Filter with Haiku
    filtered_data = stage1_filter(raw_data)
    
    # Get periods from first successful account
    periods = next((a['periods'] for a in all_accounts_data if 'periods' in a), {})
    
    # Stage 2: Analyze with Opus
    analysis = stage2_analyze(filtered_data, periods)
    
    # Count issues for summary
    total_ta = {}
    total_health = {'scheduled': 0, 'ongoing': 0, 'notifications': 0}
    for acct in all_accounts_data:
        if 'trusted_advisor' in acct:
            for cat, items in acct['trusted_advisor'].items():
                total_ta[cat] = total_ta.get(cat, 0) + len(items)
        if 'health_events' in acct:
            for k in total_health:
                total_health[k] += len(acct['health_events'].get(k, []))
    
    # Send via SNS
    logger.info("=== STAGE: Sending report via SNS ===")
    account_display = ', '.join([f"{ACCOUNT_NAMES.get(a, a)} ({a})" for a in accounts])
    sns_client.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'],
        Subject=f'[{GROUP_NAME}] AWS Health Report - {datetime.now().strftime("%Y-%m-%d")}',
        Message=f"""AWS Account Health Report - {GROUP_NAME}
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Group: {GROUP_NAME}
Accounts: {account_display}

{analysis}

---
RAW DATA SUMMARY

Accounts: {len(accounts)}
Cost Periods:
- Current: {periods.get('current', 'N/A')}
- Previous: {periods.get('previous', 'N/A')}

Trusted Advisor Issues Found (Total):
- Cost Optimization: {total_ta.get('cost_optimizing', 0)} issues
- Security: {total_ta.get('security', 0)} issues
- Performance: {total_ta.get('performance', 0)} issues
- Fault Tolerance: {total_ta.get('fault_tolerance', 0)} issues
- Service Limits: {total_ta.get('service_limits', 0)} warnings

AWS Health Events (Total):
- Scheduled: {total_health['scheduled']}
- Ongoing: {total_health['ongoing']}
- Notifications: {total_health['notifications']}"""
    )
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(f"=== AWS Health Analyzer Complete === Duration: {duration:.1f}s")
    
    return {'statusCode': 200, 'body': f'Health report sent ({len(accounts)} accounts)'}
