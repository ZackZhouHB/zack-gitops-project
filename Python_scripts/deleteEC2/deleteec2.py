import boto3
import csv

# Initialize boto3 clients
ec2_client = boto3.client('ec2')

def read_instance_ids_from_csv(file_path):
    instance_ids = []
    with open(file_path, mode='r', encoding='utf-8-sig') as file:  # Use utf-8-sig to handle BOM
        csv_reader = csv.reader(file)
        for row in csv_reader:
            instance_ids.append(row[0].strip())  # Strip any surrounding whitespace or invisible characters
    return instance_ids

def detach_and_delete_volumes(instance_id):
    volumes = ec2_client.describe_volumes(Filters=[
        {'Name': 'attachment.instance-id', 'Values': [instance_id]}
    ])['Volumes']

    for volume in volumes:
        for attachment in volume['Attachments']:
            if not attachment['DeleteOnTermination']:  # Safely check if DeleteOnTermination is False
                ec2_client.detach_volume(VolumeId=volume['VolumeId'])
                ec2_client.get_waiter('volume_available').wait(VolumeIds=[volume['VolumeId']])
                ec2_client.delete_volume(VolumeId=volume['VolumeId'])
                print(f"Detached and deleted volume {volume['VolumeId']} for instance {instance_id}")

def disassociate_and_release_eip(instance_id):
    addresses = ec2_client.describe_addresses(Filters=[
        {'Name': 'instance-id', 'Values': [instance_id]}
    ])['Addresses']

    for address in addresses:
        ec2_client.disassociate_address(AssociationId=address['AssociationId'])
        ec2_client.release_address(AllocationId=address['AllocationId'])
        print(f"Disassociated and released Elastic IP {address['PublicIp']} for instance {instance_id}")

def terminate_instance(instance_id):
    ec2_client.terminate_instances(InstanceIds=[instance_id])
    print(f"Terminated instance {instance_id}")

def main(csv_file_path):
    instance_ids = read_instance_ids_from_csv(csv_file_path)
    for instance_id in instance_ids:
        try:
            print(f"Processing instance {instance_id}")
            detach_and_delete_volumes(instance_id)
            disassociate_and_release_eip(instance_id)
            terminate_instance(instance_id)
        except Exception as e:
            print(f"An error occurred processing instance {instance_id}: {e}")

if __name__ == "__main__":
    csv_file_path = 'instances_to_terminate.csv'
    main(csv_file_path)

