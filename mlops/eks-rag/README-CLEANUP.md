# System Cleanup Scripts

This directory contains scripts to clean the AWS EKS RAG system for fresh testing while preserving the Weaviate schema to avoid backend restarts.

## Available Scripts

### 1. Bash Script: `cleanup-system.sh`
```bash
./cleanup-system.sh
```

### 2. Python Script: `cleanup-system.py`
```bash
python3 cleanup-system.py
# or
./cleanup-system.py
```

## What Gets Cleaned

✅ **S3 Documents**: All uploaded documents in `eks-rag-weaviate-documents-2kif5iiw` bucket
✅ **Weaviate Indexed Documents**: All indexed document objects (preserves Document class schema)
✅ **Chat History**: Global conversation history file

## What Gets Preserved

🔒 **Weaviate Schema**: Document class and vector dimensions (384) remain intact
🔒 **Backend Pods**: No restart needed - clients remain connected
🔒 **System Configuration**: All settings and connections preserved

## Expected Results After Cleanup

- **S3 Documents**: 0 uploaded
- **Indexed Documents**: 0 chunks
- **Vector Dimensions**: 384 (preserved)
- **Chat History**: Empty
- **System Status**: Ready for fresh testing

## Usage Example

```bash
# Run cleanup
./cleanup-system.sh

# Expected output:
# ✅ System cleanup completed successfully!
# 📊 Vector Dimensions preserved - no backend restart needed
# 🚀 Ready for fresh testing
```

## Configuration

Both scripts use these default settings:
- **Namespace**: `rag-system`
- **S3 Bucket**: `eks-rag-weaviate-documents-2kif5iiw`
- **AWS Profile**: `sandboxtest`

To modify these settings, edit the configuration section at the top of either script.

## Troubleshooting

If cleanup fails:
1. Check kubectl access to `rag-system` namespace
2. Verify AWS CLI profile `sandboxtest` is configured
3. Ensure backend pods are running and healthy
4. Check Weaviate service connectivity

## Manual Verification

After running cleanup, you can manually verify:

```bash
# Check S3
aws s3 ls s3://eks-rag-weaviate-documents-2kif5iiw --recursive --profile sandboxtest

# Check Weaviate objects
kubectl exec -n rag-system deployment/rag-backend -- python -c "
import urllib.request, json
response = urllib.request.urlopen('http://weaviate-service:8080/v1/objects?class=Document')
print(f'Objects: {len(json.loads(response.read().decode()).get(\"objects\", []))}')
"

# Check schema preservation
kubectl exec -n rag-system deployment/rag-backend -- python -c "
import urllib.request, json
response = urllib.request.urlopen('http://weaviate-service:8080/v1/schema')
classes = json.loads(response.read().decode()).get('classes', [])
print(f'Document class exists: {any(c.get(\"class\") == \"Document\" for c in classes)}')
"
```
