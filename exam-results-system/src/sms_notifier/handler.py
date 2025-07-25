import os
import boto3
import json
from botocore.exceptions import ClientError

# Import shared utilities

from common.dynamodb_status import DynamoDBStatusManager

sns = boto3.client('sns')
status_manager = DynamoDBStatusManager()

def handler(event, context):
    """
    Processes SQS messages and sends result SMS via SNS.
    """
    for record in event['Records']:
        student_data = json.loads(record['body'])
        student_id = student_data['student_id']
        phone_number = student_data['phone']
        
        message = f"HSC Results: Dear student {student_id}, your results are: {student_data['results']}"
        
        try:
            sns.publish(
                PhoneNumber=phone_number,
                Message=message
            )
            print(f"Successfully sent SMS to {student_id}")
            
            # Update DynamoDB with successful delivery status
            status_manager.update_sms_status(student_id, 'sent')
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            print(f"Failed to send SMS to {student_id}: {error_message}")
            
            # Update DynamoDB with failed delivery status
            status_manager.update_sms_status(student_id, 'failed', error_message)
            
            # Re-raise to trigger SQS retry
            raise e
    return {'status': 'completed'}