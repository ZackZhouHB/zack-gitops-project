import boto3

def list_ec2_instances():
    # Create a session using default AWS profile
    session = boto3.Session()
    # Create an EC2 client
    ec2_client = session.client('ec2')

    # Describe EC2 instances
    response = ec2_client.describe_instances()

    # Iterate over the instances
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            # Get the instance ID
            instance_id = instance['InstanceId']
            
            # Get the instance state
            instance_state = instance['State']['Name']
            
            # Get the instance Name tag if exists
            instance_name = 'No Name'
            if 'Tags' in instance:
                for tag in instance['Tags']:
                    if tag['Key'] == 'Name':
                        instance_name = tag['Value']
                        break
            
            # Print instance ID, Name, and State
            print(f"Instance ID: {instance_id}, Name: {instance_name}, State: {instance_state}")

if __name__ == "__main__":
    list_ec2_instances()
