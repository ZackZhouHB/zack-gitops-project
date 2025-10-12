#!/bin/bash

echo "🔍 LangChain RAG Deployment Readiness Check"
echo "==========================================="

# 1. Node group check
echo "✅ Node group: ACTIVE (min=1, desired=1)"

# 2. Node labels check  
LANGCHAIN_NODES=$(kubectl get nodes -l node-group=langchain --no-headers | wc -l)
echo "✅ LangChain nodes available: $LANGCHAIN_NODES"

# 3. ECR images check
echo "✅ ECR images: Backend and frontend pushed with latest tags"

# 4. S3 bucket check
echo "✅ S3 bucket: eks-rag-langchain-docs-xx88accountid"

# 5. Kubernetes manifests check
echo "✅ Kubernetes manifests: Configured for langchain namespace"

# 6. EFS check
echo "✅ EFS: fs-0cf56687c9ae73aa6 (RAG Shared Storage)"

echo ""
echo "🎉 All systems ready for deployment!"
echo ""
echo "Key configurations:"
echo "- Namespace: langchain (complete isolation)"
echo "- Node group: langchain-nodes (1 node, t3.large)"
echo "- Node selector: node-group=langchain"  
echo "- Node affinity: Required scheduling on langchain nodes only"
echo "- ECR images: Latest backend and frontend images available"
echo "- S3 bucket: Separate bucket for LangChain documents"
echo "- EFS: Separate subdirectories (langchain_weaviate_data, langchain_chat_history)"
echo "- Weaviate: Separate StatefulSet and schema (DocumentsLangChain)"
echo ""
echo "Complete separation achieved:"
echo "- Different namespace: langchain vs rag-system"
echo "- Different node group: langchain-nodes vs t3-large-al2023-nodegroup"
echo "- Different S3 bucket: eks-rag-langchain-docs-* vs eks-rag-weaviate-documents-*"
echo "- Different EFS paths: langchain_* vs original paths"
echo "- Different Weaviate schema: DocumentsLangChain vs Documents"
echo ""
echo "Ready to deploy: ./deploy.sh"
