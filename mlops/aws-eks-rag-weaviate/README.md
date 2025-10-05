# AWS EKS RAG Solution - Complete Architecture Guide

## 🏗 **Solution Overview**

A production-ready **Retrieval-Augmented Generation (RAG)** system deployed on **Amazon EKS** with **AWS managed services** for cloud team collaboration. Features **shared document access** with **global conversation history** for optimal team productivity and knowledge sharing.

### **Key Features**
- 🤝 **Shared Knowledge Base**: All team documents accessible to everyone
- 🌐 **Global Conversation History**: All conversations from all sessions visible to everyone
- 📄 **Multi-Format Support**: PDF, Word, Excel, PowerPoint, CSV, Text, Markdown
- 🚀 **Auto-Scaling**: Karpenter with spot instances for cost optimization
- 🔍 **Intelligent Search**: AWS Kendra with Bedrock Claude 3 Sonnet 4
- 📊 **Real-Time Monitoring**: Sync status, health checks, attribution tracking
- 🎨 **Professional Design**: Education-sector appropriate styling with modern UI
- 📱 **Responsive Interface**: Mobile-optimized for all device sizes
- ⚡ **Enhanced UX**: Expandable chat history, loading indicators, error handling

## 🎯 **Architecture Design**

### **High-Level Architecture**
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Frontend      │    │   EKS Cluster    │    │   AWS Services      │
│   (React SPA)   │───▶│   Backend API    │───▶│   Kendra + Bedrock  │
│   LoadBalancer  │    │   Global History │    │   S3 + EFS          │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
```

### **Detailed Component Architecture**
```
┌─────────────────────────────────────────────────────────────────────┐
│                           EKS Cluster                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐ │
│  │   Frontend      │  │   Backend       │  │   Infrastructure    │ │
│  │   - Nginx       │  │   - FastAPI     │  │   - Karpenter       │ │
│  │   - Static SPA  │  │   - Global Hist │  │   - EFS CSI         │ │
│  │   - LoadBalancer│  │   - Doc Service │  │   - EBS CSI         │ │
│  └─────────────────┘  │   - Kendra Svc  │  │   - VPC CNI         │ │
│                       └─────────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
        ┌─────────────────┐ ┌─────────────┐ ┌─────────────┐
        │       S3        │ │   Kendra    │ │   Bedrock   │
        │ Shared Docs     │ │ Search Index│ │ Claude 4    │
        │ Text Extraction │ │ Sync Jobs   │ │ Generation  │
        └─────────────────┘ └─────────────┘ └─────────────┘
                    ▲
        ┌─────────────────┐
        │      EFS        │
        │ Global History  │
        │ All Sessions    │
        └─────────────────┘
```

## 📁 **Project Structure**

```
aws-eks-rag/
├── README.md                    # This comprehensive guide
├── SESSION_DEMO.md             # Multi-user session examples
├── COMMUNICATION_FLOW.md       # Service communication validation
├── deploy.sh                   # Complete deployment automation
├── validate-communication.sh   # Service connectivity testing
│
├── terraform/                  # Infrastructure as Code
│   ├── main.tf                # Provider configuration
│   ├── variables.tf           # Input variables
│   ├── terraform.tfvars       # Environment values
│   ├── outputs.tf             # Infrastructure outputs
│   ├── vpc.tf                 # New VPC with subnets
│   ├── eks.tf                 # EKS cluster + addons
│   ├── karpenter.tf           # Auto-scaling configuration
│   ├── iam.tf                 # IAM roles + policies
│   ├── s3.tf                  # Document storage bucket
│   ├── kendra.tf              # Search index + data source
│   └── efs.tf                 # Persistent file system
│
├── backend/                    # Python FastAPI application
│   ├── Dockerfile             # Optimized container image
│   ├── requirements.txt       # Python dependencies
│   └── app/
│       ├── main.py            # API endpoints + session handling
│       ├── session_service.py # IP-based session management
│       ├── document_service.py# S3 upload + text extraction
│       ├── kendra_service.py  # Search + LLM integration
│       └── config.py          # Environment configuration
│
├── frontend/                  # Static web application
│   ├── Dockerfile             # Nginx container with proxy
│   ├── nginx.conf             # Kubernetes DNS + CORS config
│   ├── index.html             # Main SPA interface with professional design
│   ├── script.js              # Frontend logic + API calls + session management
│   └── style.css              # Professional education-sector styling
│
└── k8s/                       # Kubernetes manifests
    ├── namespace.yaml         # rag-system namespace
    ├── configmap.yaml         # Application configuration
    ├── efs-storage.yaml       # EFS persistent volumes
    ├── backend-deployment.yaml# FastAPI pods + service
    ├── frontend-deployment.yaml# Nginx + LoadBalancer
    └── ingress.yaml           # External access routing
```

## 🔧 **Infrastructure Components**

### **Amazon EKS Cluster**
- **Version**: 1.28
- **Node Group**: 2-3 m5.large on-demand instances
- **Auto-Scaling**: Karpenter with spot instances
- **Addons**: EBS CSI, EFS CSI, VPC CNI, CoreDNS, kube-proxy

### **AWS Managed Services**

#### **Amazon S3 (Document Storage)**
```
Bucket Structure:
├── documents/                  # Shared team documents
│   ├── aws-inventory.xlsx     # Multi-format support
│   ├── project-design.pdf     # Automatic text extraction
│   └── network-diagram.pptx   # Attribution metadata
└── text/                      # Extracted text for Kendra
    ├── aws-inventory.xlsx.txt
    ├── project-design.pdf.txt
    └── network-diagram.pptx.txt
```

#### **Amazon Kendra (Search & Indexing)**
- **Edition**: Developer (cost-optimized for small teams)
- **Data Source**: S3 bucket with automatic sync
- **Index**: Shared across all team members
- **Search**: Semantic search with relevance scoring

#### **Amazon Bedrock (LLM)**
- **Model**: Claude 3 Sonnet (`anthropic.claude-3-sonnet-20240229-v1:0`)
- **Usage**: Answer generation with context from Kendra
- **Integration**: Streaming responses with source attribution

#### **Amazon EFS (Persistent Storage)**
```
EFS Structure:
/efs/chat_history/
└── global_history.json          # ALL conversations from ALL sessions
    ├── Session abc12345 conversations
    ├── Session def67890 conversations  
    └── Session xyz98765 conversations
```

### **Container Registry (ECR)**

#### **Backend Image**
```
Repository: aws-eks-rag-backend
URI: {account-id}.dkr.ecr.ap-southeast-2.amazonaws.com/aws-eks-rag-backend:latest
Contents: FastAPI application with AWS service integrations
```

#### **Frontend Image**
```
Repository: aws-eks-rag-frontend  
URI: {account-id}.dkr.ecr.ap-southeast-2.amazonaws.com/aws-eks-rag-frontend:latest
Contents: Nginx with static files and API proxy configuration
```

### **Networking & Security**

#### **VPC Configuration**
- **CIDR**: 10.0.0.0/16
- **Subnets**: 3 AZs with public/private subnets
- **NAT Gateway**: For private subnet internet access
- **Security Groups**: Least privilege access

#### **Service Communication & DNS**
```
Frontend → Backend Communication:
- DNS Name: rag-backend-service.rag-system.svc.cluster.local:8000
- Protocol: HTTP with nginx proxy
- CORS: Enabled with proper headers
- Timeouts: 60s for long-running requests

External Access:
- LoadBalancer: rag-frontend-service (AWS ALB)
- Health Checks: /health endpoint
- API Routing: /api/* → backend service
- Static Files: Served directly by nginx
```

#### **IAM Roles & Policies**
```
Roles:
├── EKS Cluster Role           # EKS service permissions
├── EKS Node Group Role        # EC2 + ECR + CNI permissions
├── Karpenter Role            # Auto-scaling permissions
├── RAG Backend Role          # Kendra + Bedrock + S3 access
├── EFS CSI Role              # EFS mount permissions
└── Kendra Service Role       # S3 + KMS access
```

## 🔄 **Global Session Management Design**

### **Shared History Model**
```python
# IP-based session generation (for tracking only)
session_id = hashlib.md5(f"{client_ip}".encode()).hexdigest()[:8]

# Global shared storage strategy
Documents: SHARED across all users (documents/)
Chat History: GLOBAL shared file (/efs/chat_history/global_history.json)
Kendra Search: ALL documents searchable by ALL users
```

### **Global History Flow**
```
1. User accesses frontend → Gets unique session ID for tracking
2. Frontend loads ALL previous conversations from ALL sessions
3. User asks question → Saved to global history with session ID
4. All users see ALL conversations from ALL sessions
5. Each conversation shows which session asked it
6. Perfect for team collaboration and knowledge sharing
```

## 📊 **Data Flow Architecture**

### **Document Upload Flow**
```
User Upload → FastAPI → Text Extraction → S3 Storage → Kendra Sync → Search Index
     │              │                        │              │
     │              └─ Metadata ─────────────┘              │
     └─ Session ID ──────────────────────────────────────────┘
```

### **Query Processing Flow**
```
User Query → Session Check → Kendra Search → Context Prep → Bedrock LLM → Response + Sources
     │              │              │              │              │
     │              │              └─ All Docs ───┘              │
     │              └─ user-{session}-history.json ──────────────┘
     └─ Frontend Display ←─────────────────────────────────────────┘
```

### **File Processing Pipeline**
```
Supported Formats:
├── PDF → PyPDF2 → Text extraction
├── Word (.docx) → python-docx → Text extraction  
├── Excel (.xlsx) → pandas → Data summary
├── PowerPoint (.pptx) → python-pptx → Slide text
├── CSV → pandas → Data structure
├── Text/Markdown → Direct processing
└── All formats → S3 metadata + Kendra indexing
```

## 🔧 **Technical Improvements & Bug Fixes**

### **Major Issues Resolved**

#### **Session Management & Chat History**
- ✅ **Fixed**: Session ID generation using client IP hashing for proper tracking
- ✅ **Fixed**: Global conversation history loading and display issues
- ✅ **Added**: Expandable chat history items with full content viewing capability
- ✅ **Enhanced**: Conversation history sorted by timestamp (newest first)

#### **Document Management System**
- ✅ **Fixed**: Document upload functionality (corrected method name from `upload_document` to `upload_to_s3`)
- ✅ **Added**: Document deletion with confirmation dialogs
- ✅ **Enhanced**: Document count tracking and real-time display updates
- ✅ **Added**: Proper file format validation and error handling

#### **Kendra Integration**
- ✅ **Fixed**: Bedrock API configuration (added required `anthropic_version` field)
- ✅ **Added**: Kendra sync history tracking with job monitoring
- ✅ **Enhanced**: Sync status display with real-time updates
- ✅ **Fixed**: API method calls for document queries and searches

#### **API & Backend Fixes**
- ✅ **Fixed**: Method name mismatches between frontend and backend services
- ✅ **Enhanced**: Proper error handling with user-friendly messages
- ✅ **Added**: Global history persistence to EFS with proper file structure
- ✅ **Fixed**: Parameter ordering in API calls and function signatures

#### **Frontend JavaScript Improvements**
- ✅ **Added**: Missing functions (`showTab()`, `refreshDocuments()`, `loadKendraSyncHistory()`, `deleteDocument()`)
- ✅ **Enhanced**: Document upload functionality with progress feedback
- ✅ **Updated**: DOMContentLoaded to automatically load documents and history
- ✅ **Improved**: Error handling and user feedback mechanisms

### **Performance Enhancements**
- **Loading Indicators**: Professional spinners with progress bars
- **Async Operations**: Non-blocking API calls with proper state management
- **Error Recovery**: Automatic retry mechanisms for failed operations
- **Caching**: Efficient document list caching to reduce API calls

## 🎨 **Professional Design & User Experience**

### **Education-Sector Appropriate Styling**
The system features a professional, modern interface designed specifically for public sector education departments:

#### **Color Scheme**
```css
Professional Palette:
├── Header: Linear gradient (#2c3e50 → #34495e) - Sophisticated blue-gray
├── Background: #f5f7fa - Clean, light gray
├── Primary Actions: #3498db - Professional blue
├── Secondary Elements: #6c757d - Formal gray
├── Status Indicators: Green (#28a745), Red (#dc3545), Yellow (#ffc107)
└── Text: #2c3e50, #495057 - High contrast, accessibility compliant
```

#### **Modern UI Components**
- **Card-Based Layout**: Clean white containers with subtle shadows
- **Professional Typography**: System font stack with proper weights
- **Button Styling**: Uppercase text, letter spacing, smooth transitions
- **Responsive Design**: Mobile-optimized layouts for all screen sizes
- **Loading States**: Professional spinners with progress indicators
- **Alert Messaging**: Contextual colors with proper contrast ratios

#### **Enhanced User Experience**
- **Expandable Chat History**: Click to view full conversation details
- **Real-Time Feedback**: Loading indicators during API calls
- **Error Handling**: User-friendly error messages with retry options
- **Document Management**: Intuitive upload, sync, and deletion workflows
- **Session Tracking**: Clear session identification and status display

#### **Accessibility Features**
- High contrast color ratios (WCAG 2.1 AA compliant)
- Keyboard navigation support
- Screen reader friendly markup
- Focus indicators with visible outlines
- Responsive text scaling

## 🚀 **Deployment Guide**

### **Prerequisites**
- AWS CLI configured with `sandboxtest` profile
- Docker installed and running
- kubectl installed
- Terraform >= 1.0

### **Complete Deployment**
```bash
# Clone and navigate
cd /mnt/f/aws/zz-nesa/AI/aws-eks-rag

# Deploy everything (infrastructure + application)
./deploy.sh

# Monitor deployment
kubectl get pods -n rag-system -w
kubectl get services -n rag-system
kubectl get ingress -n rag-system
```

### **Deployment Steps Breakdown**
```
1. Terraform Infrastructure Provisioning
   ├── VPC + Subnets + NAT Gateway
   ├── EKS Cluster + Node Groups + Karpenter
   ├── S3 Bucket + Kendra Index + EFS
   └── IAM Roles + Security Groups

2. ECR Repository Setup & Image Build
   ├── Create ECR repositories (backend + frontend)
   ├── Build backend Docker image (FastAPI + dependencies)
   ├── Build frontend Docker image (nginx + static files)
   ├── Push both images to ECR
   └── Update Kubernetes manifests with ECR URIs

3. Kubernetes Application Deployment
   ├── Namespace + ConfigMaps
   ├── EFS Storage Classes + PVCs
   ├── Backend Deployment + ClusterIP Service
   ├── Frontend Deployment + LoadBalancer Service
   └── Service Communication Validation

4. Service Validation & Testing
   ├── Health checks (Backend, Kendra, S3, Bedrock)
   ├── DNS resolution testing (validate-communication.sh)
   ├── HTTP connectivity validation
   ├── Document upload testing
   ├── Kendra sync verification
   └── End-to-end query testing
```

## 🔍 **API Endpoints Reference**

### **Health & Status**
```
GET  /api/                     # System health + session info
GET  /api/documents/sync-status/{job_id}  # Kendra sync monitoring
```

### **Document Management**
```
POST /api/documents/upload     # Multi-format file upload
GET  /api/documents           # List all shared documents
DELETE /api/documents/{filename}  # Delete shared document
POST /api/documents/sync      # Trigger Kendra sync job
```

### **Query & Chat**
```
POST /api/query               # RAG query with global history tracking
GET  /api/conversation-history # Global chat history from all sessions
```

### **Request/Response Examples**

#### **Document Upload**
```bash
curl -X POST "http://your-loadbalancer/api/documents/upload" \
  -F "file=@aws-architecture.pdf" \
  -H "Content-Type: multipart/form-data"

Response:
{
  "message": "Successfully uploaded aws-architecture.pdf",
  "session_id": "abc12345"
}
```

#### **RAG Query**
```bash
curl -X POST "http://your-loadbalancer/api/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are our VPC security requirements?",
    "top_k": 5
  }'

Response:
{
  "question": "What are our VPC security requirements?",
  "answer": "Based on the AWS architecture and security policy documents...",
  "sources": [
    {
      "title": "aws-architecture.pdf",
      "uri": "s3://bucket/documents/aws-architecture.pdf",
      "score": 0.85,
      "excerpt": "VPC security groups must..."
    }
  ],
  "processing_time": 2.34,
  "user_prefix": "user-abc12345"
}
```

## 🛠 **Troubleshooting Guide**

### **Common Issues & Solutions**

#### **1. EKS Cluster Issues**
```bash
# Check cluster status
aws eks describe-cluster --name eks-rag-cluster --profile sandboxtest

# Update kubeconfig
aws eks update-kubeconfig --name eks-rag-cluster --region ap-southeast-2 --profile sandboxtest

# Check node status
kubectl get nodes
kubectl describe node <node-name>
```

#### **2. Pod Deployment Issues**
```bash
# Check pod status
kubectl get pods -n rag-system
kubectl describe pod <pod-name> -n rag-system
kubectl logs <pod-name> -n rag-system

# Check persistent volumes
kubectl get pv,pvc -n rag-system
kubectl describe pvc efs-chat-history-pvc -n rag-system
```

#### **3. AWS Service Connectivity**
```bash
# Test S3 access
aws s3 ls s3://your-bucket-name --profile sandboxtest

# Check Kendra index
aws kendra describe-index --index-id YOUR_INDEX_ID --region ap-southeast-2 --profile sandboxtest

# Test Bedrock access
aws bedrock list-foundation-models --region ap-southeast-2 --profile sandboxtest
```

#### **4. Application Health Checks**
```bash
# Backend health
kubectl port-forward svc/rag-backend-service 8000:8000 -n rag-system
curl http://localhost:8000/

# Frontend access
kubectl get svc rag-frontend-service -n rag-system
# Check LoadBalancer external IP
```

#### **5. Session & Storage Issues**
```bash
# Check EFS mount
kubectl exec -it <backend-pod> -n rag-system -- ls -la /efs/chat_history/

# Verify S3 document structure
aws s3 ls s3://your-bucket/documents/ --profile sandboxtest
aws s3 ls s3://your-bucket/text/ --profile sandboxtest

# Check Kendra sync status
curl "http://your-loadbalancer/api/documents/sync-status/JOB_ID"
```

#### **5. Service Communication Issues**
```bash
# Run comprehensive communication validation
./validate-communication.sh

# Manual DNS resolution testing
kubectl exec <frontend-pod> -n rag-system -- nslookup rag-backend-service.rag-system.svc.cluster.local

# Test HTTP connectivity
kubectl exec <frontend-pod> -n rag-system -- curl http://rag-backend-service.rag-system.svc.cluster.local:8000/

# Test nginx proxy functionality
kubectl exec <frontend-pod> -n rag-system -- curl http://localhost/api/

# Check service endpoints
kubectl get endpoints -n rag-system
kubectl describe svc rag-backend-service -n rag-system

# Verify nginx configuration
kubectl exec <frontend-pod> -n rag-system -- cat /etc/nginx/conf.d/default.conf
```

#### **6. ECR Image Issues**
```bash
# Check ECR repositories
aws ecr describe-repositories --region ap-southeast-2 --profile sandboxtest

# Verify image tags
aws ecr list-images --repository-name aws-eks-rag-backend --region ap-southeast-2 --profile sandboxtest
aws ecr list-images --repository-name aws-eks-rag-frontend --region ap-southeast-2 --profile sandboxtest

# Check pod image pull status
kubectl describe pod <pod-name> -n rag-system | grep -A 10 "Events:"

# Manual image pull test
docker pull {account-id}.dkr.ecr.ap-southeast-2.amazonaws.com/aws-eks-rag-backend:latest
```

### **Monitoring & Logs**
```bash
# Application logs
kubectl logs -f deployment/rag-backend -n rag-system
kubectl logs -f deployment/rag-frontend -n rag-system

# Karpenter logs
kubectl logs -f -n karpenter deployment/karpenter

# EFS CSI logs
kubectl logs -f -n kube-system daemonset/efs-csi-node
```

## 💰 **Cost Optimization**

### **Current Architecture Costs (Monthly)**
```
EKS Cluster Control Plane: ~$73
EC2 Instances (2x m5.large): ~$140
Kendra Developer Edition: ~$810
S3 Storage (100GB): ~$2.30
EFS Storage (10GB): ~$3
Bedrock Usage (estimated): ~$50
Total: ~$1,078/month
```

### **Cost Optimization Strategies**
- **Karpenter Spot Instances**: 60-70% cost reduction on compute
- **EFS Provisioned Throughput**: Adjust based on usage patterns
- **S3 Intelligent Tiering**: Automatic cost optimization for documents
- **Bedrock Token Optimization**: Efficient prompt engineering

## 🔮 **Future Enhancements**

### **Phase 2: Multi-Tenant Architecture**
- Team-based namespaces (cloud-team, hr-team, solutions-team)
- Separate Kendra indexes per team
- JWT-based authentication with team claims
- Admin interface for user/team management

### **Phase 3: Advanced Features**
- Document versioning and change tracking
- Advanced analytics and usage metrics
- Integration with existing SSO (Cognito/OIDC)
- Mobile-responsive PWA frontend
- Automated document classification

### **Phase 4: Enterprise Features**
- Multi-region deployment
- Disaster recovery and backup strategies
- Advanced security scanning and compliance
- Integration with enterprise document systems
- Custom model fine-tuning capabilities

## ✅ **Deployment Validation Checklist**

### **Infrastructure Validation**
- [ ] **EKS Cluster**: `kubectl cluster-info`
- [ ] **Nodes Ready**: `kubectl get nodes`
- [ ] **Namespace**: `kubectl get ns rag-system`
- [ ] **ECR Repositories**: `aws ecr describe-repositories --region ap-southeast-2`

### **Service Validation**
- [ ] **Services Exist**: `kubectl get svc -n rag-system`
- [ ] **Pods Running**: `kubectl get pods -n rag-system`
- [ ] **Endpoints Ready**: `kubectl get endpoints -n rag-system`
- [ ] **LoadBalancer IP**: `kubectl get svc rag-frontend-service -n rag-system`

### **Communication Validation**
- [ ] **DNS Resolution**: `./validate-communication.sh`
- [ ] **Backend Health**: `curl http://rag-backend-service:8000/` (from frontend pod)
- [ ] **Proxy Function**: `curl http://localhost/api/` (from frontend pod)
- [ ] **External Access**: `curl http://<external-ip>/api/`

### **Application Validation**
- [ ] **Document Upload**: Test file upload via frontend
- [ ] **Kendra Sync**: Trigger and monitor sync job
- [ ] **RAG Query**: Test question answering
- [ ] **Session Isolation**: Test multiple user sessions

## 📞 **Support & Maintenance**

### **Validation & Testing Tools**

#### **Communication Validation**
```bash
# Comprehensive service communication testing
./validate-communication.sh

# Manual validation commands
kubectl get svc,endpoints -n rag-system
kubectl exec <frontend-pod> -n rag-system -- nslookup rag-backend-service
kubectl exec <frontend-pod> -n rag-system -- curl http://localhost/api/
```

#### **Health Check Endpoints**
```bash
# Backend health (direct)
kubectl port-forward svc/rag-backend-service 8000:8000 -n rag-system
curl http://localhost:8000/

# Frontend health (via LoadBalancer)
curl http://<external-ip>/health

# API health (via proxy)
curl http://<external-ip>/api/
```

### **Key Configuration Files**
- **Infrastructure**: `terraform/terraform.tfvars`
- **Application**: `k8s/configmap.yaml`
- **Backend Container**: `backend/Dockerfile`
- **Frontend Container**: `frontend/Dockerfile` + `frontend/nginx.conf`
- **Deployment**: `deploy.sh`
- **Validation**: `validate-communication.sh`
- **Communication Guide**: `COMMUNICATION_FLOW.md`

### **Important Environment Variables**
```bash
# Backend Configuration
AWS_REGION=ap-southeast-2
S3_BUCKET_NAME=eks-rag-cluster-documents-xxxxx
KENDRA_INDEX_ID=xxxxxxxxxx
KENDRA_DATA_SOURCE_ID=xxxxxxxxxx
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0

# ECR Configuration
ECR_BACKEND_URI={account-id}.dkr.ecr.ap-southeast-2.amazonaws.com/aws-eks-rag-backend
ECR_FRONTEND_URI={account-id}.dkr.ecr.ap-southeast-2.amazonaws.com/aws-eks-rag-frontend

# Service Communication
BACKEND_SERVICE_DNS=rag-backend-service.rag-system.svc.cluster.local:8000
FRONTEND_SERVICE_DNS=rag-frontend-service.rag-system.svc.cluster.local:80
```

### **Backup & Recovery**
- **EFS Chat History**: Automatic AWS backups enabled
- **S3 Documents**: Versioning enabled with lifecycle policies
- **Kendra Index**: Rebuild from S3 source documents
- **Infrastructure**: Terraform state in version control

This comprehensive guide provides complete visibility into the AWS EKS RAG solution architecture, enabling effective troubleshooting, maintenance, and future enhancements for your cloud team's collaborative Q&A system.

## 📋 **Summary of Improvements**

### **Since Initial Deployment, Major Enhancements Include:**

#### **Functionality Fixes**
- **Chat History**: Resolved loading issues, now displays global conversation history with expandable items
- **Document Upload**: Fixed broken upload functionality with proper API integration
- **Session Management**: Implemented proper IP-based session tracking
- **Kendra Sync**: Added sync history tracking and status monitoring
- **API Integration**: Fixed method name mismatches and parameter ordering issues

#### **Professional Design Overhaul**
- **Color Scheme**: Transformed from informal orange/purple to professional blue-gray palette
- **Typography**: Updated to system font stack with proper weights and spacing
- **Layout**: Modernized with card-based design and subtle shadows
- **Responsive Design**: Enhanced mobile optimization for all screen sizes
- **Accessibility**: WCAG 2.1 AA compliant with high contrast ratios

#### **User Experience Enhancements**
- **Loading States**: Professional spinners with progress indicators
- **Error Handling**: User-friendly messages with retry options
- **Navigation**: Intuitive tab-based interface with smooth transitions
- **Feedback**: Real-time status updates and confirmation dialogs
- **History**: Expandable conversation items with full content viewing

#### **System Reliability**
- **Error Recovery**: Automatic retry mechanisms for failed operations
- **Validation**: Comprehensive input validation and format checking
- **Monitoring**: Enhanced health checks and status reporting
- **Documentation**: Updated README with complete technical specifications

The system now provides a robust, professional, and education-appropriate RAG solution ready for production deployment in public sector environments.
