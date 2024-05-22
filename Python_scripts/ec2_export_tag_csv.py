# Import libiaries
import boto3
import csv
import os

# Define the mandatory tags
MANDATORY_TAGS = ["Env", "BizOwner", "Technology", "Project"]

# Initialize boto3 clients
ec2 = boto3.client('ec2')
s3 = boto3.client('s3')

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
                **{tag: tags.get(tag, '') for tag in MANDATORY_TAGS}
            }
            instances.append(instance_info)
    return instances

# write and loop each ec2 tag info, add MANDATORY_TAGS in fields
def export_to_csv(instances, filename='ec2_instances.csv'):
    fieldnames = ['InstanceId', 'DefaultName'] + MANDATORY_TAGS
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for instance in instances:
            writer.writerow(instance)

# Update CSV by adding biz input, then apply all tags 

#def update_tags_from_csv(filename='ec2_instances_updated.csv'):
#    with open(filename, newline='') as csvfile:
#        reader = csv.DictReader(csvfile)
#        for row in reader:
#            instance_id = row['InstanceId']
#            tags = [{'Key': tag, 'Value': row[tag]} for tag in MANDATORY_TAGS if row[tag]]
#            if tags:
#                ec2.create_tags(Resources=[instance_id], Tags=tags)

# skip the lambda function and config rule creation steps

#def create_lambda_function(): # skip lambda creation
#def create_config_rule(): # skip config rule creation

# print status
def main():
    instances = list_ec2_instances()
    export_to_csv(instances)
    print("CSV export complete. Please update the mandatory tags and save the file as 'ec2_instances_updated.csv'.")
#    input("Press Enter after updating the CSV file...")

#    update_tags_from_csv()
#    print("Tags updated successfully.")

if __name__ == '__main__':
    main()
