import json
import logging
import boto3
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

stepfunctions = boto3.client('stepfunctions')
STATE_MACHINE_ARN = os.environ['STATE_MACHINE_ARN']

def handler(event, context):
    logger.info("Validation Lambda invoked!")
    logger.info(f"Received event: {json.dumps(event)}")
    
    # Extract S3 details from the event
    for record in event.get('Records', []):
        if record.get('eventSource') == 'aws:s3':
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            # Start Step Function execution
            execution_name = f"hsc-processing-{record['s3']['object']['eTag']}"
            
            try:
                response = stepfunctions.start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    name=execution_name,
                    input=json.dumps({
                        's3_bucket': bucket,
                        's3_key': key
                    })
                )
                
                logger.info(f"Started Step Function execution: {response['executionArn']}")
                
                return {
                    'statusCode': 200,
                    'body': json.dumps({
                        'message': 'Step Function execution started',
                        'executionArn': response['executionArn']
                    })
                }
                
            except Exception as e:
                logger.error(f"Error starting Step Function: {str(e)}")
                return {
                    'statusCode': 500,
                    'body': json.dumps({'error': str(e)})
                }
    
    return {
        'statusCode': 400,
        'body': json.dumps({'error': 'No valid S3 event found'})
    }