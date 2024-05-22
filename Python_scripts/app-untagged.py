import boto3

def get_untagged_ec2_instances():
    ec2_client = boto3.client('ec2')
    response = ec2_client.describe_instances()
    
    untagged_instances = []
    
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            has_owner_tag = False
            if 'Tags' in instance:
                for tag in instance['Tags']:
                    if tag['Key'].lower() == 'owner':
                        has_owner_tag = True
                        break
            
            if not has_owner_tag:
                instance_id = instance['InstanceId']
                instance_state = instance['State']['Name']
                untagged_instances.append({'InstanceId': instance_id, 'State': instance_state})
    
    return untagged_instances

untagged_instances = get_untagged_ec2_instances()
print("Untagged Instances:", untagged_instances)

