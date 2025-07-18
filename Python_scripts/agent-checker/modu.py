#!/usr/bin/env python3

import boto3
import json
import time
import csv
import os
import configparser
import argparse
from botocore.exceptions import ClientError, ProfileNotFound
from abc import ABC, abstractmethod

# Global settings for timeouts and retries
BASE_TIMEOUT = 15  # Base timeout in seconds
MAX_RETRIES = 3    # Maximum number of retries

class AgentChecker(ABC):
    """Abstract base class for agent checkers"""
    
    @abstractmethod
    def get_agent_name(self):
        """Return the name of the agent being checked"""
        pass
    
    @abstractmethod
    def get_linux_check_script(self):
        """Return the shell script for checking the agent on Linux"""
        pass
    
    @abstractmethod
    def get_windows_check_script(self):
        """Return the PowerShell script for checking the agent on Windows"""
        pass
    
    @abstractmethod
    def get_default_output_filename(self):
        """Return the default output filename for this agent"""
        pass

class AirlockChecker(AgentChecker):
    """Airlock agent checker implementation"""
    
    def get_agent_name(self):
        return "Airlock"
    
    def get_default_output_filename(self):
        return "all_accounts_airlock_status.csv"
    
    def get_linux_check_script(self):
        return """#!/bin/bash

# Default values
AGENT_STATUS="Not Found"
AGENT_VERSION="N/A"
SERVICE_STATUS="Not Running"

# Check for Debian/Ubuntu (dpkg)
if command -v dpkg &> /dev/null; then
    # Check for airlock-enforcement-agent
    if dpkg -l | grep -q airlock-enforcement-agent; then
        AGENT_STATUS="Installed"
        AGENT_VERSION=$(dpkg -l | grep airlock-enforcement-agent | awk '{print $3}')
        
        # Check service status
        if systemctl is-active --quiet airlock-client.service; then
            SERVICE_STATUS="Running"
        else
            SERVICE_STATUS="Installed but Not Running"
        fi
    # Also check for just airlock
    elif dpkg -s airlock &> /dev/null; then
        AGENT_STATUS="Installed"
        AGENT_VERSION=$(dpkg -s airlock | grep 'Version:' | awk '{print $2}')
        
        # Check service status
        if systemctl is-active --quiet airlock-client.service; then
            SERVICE_STATUS="Running"
        else
            SERVICE_STATUS="Installed but Not Running"
        fi
    fi

# Check for Red Hat/CentOS/Amazon Linux (rpm)
elif command -v rpm &> /dev/null; then
    # Check for airlock-enforcement-agent
    if rpm -q airlock-enforcement-agent &> /dev/null; then
        AGENT_STATUS="Installed"
        AGENT_VERSION=$(rpm -q --queryformat '%{VERSION}' airlock-enforcement-agent)
        
        # Check service status
        if systemctl is-active --quiet airlock-client.service; then
            SERVICE_STATUS="Running"
        else
            SERVICE_STATUS="Installed but Not Running"
        fi
    # Also check for just airlock
    elif rpm -q airlock &> /dev/null; then
        AGENT_STATUS="Installed"
        AGENT_VERSION=$(rpm -q --queryformat '%{VERSION}' airlock)
        
        # Check service status
        if systemctl is-active --quiet airlock-client.service; then
            SERVICE_STATUS="Running"
        else
            SERVICE_STATUS="Installed but Not Running"
        fi
    fi
fi

# Output in a structured format (e.g., JSON) for easy parsing
echo "{\\\"status\\\": \\\"$AGENT_STATUS\\\", \\\"version\\\": \\\"$AGENT_VERSION\\\", \\\"service\\\": \\\"$SERVICE_STATUS\\\"}"
"""
    
    def get_windows_check_script(self):
        return """
# Default values
$agentInstalled = "Not Found"
$agentVersion = "N/A"
$agentStatus = "Not Running"

# Check for Airlock using Get-Package (more reliable than registry checks)
try {
    $agentPackage = Get-Package -Name "*Airlock*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($agentPackage) {
        $agentInstalled = "Installed"
        $agentVersion = $agentPackage.Version
    }
} catch {
    Write-Host "Error checking for Airlock package: $_"
}

# Check service status using Get-Service
try {
    $agentService = Get-Service -Name "*airlock*" -ErrorAction SilentlyContinue
    if (-not $agentService) {
        # Try alternative service name
        $agentService = Get-Service -Name "*AirlockClient*" -ErrorAction SilentlyContinue
    }
    
    if ($agentService) {
        if ($agentService.Status -eq "Running") {
            $agentStatus = "Running"
        } else {
            $agentStatus = "Installed but Not Running"
        }
    }
} catch {
    Write-Host "Error checking for Airlock service: $_"
}

# Create result object
$result = @{
    status = $agentInstalled
    version = $agentVersion
    service = $agentStatus
}

# Convert to JSON and output
$result | ConvertTo-Json
"""

class DynatraceChecker(AgentChecker):
    """Dynatrace OneAgent checker implementation"""
    
    def get_agent_name(self):
        return "Dynatrace OneAgent"
    
    def get_default_output_filename(self):
        return "all_accounts_dynatrace_status.csv"
    
    def get_linux_check_script(self):
        return """#!/bin/bash

# Default values
AGENT_STATUS="Not Found"
AGENT_VERSION="N/A"
SERVICE_STATUS="Not Running"

# Check for Dynatrace OneAgent installation
if [ -d "/opt/dynatrace/oneagent" ]; then
    AGENT_STATUS="Installed"
    
    # Get version from installer.version file
    if [ -f "/opt/dynatrace/oneagent/agent/installer.version" ]; then
        AGENT_VERSION=$(cat /opt/dynatrace/oneagent/agent/installer.version)
    fi
    
    # Check service status
    if systemctl is-active --quiet oneagent.service; then
        SERVICE_STATUS="Running"
    elif systemctl is-active --quiet oneagent; then
        SERVICE_STATUS="Running"
    else
        SERVICE_STATUS="Installed but Not Running"
    fi
    
# Also check for package managers
elif command -v dpkg &> /dev/null; then
    # Check for Debian/Ubuntu (dpkg)
    if dpkg -l | grep -q oneagent; then
        AGENT_STATUS="Installed"
        AGENT_VERSION=$(dpkg -l | grep oneagent | awk '{print $3}')
        
        # Check service status
        if systemctl is-active --quiet oneagent.service; then
            SERVICE_STATUS="Running"
        else
            SERVICE_STATUS="Installed but Not Running"
        fi
    fi
elif command -v rpm &> /dev/null; then
    # Check for Red Hat/CentOS/Amazon Linux (rpm)
    if rpm -q oneagent &> /dev/null; then
        AGENT_STATUS="Installed"
        AGENT_VERSION=$(rpm -q --queryformat '%{VERSION}' oneagent)
        
        # Check service status
        if systemctl is-active --quiet oneagent.service; then
            SERVICE_STATUS="Running"
        else
            SERVICE_STATUS="Installed but Not Running"
        fi
    fi
fi

# Output in a structured format (e.g., JSON) for easy parsing
echo "{\\\"status\\\": \\\"$AGENT_STATUS\\\", \\\"version\\\": \\\"$AGENT_VERSION\\\", \\\"service\\\": \\\"$SERVICE_STATUS\\\"}"
"""
    
    def get_windows_check_script(self):
        return """
# Default values
$agentInstalled = "Not Found"
$agentVersion = "N/A"
$agentStatus = "Not Running"

# Check for Dynatrace OneAgent using Get-Package
try {
    $agentPackage = Get-Package -Name "*Dynatrace*" -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($agentPackage) {
        $agentInstalled = "Installed"
        $agentVersion = $agentPackage.Version
    }
} catch {
    Write-Host "Error checking for Dynatrace package: $_"
}

# Check service status using Get-Service
try {
    $agentService = Get-Service -Name "*Dynatrace*" -ErrorAction SilentlyContinue
    if (-not $agentService) {
        # Try alternative service name
        $agentService = Get-Service -Name "*oneagent*" -ErrorAction SilentlyContinue
    }
    
    if ($agentService) {
        if ($agentService.Status -eq "Running") {
            $agentStatus = "Running"
        } else {
            $agentStatus = "Installed but Not Running"
        }
    }
} catch {
    Write-Host "Error checking for Dynatrace service: $_"
}

# Create result object
$result = @{
    status = $agentInstalled
    version = $agentVersion
    service = $agentStatus
}

# Convert to JSON and output
$result | ConvertTo-Json
"""

# Available agent checkers
AVAILABLE_AGENTS = {
    'airlock': AirlockChecker(),
    'dynatrace': DynatraceChecker()
}

def get_aws_profiles():
    """Get all AWS profiles from ~/.aws/config"""
    profiles = []
    config_path = os.path.expanduser('~/.aws/config')
    
    if not os.path.exists(config_path):
        print(f"AWS config file not found at: {config_path}")
        return profiles
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    for section in config.sections():
        if section == 'default':
            profiles.append('default')
        elif section.startswith('profile '):
            profiles.append(section.split(' ', 1)[1])
    
    return profiles

def get_account_info(session):
    """Get AWS account ID and name"""
    try:
        sts_client = session.client('sts')
        account_id = sts_client.get_caller_identity()['Account']
        
        try:
            org_client = session.client('organizations')
            account_name = org_client.describe_account(AccountId=account_id)['Account']['Name']
        except (ClientError, KeyError):
            account_name = f"Account {account_id}"
    except Exception as e:
        print(f"Error getting account info: {e}")
        account_id = "Unknown"
        account_name = "Unknown"
    
    return account_id, account_name

def get_instance_name(ec2_client, instance_id):
    """Get instance name from tags"""
    try:
        response = ec2_client.describe_tags(
            Filters=[
                {'Name': 'resource-id', 'Values': [instance_id]},
                {'Name': 'key', 'Values': ['Name']}
            ]
        )
        for tag in response.get('Tags', []):
            if tag['Key'] == 'Name':
                return tag['Value']
    except Exception as e:
        print(f"Error getting name for {instance_id}: {e}")
    
    return instance_id

def get_all_instances(ec2_client):
    """Get all EC2 instances in the account"""
    instances = []
    try:
        paginator = ec2_client.get_paginator('describe_instances')
        
        for page in paginator.paginate():
            for reservation in page['Reservations']:
                for instance in reservation['Instances']:
                    instances.append(instance)
    except Exception as e:
        print(f"Error getting instances: {e}")
    
    return instances

def get_ssm_info(ssm_client, instance_id):
    """Get SSM agent status and OS information"""
    try:
        response = ssm_client.describe_instance_information(
            Filters=[{'Key': 'InstanceIds', 'Values': [instance_id]}]
        )
        
        if response['InstanceInformationList']:
            info = response['InstanceInformationList'][0]
            return {
                'ssm_status': info.get('PingStatus', 'Unknown'),
                'os_type': info.get('PlatformName', 'Unknown'),
                'os_version': info.get('PlatformVersion', 'Unknown'),
                'platform_type': info.get('PlatformType', 'Unknown')
            }
    except Exception as e:
        print(f"Error getting SSM info for {instance_id}: {e}")
    
    return {
        'ssm_status': 'Not Available',
        'os_type': 'Unknown',
        'os_version': 'Unknown',
        'platform_type': 'Unknown'
    }

def check_linux_agent_status(ssm_client, instance_id, agent_checker):
    """Check agent status on Linux instance"""
    # Default values
    agent_info = {
        'installed': 'No',
        'version': 'N/A',
        'status': 'Not Running'
    }
    
    script = agent_checker.get_linux_check_script()
    
    try:
        # Send command to the instance
        response = ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunShellScript',
            Parameters={'commands': [script]}
        )
        
        command_id = response['Command']['CommandId']
        
        # Wait for command to complete - using original timeout of 3 seconds for Linux
        time.sleep(3)
        
        # Get command result
        result = ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )
        
        if result['Status'] == 'Success':
            try:
                output = json.loads(result['StandardOutputContent'])
                agent_info = {
                    'installed': output.get('status', 'No'),
                    'version': output.get('version', 'N/A'),
                    'status': output.get('service', 'Not Running')
                }
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  Error parsing output for {instance_id}: {e}")
                if result['StandardOutputContent']:
                    print(f"  Raw output: {result['StandardOutputContent'][:100]}...")
        elif result['Status'] == 'InProgress':
            print(f"  Command still in progress for Linux instance {instance_id}. Unusual delay.")
            agent_info = {
                'installed': 'Unknown',
                'version': 'Timeout',
                'status': 'Check Timed Out'
            }
        else:
            print(f"  Command failed for {instance_id}: {result.get('Status')}")
            if 'StandardErrorContent' in result and result['StandardErrorContent']:
                print(f"  Error details: {result['StandardErrorContent'][:100]}...")
    
    except Exception as e:
        print(f"  Error checking {agent_checker.get_agent_name()} status for {instance_id}: {e}")
    
    return agent_info

def check_windows_agent_status(ssm_client, instance_id, agent_checker):
    """Check agent status on Windows instance"""
    # Default values
    agent_info = {
        'installed': 'No',
        'version': 'N/A',
        'status': 'Not Running'
    }
    
    script = agent_checker.get_windows_check_script()
    
    try:
        # Send command to the instance
        response = ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName='AWS-RunPowerShellScript',
            Parameters={'commands': [script]}
        )
        
        command_id = response['Command']['CommandId']
        
        # Wait for command to complete with multiple retries
        for attempt in range(MAX_RETRIES):
            # Exponential backoff
            wait_time = BASE_TIMEOUT * (2 ** attempt)
            time.sleep(wait_time)
            
            # Get command result
            result = ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
            
            if result['Status'] in ['Success', 'Failed', 'Cancelled']:
                break
            
            print(f"  Command still in progress for {instance_id}. Retry {attempt+1}/{MAX_RETRIES}...")
        
        if result['Status'] == 'Success':
            try:
                output = json.loads(result['StandardOutputContent'])
                agent_info = {
                    'installed': output.get('status', 'No'),
                    'version': output.get('version', 'N/A'),
                    'status': output.get('service', 'Not Running')
                }
            except (json.JSONDecodeError, KeyError) as e:
                print(f"  Error parsing output for {instance_id}: {e}")
                if result['StandardOutputContent']:
                    print(f"  Raw output: {result['StandardOutputContent'][:100]}...")
        elif result['Status'] == 'InProgress':
            print(f"  Command timed out for {instance_id} after {MAX_RETRIES} retries.")
            agent_info = {
                'installed': 'Unknown',
                'version': 'Timeout',
                'status': 'Check Timed Out'
            }
        else:
            print(f"  Command failed for {instance_id}: {result.get('Status')}")
            if 'StandardErrorContent' in result and result['StandardErrorContent']:
                print(f"  Error details: {result['StandardErrorContent'][:100]}...")
    
    except Exception as e:
        print(f"  Error checking {agent_checker.get_agent_name()} status for {instance_id}: {e}")
    
    return agent_info

def check_agent_status(ssm_client, instance_id, platform_type, agent_checker):
    """Check agent status based on platform type"""
    if platform_type.lower() == 'windows':
        print(f"  Detected Windows instance. Using PowerShell to check {agent_checker.get_agent_name()} status...")
        agent_info = check_windows_agent_status(ssm_client, instance_id, agent_checker)
        # Ensure we have the right keys for consistency
        return {
            'installed': agent_info.get('installed', 'No'),
            'version': agent_info.get('version', 'N/A'),
            'status': agent_info.get('status', agent_info.get('service', 'Not Running'))
        }
    else:
        print(f"  Detected Linux instance. Using Shell script to check {agent_checker.get_agent_name()} status...")
        return check_linux_agent_status(ssm_client, instance_id, agent_checker)

def process_account(profile_name, aws_region, csv_writer, agent_checker):
    """Process a single AWS account"""
    print(f"\n{'='*80}")
    print(f"Processing AWS Profile: {profile_name}")
    print(f"{'='*80}")
    
    try:
        # Create AWS session
        session = boto3.Session(profile_name=profile_name, region_name=aws_region)
        ec2_client = session.client('ec2')
        ssm_client = session.client('ssm')
        
        # Get account information
        account_id, account_name = get_account_info(session)
        print(f"Account: {account_name}")
        
        # Get all instances
        instances = get_all_instances(ec2_client)
        print(f"Found {len(instances)} EC2 instances")
        
        # Process each instance
        for instance in instances:
            instance_id = instance['InstanceId']
            instance_state = instance['State']['Name']
            print(f"\nProcessing instance: {instance_id} (State: {instance_state})")
            
            # Get instance details
            instance_name = get_instance_name(ec2_client, instance_id)
            ip_address = instance.get('PrivateIpAddress', 'N/A')
            
            # Get SSM information
            ssm_info = get_ssm_info(ssm_client, instance_id)
            platform_type = ssm_info['platform_type']
            
            # Check agent status if instance is running and SSM agent is online
            agent_info = {'installed': 'No', 'version': 'N/A', 'status': 'Not Running'}
            if instance_state == 'running' and ssm_info['ssm_status'] == 'Online':
                agent_info = check_agent_status(ssm_client, instance_id, platform_type, agent_checker)
            elif instance_state != 'running':
                print(f"  Instance is not running. Skipping {agent_checker.get_agent_name()} check.")
            
            # Write to CSV
            csv_writer.writerow({
                'AWS Account': account_name,
                'AWS Profile': profile_name,
                'Instance ID': instance_id,
                'Instance Name': instance_name,
                'IP Address': ip_address,
                'Instance Status': instance_state,
                'OS Type': f"{ssm_info['os_type']} {ssm_info['os_version']}",
                'Platform': platform_type,
                'SSM Agent Status': ssm_info['ssm_status'],
                f'{agent_checker.get_agent_name()} Installed': agent_info.get('installed', 'No'),
                f'{agent_checker.get_agent_name()} Version': agent_info.get('version', 'N/A'),
                f'{agent_checker.get_agent_name()} Status': agent_info.get('status', 'Not Running')
            })
            
            print(f"  Name: {instance_name}")
            print(f"  IP: {ip_address}")
            print(f"  Status: {instance_state}")
            print(f"  OS: {ssm_info['os_type']} {ssm_info['os_version']} ({platform_type})")
            print(f"  SSM Status: {ssm_info['ssm_status']}")
            print(f"  {agent_checker.get_agent_name()}: {agent_info.get('installed', 'No')} (Version: {agent_info.get('version', 'N/A')}, Status: {agent_info.get('status', 'Not Running')})")
        
        return True
    except ProfileNotFound:
        print(f"AWS profile '{profile_name}' not found. Skipping.")
        return False
    except Exception as e:
        print(f"Error processing account with profile '{profile_name}': {e}")
        return False

def main():
    """Main function to check agent status across all AWS accounts"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Check agent status across all AWS accounts')
    parser.add_argument('--agent', choices=list(AVAILABLE_AGENTS.keys()), default='airlock', 
                       help='Agent to check (default: airlock)')
    parser.add_argument('--region', default='ap-southeast-2', help='AWS region to use')
    parser.add_argument('--output', help='Output CSV file name (default: auto-generated based on agent)')
    parser.add_argument('--profiles', nargs='+', help='Specific AWS profiles to check (default: all profiles)')
    parser.add_argument('--exclude', nargs='+', help='AWS profiles to exclude')
    parser.add_argument('--timeout', type=int, default=15, help='Base timeout in seconds for Windows SSM commands (default: 15)')
    parser.add_argument('--retries', type=int, default=3, help='Number of retries for Windows SSM commands (default: 3)')
    args = parser.parse_args()
    
    # Get the agent checker
    agent_checker = AVAILABLE_AGENTS[args.agent]
    
    # Set AWS region and output file
    aws_region = args.region
    output_file = args.output or agent_checker.get_default_output_filename()
    
    # Set global timeout and retry settings
    global BASE_TIMEOUT, MAX_RETRIES
    BASE_TIMEOUT = args.timeout
    MAX_RETRIES = args.retries
    
    print(f"Starting {agent_checker.get_agent_name()} status check across all AWS accounts")
    print(f"AWS Region: {aws_region}")
    print(f"Output file: {output_file}")
    print(f"Windows command timeout: {BASE_TIMEOUT}s with {MAX_RETRIES} retries")
    
    # Get all AWS profiles
    all_profiles = get_aws_profiles()
    
    # Filter profiles if specified
    if args.profiles:
        profiles = [p for p in args.profiles if p in all_profiles]
        print(f"Checking specific profiles: {', '.join(profiles)}")
    else:
        profiles = all_profiles
        print(f"Found {len(profiles)} AWS profiles")
    
    # Exclude profiles if specified
    if args.exclude:
        profiles = [p for p in profiles if p not in args.exclude]
        print(f"Excluding profiles: {', '.join(args.exclude)}")
    
    # Prepare CSV file
    with open(output_file, 'w', newline='') as csvfile:
        agent_name = agent_checker.get_agent_name()
        fieldnames = [
            'AWS Account',
            'AWS Profile',
            'Instance ID', 
            'Instance Name', 
            'IP Address',
            'Instance Status',
            'OS Type',
            'Platform',
            'SSM Agent Status', 
            f'{agent_name} Installed', 
            f'{agent_name} Version', 
            f'{agent_name} Status'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Process each AWS profile
        successful_profiles = 0
        for profile in profiles:
            if process_account(profile, aws_region, writer, agent_checker):
                successful_profiles += 1
    
    print(f"\nProcessed {successful_profiles} out of {len(profiles)} AWS profiles")
    print(f"Report generated: {output_file}")

if __name__ == "__main__":
    main()