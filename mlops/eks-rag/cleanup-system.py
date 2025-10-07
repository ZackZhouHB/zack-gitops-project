#!/usr/bin/env python3
"""
AWS EKS RAG System Cleanup Script (Python Version)
This script cleans S3 documents, Weaviate indexed documents, and chat history
while preserving the Weaviate schema (Vector Dimensions) to avoid backend restarts
"""

import subprocess
import json
import sys
import urllib.request
import urllib.error

# Configuration
NAMESPACE = "rag-system"
S3_BUCKET = "eks-rag-weaviate-documents-2kif5iiw"
AWS_PROFILE = "sandboxtest"

def run_command(cmd, shell=True, capture_output=True):
    """Run a shell command and return the result"""
    try:
        result = subprocess.run(cmd, shell=shell, capture_output=capture_output, text=True)
        return result.returncode == 0, result.stdout.strip(), result.stderr.strip()
    except Exception as e:
        return False, "", str(e)

def kubectl_exec(command):
    """Execute command in backend pod"""
    cmd = f"kubectl exec -n {NAMESPACE} deployment/rag-backend -- {command}"
    return run_command(cmd)

def clean_s3_documents():
    """Clean all S3 documents"""
    print("📁 Cleaning S3 documents...")
    success, stdout, stderr = run_command(f"aws s3 rm s3://{S3_BUCKET} --recursive --profile {AWS_PROFILE}")
    if success:
        print("✅ S3 documents cleaned successfully")
        return True
    else:
        print(f"❌ Failed to clean S3 documents: {stderr}")
        return False

def clean_weaviate_documents():
    """Clean Weaviate indexed documents while preserving schema"""
    print("🗂️  Cleaning Weaviate indexed documents...")
    
    python_script = '''
import urllib.request
import json
try:
    # Get all document IDs
    response = urllib.request.urlopen("http://weaviate-service:8080/v1/objects?class=Document", timeout=30)
    data = json.loads(response.read().decode())
    objects = data.get("objects", [])
    
    print(f"Found {len(objects)} documents to delete")
    
    # Delete each document by ID (preserves schema)
    deleted_count = 0
    for obj in objects:
        doc_id = obj.get("id")
        if doc_id:
            try:
                req = urllib.request.Request(f"http://weaviate-service:8080/v1/objects/{doc_id}", method="DELETE")
                urllib.request.urlopen(req, timeout=10)
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting document {doc_id}: {e}")
    
    print(f"✅ Deleted {deleted_count} indexed documents (schema preserved)")
    
except Exception as e:
    print(f"❌ Error cleaning Weaviate documents: {e}")
    exit(1)
'''
    
    success, stdout, stderr = kubectl_exec(f'python -c "{python_script}"')
    if success:
        print(stdout)
        return True
    else:
        print(f"❌ Failed to clean Weaviate documents: {stderr}")
        return False

def clean_chat_history():
    """Clean chat history"""
    print("💬 Cleaning chat history...")
    success, stdout, stderr = kubectl_exec("rm -f /efs/chat_history/global_history.json")
    if success:
        print("✅ Chat history cleaned successfully")
        return True
    else:
        print(f"❌ Failed to clean chat history: {stderr}")
        return False

def verify_cleanup():
    """Verify cleanup results"""
    print("🔍 Verifying cleanup...")
    
    # Check S3
    success, stdout, stderr = run_command(f"aws s3 ls s3://{S3_BUCKET} --recursive --profile {AWS_PROFILE}")
    s3_count = len(stdout.split('\n')) if stdout.strip() else 0
    print(f"📁 S3 documents remaining: {s3_count}")
    
    # Check Weaviate
    weaviate_script = '''
import urllib.request
import json
try:
    response = urllib.request.urlopen("http://weaviate-service:8080/v1/objects?class=Document", timeout=10)
    data = json.loads(response.read().decode())
    print(len(data.get("objects", [])))
except:
    print("0")
'''
    success, stdout, stderr = kubectl_exec(f'python -c "{weaviate_script}"')
    weaviate_count = int(stdout.strip()) if stdout.strip().isdigit() else 0
    print(f"🗂️  Weaviate documents remaining: {weaviate_count}")
    
    # Check Schema
    schema_script = '''
import urllib.request
import json
try:
    response = urllib.request.urlopen("http://weaviate-service:8080/v1/schema", timeout=10)
    data = json.loads(response.read().decode())
    classes = data.get("classes", [])
    print("YES" if any(cls.get("class") == "Document" for cls in classes) else "NO")
except:
    print("NO")
'''
    success, stdout, stderr = kubectl_exec(f'python -c "{schema_script}"')
    schema_exists = stdout.strip() == "YES"
    print(f"📊 Document schema preserved: {'YES' if schema_exists else 'NO'}")
    
    # Check Chat History
    success, stdout, stderr = kubectl_exec("test -f /efs/chat_history/global_history.json")
    chat_exists = success
    print(f"💬 Chat history file exists: {'YES' if chat_exists else 'NO'}")
    
    return s3_count == 0, weaviate_count == 0, schema_exists, not chat_exists

def main():
    """Main cleanup function"""
    print("🧹 Starting AWS EKS RAG System Cleanup...")
    print("=" * 48)
    
    # Perform cleanup
    s3_success = clean_s3_documents()
    weaviate_success = clean_weaviate_documents()
    chat_success = clean_chat_history()
    
    if not all([s3_success, weaviate_success, chat_success]):
        print("❌ Some cleanup operations failed")
        sys.exit(1)
    
    # Verify results
    s3_clean, weaviate_clean, schema_preserved, chat_clean = verify_cleanup()
    
    print("=" * 48)
    if s3_clean and weaviate_clean and schema_preserved and chat_clean:
        print("✅ System cleanup completed successfully!")
        print("📊 Vector Dimensions preserved - no backend restart needed")
        print("🚀 Ready for fresh testing")
    else:
        print("⚠️  Cleanup completed with warnings - please verify manually")
    
    print("=" * 48)

if __name__ == "__main__":
    main()
