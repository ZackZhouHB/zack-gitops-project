import boto3
import csv

# Define the mandatory tags
MANDATORY_TAGS = ["Env", "BizOwner", "Technology", "Project"]

def update_tags_from_csv(filename='ec2_instances_updated.csv'):
    ec2 = boto3.client('ec2')
    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            instance_id = row['InstanceId']
            tags = [{'Key': tag, 'Value': row[tag]} for tag in MANDATORY_TAGS if row[tag]]
            if tags:
                ec2.create_tags(Resources=[instance_id], Tags=tags)

def main():
    update_tags_from_csv()
    print("Tags updated successfully from 'ec2_instances_updated.csv'.")

if __name__ == '__main__':
    main()

