import os
import boto3
import json
from botocore.exceptions import ClientError

# Import shared utilities

from common.dynamodb_status import DynamoDBStatusManager

ses = boto3.client('ses')
SENDER_EMAIL = os.environ['SENDER_EMAIL']
status_manager = DynamoDBStatusManager()

def handler(event, context):
    """
    Processes SQS messages and sends result emails via SES.
    """
    for record in event['Records']:
        student_data = json.loads(record['body'])
        student_id = student_data['student_id']
        student_email = student_data['email']
        
        # NOTE: A real template engine (e.g., Jinja2) would be better here
        email_body = f"""
        <html>
        <body>
            <h1>Your HSC Results Are Ready</h1>
            <p>Dear student {student_id},</p>
            <p>Your results are: {student_data['results']}</p>
            <p>This is an automated notification.</p>
        </body>
        </html>
        """
        
        try:
            ses.send_email(
                Source=SENDER_EMAIL,
                Destination={'ToAddresses': [student_email]},
                Message={
                    'Subject': {'Data': 'Your HSC Results Are Ready'},
                    'Body': {'Html': {'Data': email_body}}
                }
            )
            print(f"Successfully sent email to {student_id}")
            
            # Update DynamoDB with successful delivery status
            status_manager.update_email_status(student_id, 'sent')
            
        except ClientError as e:
            error_message = e.response['Error']['Message']
            print(f"Failed to send email to {student_id}: {error_message}")
            
            # Update DynamoDB with failed delivery status
            status_manager.update_email_status(student_id, 'failed', error_message)
            
            # Re-raise to trigger SQS retry
            raise e
    return {'status': 'completed'}