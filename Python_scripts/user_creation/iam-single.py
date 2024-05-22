import boto3
from botocore.exceptions import ProfileNotFound, ClientError

# List of AWS account profiles
AWS_PROFILES = ["aws_account_zackblog", "aws_account_joesite"]  # Add more profiles as needed

# IAM User details
USER_NAME = "infra_team_user"
PASSWORD = "P@ssw0rd123"
POLICY_ARN = "arn:aws:iam::aws:policy/AdministratorAccess"

def create_iam_user(profile_name):
    session = boto3.Session(profile_name=profile_name)
    iam = session.client('iam')
    
    try:
        # Create IAM user
        iam.create_user(UserName=USER_NAME)
        print(f"User {USER_NAME} created in profile {profile_name}.")

        # Create login profile for console access
        iam.create_login_profile(
            UserName=USER_NAME,
            Password=PASSWORD,
            PasswordResetRequired=False
        )
        print(f"Login profile created for user {USER_NAME} in profile {profile_name}.")

        # Attach AdministratorAccess policy
        iam.attach_user_policy(
            UserName=USER_NAME,
            PolicyArn=POLICY_ARN
        )
        print(f"AdministratorAccess policy attached to user {USER_NAME} in profile {profile_name}.")

    except ClientError as e:
        if e.response['Error']['Code'] == 'EntityAlreadyExists':
            print(f"User {USER_NAME} already exists in profile {profile_name}.")
        else:
            print(f"Error creating user {USER_NAME} in profile {profile_name}: {e}")

def process_all_profiles():
    for profile in AWS_PROFILES:
        try:
            print(f"Processing profile: {profile}")
            create_iam_user(profile)
        except ProfileNotFound:
            print(f"Profile {profile} not found. Skipping.")

if __name__ == '__main__':
    process_all_profiles()

