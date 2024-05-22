import boto3
import csv

# Define the mandatory tags
MANDATORY_TAGS = ["Env", "BizOwner", "Technology", "Project"]

# Initialize boto3 clients
ec2 = boto3.client('ec2')

def list_ec2_instances():
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

def export_to_csv(instances, filename='ec2_instances.csv'):
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

def main():
    instances = list_ec2_instances()
    export_to_csv(instances)
    print("CSV export complete. Please update the mandatory tags in 'ec2_instances.csv'.")

if __name__ == '__main__':
    main()

