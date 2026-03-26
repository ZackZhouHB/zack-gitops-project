"""Lambda function: S3 upload → Bedrock KB sync trigger.

When a file is uploaded to the KB data source S3 bucket,
this Lambda automatically starts an ingestion job to re-index.

Environment variables:
    KNOWLEDGE_BASE_ID: Bedrock Knowledge Base ID
    DATA_SOURCE_ID: S3 data source ID within the KB
"""
import os
import json
import logging

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

bedrock_agent = boto3.client("bedrock-agent")

KNOWLEDGE_BASE_ID = os.environ["KNOWLEDGE_BASE_ID"]
DATA_SOURCE_ID = os.environ["DATA_SOURCE_ID"]


def handler(event, context):
    """Handle S3 event notification → start KB ingestion job."""
    logger.info(f"S3 event received: {json.dumps(event)}")

    # Extract S3 details for logging
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        logger.info(f"File uploaded: s3://{bucket}/{key}")

    # Start ingestion job
    try:
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=KNOWLEDGE_BASE_ID,
            dataSourceId=DATA_SOURCE_ID,
        )
        job_id = response["ingestionJob"]["ingestionJobId"]
        status = response["ingestionJob"]["status"]
        logger.info(f"Ingestion job started: {job_id} (status: {status})")

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Ingestion job started",
                "jobId": job_id,
                "status": status,
            }),
        }

    except Exception as e:
        logger.error(f"Failed to start ingestion job: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
