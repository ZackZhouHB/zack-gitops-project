import os
import boto3
import json
from datetime import datetime

# Import shared utilities

from common.dynamodb_status import DynamoDBStatusManager

dynamodb = boto3.resource('dynamodb')
sqs = boto3.client('sqs')

RESULTS_TABLE_NAME = os.environ['RESULTS_TABLE_NAME']
EMAIL_QUEUE_URL = os.environ['EMAIL_QUEUE_URL']
SMS_QUEUE_URL = os.environ['SMS_QUEUE_URL']

def handler(event, context):
    """
    Processes a single batch of student records.
    - Creates initial DynamoDB records with pending statuses
    - Queues notifications to dual SQS queues (email + SMS)
    """
    batch_data = event # The Map state passes each item from the 'batches' array here
    
    status_manager = DynamoDBStatusManager()
    
    email_messages = []
    sms_messages = []
    
    # 1. Create initial DynamoDB records and prepare dual queue messages
    for student in batch_data:
        # Create initial record with pending statuses
        status_manager.create_initial_record(student)
        
        # Prepare email queue message
        email_messages.append({
            'Id': f"email-{student['student_id']}",
            'MessageBody': json.dumps({
                'student_id': student['student_id'],
                'email': student['email'],
                'results': student['results'],
                'phone': student['phone']
            }),
            'MessageGroupId': 'email-notification'
        })
        
        # Prepare SMS queue message
        sms_messages.append({
            'Id': f"sms-{student['student_id']}",
            'MessageBody': json.dumps({
                'student_id': student['student_id'],
                'phone': student['phone'],
                'results': student['results'],
                'email': student['email']
            }),
            'MessageGroupId': 'sms-notification'
        })
    
    # 2. Send messages to email queue
    if email_messages:
        for i in range(0, len(email_messages), 10):
            sqs.send_message_batch(
                QueueUrl=EMAIL_QUEUE_URL,
                Entries=email_messages[i:i + 10]
            )
    
    # 3. Send messages to SMS queue
    if sms_messages:
        for i in range(0, len(sms_messages), 10):
            sqs.send_message_batch(
                QueueUrl=SMS_QUEUE_URL,
                Entries=sms_messages[i:i + 10]
            )
        
    return {
        'processed_count': len(batch_data),
        'email_queued': len(email_messages),
        'sms_queued': len(sms_messages),
        'status': 'completed'
    }