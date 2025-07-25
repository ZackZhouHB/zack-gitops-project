import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError

class DynamoDBStatusManager:
    def __init__(self):
        self.dynamodb = boto3.resource('dynamodb')
        self.table_name = os.environ['RESULTS_TABLE_NAME']
        self.table = self.dynamodb.Table(self.table_name)
    
    def update_email_status(self, student_id, status, error_message=None):
        self._update_status(student_id, 'email_status', status, error_message)

    def update_sms_status(self, student_id, status, error_message=None):
        self._update_status(student_id, 'sms_status', status, error_message)

    def _update_status(self, student_id, status_field, status, error_message=None):
        """Generic private method to update a status field."""
        try:
            update_expr = f"SET {status_field} = :status, updated_at = :now"
            expr_values = {
                ':status': status,
                ':now': datetime.utcnow().isoformat()
            }

            if status == 'sent':
                sent_at_field = status_field.replace('_status', '_sent_at')
                update_expr += f", {sent_at_field} = :sent_at"
                expr_values[':sent_at'] = datetime.utcnow().isoformat()
            elif status == 'failed' and error_message:
                error_field = status_field.replace('_status', '_error')
                update_expr += f", {error_field} = :error"
                expr_values[':error'] = str(error_message)

            self.table.update_item(
                Key={'student_id': str(student_id)},
                UpdateExpression=update_expr,
                ExpressionAttributeValues=expr_values,
                ConditionExpression="attribute_exists(student_id)"
            )
            return True
        except ClientError as e:
            print(f"Error updating {status_field} for {student_id}: {str(e)}")
            return False
    
    def create_initial_record(self, student_data):
        """Create initial student record with pending statuses"""
        try:
            item = {
                'student_id': str(student_data['student_id']),
                'email': student_data['email'],
                'phone': student_data['phone'],
                'results': student_data['results'],
                'email_status': 'pending',
                'sms_status': 'pending',
                'email_error': None,
                'sms_error': None,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            self.table.put_item(Item=item)
            return True
        except ClientError as e:
            print(f"Error creating initial record: {str(e)}")
            return False