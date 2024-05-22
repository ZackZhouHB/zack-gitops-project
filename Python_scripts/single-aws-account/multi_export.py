import boto3
import csv
from botocore.exceptions import ProfileNotFound

# Define the mandatory tags
MANDATORY_TAGS = ["Env", "BizOwner", "Technology", "Project"]

# List of AWS account profiles
AWS_PROFILES = ["aws_account_zackblog", "aws_account_joesite"]  # Add more profiles as needed

def list_ec2_instances(profile_name):
    session = boto3.Session(profile_name=profile_name)
    ec2 = session.client('ec2')
    instances = []
    response = ec2.describe_instances()
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            default_name = next((tag['Value'] for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), 'No Name')
            tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
            instance_info = {
                'InstanceId': instance_id,
                'DefaultName': default_name,
                **tags
            }
            # Ensure mandatory tags are included with empty values if not present
            for mandatory_tag in MANDATORY_TAGS:
                if mandatory_tag not in instance_info:
                    instance_info[mandatory_tag] = ''
            instances.append(instance_info)
    return instances

def export_to_csv(instances, profile_name):
    filename = f"ec2_instances_{profile_name}.csv"
    # Collect all possible tag keys
    all_tags = set()
    for instance in instances:
        all_tags.update(instance.keys())
    
    # Ensure mandatory tags are included in the header
    all_tags.update(MANDATORY_TAGS)
    fieldnames = ['InstanceId', 'DefaultName'] + sorted(all_tags - {'InstanceId', 'DefaultName'})
    
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for instance in instances:
            writer.writerow(instance)

def process_all_profiles():
    for profile in AWS_PROFILES:
        try:
            print(f"Processing profile: {profile}")
            instances = list_ec2_instances(profile)
            export_to_csv(instances, profile)
            print(f"CSV export complete for profile {profile}. Please update the mandatory tags in 'ec2_instances_{profile}.csv'.")
        except ProfileNotFound:
            print(f"Profile {profile} not found. Skipping.")

if __name__ == '__main__':
    process_all_profiles()

