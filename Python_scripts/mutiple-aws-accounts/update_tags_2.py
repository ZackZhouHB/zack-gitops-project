import boto3
import csv
from botocore.exceptions import ProfileNotFound

# Define the mandatory tags
MANDATORY_TAGS = ["Env", "BizOwner", "Technology", "Project"]

# List of AWS account profiles
AWS_PROFILES = ["aws_account_zackblog", "aws_account_joesite"]  # Add more profiles as needed

def update_tags_from_csv(profile_name):
    filename = f"ec2_instances_updated_{profile_name}.csv"
    session = boto3.Session(profile_name=profile_name)
    ec2 = session.client('ec2')
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            instance_id = row['InstanceId']
            tags = [{'Key': tag, 'Value': row[tag]} for tag in MANDATORY_TAGS if row[tag]]
            if tags:
                ec2.create_tags(Resources=[instance_id], Tags=tags)

def process_all_profiles():
    for profile in AWS_PROFILES:
        try:
            print(f"Processing profile: {profile}")
            update_tags_from_csv(profile)
            print(f"Tags updated successfully from 'ec2_instances_updated_{profile}.csv' for profile {profile}.")
        except ProfileNotFound:
            print(f"Profile {profile} not found. Skipping.")
        except FileNotFoundError:
            print(f"Updated CSV file for profile {profile} not found. Skipping.")

if __name__ == '__main__':
    process_all_profiles()

