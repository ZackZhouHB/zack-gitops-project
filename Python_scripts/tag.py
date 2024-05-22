import boto3
import csv

def get_ec2_instances(region):
    ec2 = boto3.client('ec2', region_name=region)
    response = ec2.describe_instances()
    instances = []

    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            tags = instance.get('Tags', [])
            instance_info = {'InstanceId': instance_id, 'Tags': tags}
            instances.append(instance_info)

    return instances

def write_to_csv(instances, filename):
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['InstanceId', 'TagKey', 'TagValue'])

        for instance in instances:
            instance_id = instance['InstanceId']
            tags = instance['Tags']
            if tags:
                for tag in tags:
                    writer.writerow([instance_id, tag['Key'], tag['Value']])
            else:
                writer.writerow([instance_id, '', ''])

if __name__ == "__main__":
    region = 'ap-southeast-2'  # Change to your desired AWS region
    filename = 'ec2_tags.csv'

    instances = get_ec2_instances(region)
    write_to_csv(instances, filename)

    print(f"EC2 instance IDs and tags have been exported to {filename}")

