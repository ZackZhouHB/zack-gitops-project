import os
import boto3
import pandas as pd
import io
import json

s3_client = boto3.client('s3')
BATCH_SIZE = 500  # Configurable batch size

def handler(event, context):
    """
    Parses a headerless CSV file from S3 and splits it into manageable batches.
    This version is adapted for the specific format of the POC test files.
    """
    bucket = event['s3_bucket']
    key = event['s3_key']
    
    # 1. Read CSV from S3 into a pandas DataFrame, assuming no header
    response = s3_client.get_object(Bucket=bucket, Key=key)
    csv_content = response['Body'].read()
    
    # Define column names manually as the source CSV has no header
    # Based on "hsc_results_poc_email_sms_no_header.csv"
    # "amro.malkawi@nesa.nsw.edu.au",20000001,16.000,"2024 HSC Results...",452025776
    column_names = ['email', 'student_id', 'extra_data', 'results', 'phone']
    
    df = pd.read_csv(io.BytesIO(csv_content), header=None, names=column_names)
    
    # 2. Basic validation on the dataframe shape
    if 'student_id' not in df.columns or 'results' not in df.columns:
        raise ValueError(f"CSV is missing required columns. Found: {list(df.columns)}")

    # Validate phone column exists and is not null for SMS delivery
    if 'phone' not in df.columns:
        raise ValueError("CSV is missing required 'phone' column for SMS notifications")
    
    # Ensure phone is string type for consistent processing
    df['phone'] = df['phone'].astype(str)

    total_records = len(df)
    
    # 3. Convert DataFrame to list of dictionaries
    records = df.to_dict('records')
    
    # 4. Create batches
    batches = [records[i:i + BATCH_SIZE] for i in range(0, total_records, BATCH_SIZE)]
    
    # 5. Return the batches payload for the Step Functions Map state
    return {
        'total_students': total_records,
        'batch_count': len(batches),
        'batches': batches
    }