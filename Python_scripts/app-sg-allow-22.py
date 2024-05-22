import boto3
import json

def lambda_handler(event, context):
    # Initialize boto3 clients
    ses_client = boto3.client('ses')
    ec2_client = boto3.client('ec2')
    
    # Email details
    sender = 'sender@example.com'
    recipient = 'recipient@example.com'
    subject = 'Security Group Alert: Port 22 Open to the World'
    
    # Extract details from the event
    detail = event['detail']
    event_name = detail['eventName']
    security_group_id = None
    
    if event_name == 'AuthorizeSecurityGroupIngress':
        security_group_id = detail['requestParameters']['groupId']
        ip_permissions = detail['requestParameters']['ipPermissions']['items']
    elif event_name == 'CreateSecurityGroup':
        security_group_id = detail['responseElements']['groupId']
        ip_permissions = detail['requestParameters']['ipPermissionsEgress']['items']
    
    # Check if port 22 is open to 0.0.0.0/0
    if security_group_id and ip_permissions:
        for permission in ip_permissions:
            if 'ipRanges' in permission:
                for ip_range in permission['ipRanges']['items']:
                    if ip_range['cidrIp'] == '0.0.0.0/0' and permission['fromPort'] == 22 and permission['toPort'] == 22:
                        # Compose email body
                        body_text = (f"Security Group ID: {security_group_id} has been modified to allow port 22 from everywhere (0.0.0.0/0).")
                        body_html = f"""<html>
                        <head></head>
                        <body>
                          <h1>Security Group Alert</h1>
                          <p>Security Group ID: <b>{security_group_id}</b> has been modified to allow port 22 from everywhere (0.0.0.0/0).</p>
                        </body>
                        </html>"""
                        
                        # Send email
                        response = ses_client.send_email(
                            Source=sender,
                            Destination={'ToAddresses': [recipient]},
                            Message={
                                'Subject': {'Data': subject},
                                'Body': {
                                    'Text': {'Data': body_text},
                                    'Html': {'Data': body_html}
                                }
                            }
                        )
                        print(f"Email sent! Message ID: {response['MessageId']}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Lambda function executed successfully!')
    }

