import boto3
import csv
from botocore.exceptions import ProfileNotFound, ClientError

# List of AWS account profiles
AWS_PROFILES = ["aws_account_zackblog", "aws_account_joesite"]  # Add more profiles as needed

# IAM User details
PASSWORD = "P@ssw0rd123"
POLICY_ARN = "arn:aws:iam::aws:policy/AdministratorAccess"
CSV_FILE = "all_users.csv"

def read_users_from_csv(filename):
    users = []
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            users.append(row['Username'])
    return users

def create_iam_user(profile_name, user_name):
    session = boto3.Session(profile_name=profile_name)
    iam = session.client('iam')
    
    try:
        # Create IAM user
        iam.create_user(UserName=user_name)
        print(f"User {user_name} created in profile {profile_name}.")

        # Create login profile for console access
        iam.create_login_profile(
            UserName=user_name,
            Password=PASSWORD,
            PasswordResetRequired=False
        )
        print(f"Login profile created for user {user_name} in profile {profile_name}.")

        # Attach AdministratorAccess policy
        iam.attach_user_policy(
            UserName=user_name,
            PolicyArn=POLICY_ARN
        )
        print(f"AdministratorAccess policy attached to user {user_name} in profile {profile_name}.")

    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"User {user_name} already exists in profile {profile_name}.")
        else:
            print(f"Error creating user {user_name} in profile {profile_name}: {e}")

def process_all_profiles(users):
    for profile in AWS_PROFILES:
        try:
            print(f"Processing profile: {profile}")
            for user in users:
                create_iam_user(profile, user)
        except ProfileNotFound:
            print(f"Profile {profile} not found. Skipping.")

if __name__ == '__main__':
    users = read_users_from_csv(CSV_FILE)
    process_all_profiles(users)

