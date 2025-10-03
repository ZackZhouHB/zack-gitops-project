#!/usr/bin/env python3

import boto3
import csv
import os
import configparser
import argparse
from botocore.exceptions import ClientError, ProfileNotFound

def get_aws_profiles():
    """Get all SSO AWS profiles from ~/.aws/config (excluding personal profiles)"""
    profiles = []
    config_path = os.path.expanduser('~/.aws/config')
    
    if not os.path.exists(config_path):
        print(f"AWS config file not found at: {config_path}")
        return profiles
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    # Personal profiles to exclude
    personal_profiles = ['default', 'zack']
    
    for section in config.sections():
        if section.startswith('profile '):
            profile_name = section.split(' ', 1)[1]
            # Only include SSO profiles (exclude personal profiles)
            if profile_name not in personal_profiles and config.has_option(section, 'sso_session'):
                profiles.append(profile_name)
    
    return profiles

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

def process_account(profile_name, aws_region, csv_writer):
    """Process a single AWS account"""
    print(f"\n{'='*80}")
    print(f"Processing AWS Profile: {profile_name}")
    print(f"{'='*80}")
    
    try:
        # Create AWS session
        session = boto3.Session(profile_name=profile_name, region_name=aws_region)
        ec2_client = session.client('ec2')
        ssm_client = session.client('ssm')
        
        # Get all instances
        instances = get_all_instances(ec2_client)
        print(f"Found {len(instances)} EC2 instances")
        
        # Process each instance
        for instance in instances:
            instance_id = instance['InstanceId']
            instance_state = instance['State']['Name']
            print(f"Processing instance: {instance_id} (State: {instance_state})")
            
            # Get instance details
            instance_name = get_instance_name(ec2_client, instance_id)
            ip_address = instance.get('PrivateIpAddress', 'N/A')
            
            # Get SSM information
            ssm_info = get_ssm_info(ssm_client, instance_id)
            
            # Write to CSV
            csv_writer.writerow({
                'AWS Profile': profile_name,
                'Instance ID': instance_id,
                'Instance Name': instance_name,
                'IP Address': ip_address,
                'Instance Status': instance_state,
                'OS Type': f"{ssm_info['os_type']} {ssm_info['os_version']}",
                'Platform': ssm_info['platform_type'],
                'SSM Agent Status': ssm_info['ssm_status']
            })
            
            print(f"  Name: {instance_name}")
            print(f"  IP: {ip_address}")
            print(f"  Status: {instance_state}")
            print(f"  OS: {ssm_info['os_type']} {ssm_info['os_version']} ({ssm_info['platform_type']})")
            print(f"  SSM Status: {ssm_info['ssm_status']}")
        
        return True
    except ProfileNotFound:
        print(f"AWS profile '{profile_name}' not found. Skipping.")
        return False
    except Exception as e:
        print(f"Error processing account with profile '{profile_name}': {e}")
        return False

def main():
    """Main function to generate EC2 inventory across all AWS accounts"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate EC2 inventory across all AWS accounts')
    parser.add_argument('--region', default='ap-southeast-2', help='AWS region to use')
    parser.add_argument('--output', default='ec2_inventory.csv', help='Output CSV file name')
    parser.add_argument('--profiles', nargs='+', help='Specific AWS profiles to check (default: all profiles)')
    parser.add_argument('--exclude', nargs='+', help='AWS profiles to exclude')
    args = parser.parse_args()
    
    # Set AWS region and output file
    aws_region = args.region
    output_file = args.output
    
    print(f"Starting EC2 inventory generation across all AWS accounts")
    print(f"AWS Region: {aws_region}")
    print(f"Output file: {output_file}")
    
    # Get all AWS profiles
    all_profiles = get_aws_profiles()
    
    # Filter profiles if specified
    if args.profiles:
        profiles = [p for p in args.profiles if p in all_profiles]
        print(f"Checking specific profiles: {', '.join(profiles)}")
    else:
        profiles = all_profiles
        print(f"Found {len(profiles)} SSO company profiles (excluding personal profiles)")
    
    # Exclude profiles if specified
    if args.exclude:
        profiles = [p for p in profiles if p not in args.exclude]
        print(f"Excluding profiles: {', '.join(args.exclude)}")
    
    print(f"Will process {len(profiles)} profiles: {', '.join(profiles[:5])}{'...' if len(profiles) > 5 else ''}")
    
    # Prepare CSV file
    with open(output_file, 'w', newline='') as csvfile:
        fieldnames = [
            'AWS Profile',
            'Instance ID', 
            'Instance Name', 
            'IP Address',
            'Instance Status',
            'OS Type',
            'Platform',
            'SSM Agent Status'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        # Process each AWS profile
        successful_profiles = 0
        for profile in profiles:
            if process_account(profile, aws_region, writer):
                successful_profiles += 1
    
    print(f"\nProcessed {successful_profiles} out of {len(profiles)} AWS profiles")
    print(f"EC2 inventory report generated: {output_file}")

if __name__ == "__main__":
    main()
