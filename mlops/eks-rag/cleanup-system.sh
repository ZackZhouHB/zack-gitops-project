#!/bin/bash

# AWS EKS RAG System Cleanup Script
# This script cleans S3 documents, Weaviate indexed documents, and chat history
# while preserving the Weaviate schema (Vector Dimensions) to avoid backend restarts

set -e

# Configuration
NAMESPACE="rag-system"
S3_BUCKET="eks-rag-weaviate-documents-2kif5iiw"
AWS_PROFILE="sandboxtest"

echo "🧹 Starting AWS EKS RAG System Cleanup..."
echo "================================================"

# 1. Clean S3 Documents
echo "📁 Cleaning S3 documents..."
aws s3 rm s3://${S3_BUCKET} --recursive --profile ${AWS_PROFILE}
if [ $? -eq 0 ]; then
    echo "✅ S3 documents cleaned successfully"
else
    echo "❌ Failed to clean S3 documents"
    exit 1
fi

# 2. Clean Weaviate Indexed Documents (preserve schema)
echo "🗂️  Cleaning Weaviate indexed documents..."
kubectl exec -n ${NAMESPACE} deployment/rag-backend -- python -c "
import urllib.request
import json
try:
    # Get all document IDs
    response = urllib.request.urlopen('http://weaviate-service:8080/v1/objects?class=Document', timeout=30)
    data = json.loads(response.read().decode())
    objects = data.get('objects', [])
    
    print(f'Found {len(objects)} documents to delete')
    
    # Delete each document by ID (preserves schema)
    deleted_count = 0
    for obj in objects:
        doc_id = obj.get('id')
        if doc_id:
            try:
                req = urllib.request.Request(f'http://weaviate-service:8080/v1/objects/{doc_id}', method='DELETE')
                urllib.request.urlopen(req, timeout=10)
                deleted_count += 1
            except Exception as e:
                print(f'Error deleting document {doc_id}: {e}')
    
    print(f'✅ Deleted {deleted_count} indexed documents (schema preserved)')
    
except Exception as e:
    print(f'❌ Error cleaning Weaviate documents: {e}')
    exit(1)
"

if [ $? -ne 0 ]; then
    echo "❌ Failed to clean Weaviate documents"
    exit 1
fi

# 3. Clean Chat History
echo "💬 Cleaning chat history..."
kubectl exec -n ${NAMESPACE} deployment/rag-backend -- rm -f /efs/chat_history/global_history.json
if [ $? -eq 0 ]; then
    echo "✅ Chat history cleaned successfully"
else
    echo "❌ Failed to clean chat history"
    exit 1
fi

# 4. Verify Cleanup
echo "🔍 Verifying cleanup..."

# Check S3
S3_COUNT=$(aws s3 ls s3://${S3_BUCKET} --recursive --profile ${AWS_PROFILE} | wc -l)
echo "📁 S3 documents remaining: ${S3_COUNT}"

# Check Weaviate
WEAVIATE_COUNT=$(kubectl exec -n ${NAMESPACE} deployment/rag-backend -- python -c "
import urllib.request
import json
try:
    response = urllib.request.urlopen('http://weaviate-service:8080/v1/objects?class=Document', timeout=10)
    data = json.loads(response.read().decode())
    print(len(data.get('objects', [])))
except:
    print('0')
" 2>/dev/null)
echo "🗂️  Weaviate documents remaining: ${WEAVIATE_COUNT}"

# Check Schema (should still exist)
SCHEMA_EXISTS=$(kubectl exec -n ${NAMESPACE} deployment/rag-backend -- python -c "
import urllib.request
import json
try:
    response = urllib.request.urlopen('http://weaviate-service:8080/v1/schema', timeout=10)
    data = json.loads(response.read().decode())
    classes = data.get('classes', [])
    print('YES' if any(cls.get('class') == 'Document' for cls in classes) else 'NO')
except:
    print('NO')
" 2>/dev/null)
echo "📊 Document schema preserved: ${SCHEMA_EXISTS}"

# Check Chat History
CHAT_EXISTS=$(kubectl exec -n ${NAMESPACE} deployment/rag-backend -- test -f /efs/chat_history/global_history.json && echo "YES" || echo "NO")
echo "💬 Chat history file exists: ${CHAT_EXISTS}"

echo "================================================"
if [ "${S3_COUNT}" -eq 0 ] && [ "${WEAVIATE_COUNT}" -eq 0 ] && [ "${SCHEMA_EXISTS}" = "YES" ] && [ "${CHAT_EXISTS}" = "NO" ]; then
    echo "✅ System cleanup completed successfully!"
    echo "📊 Vector Dimensions preserved - no backend restart needed"
    echo "🚀 Ready for fresh testing"
else
    echo "⚠️  Cleanup completed with warnings - please verify manually"
fi

echo "================================================"
