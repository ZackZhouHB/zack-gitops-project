#!/bin/bash
set -e

# RAG Cloud Deployment Script
# Usage: ./deploy.sh [apply|destroy]

REGION="ap-southeast-2"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "=== RAG Cloud Deployment ==="
echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"

if [ "$1" == "destroy" ]; then
    echo "=== CLEANUP MODE ==="
    
    # Get CloudFront ID if exists
    CF_ID=$(aws cloudfront list-distributions --query "DistributionList.Items[?Comment=='RAG Cloud Frontend'].Id" --output text 2>/dev/null || true)
    
    if [ -n "$CF_ID" ] && [ "$CF_ID" != "None" ]; then
        echo "Disabling CloudFront $CF_ID..."
        ETAG=$(aws cloudfront get-distribution --id $CF_ID --query 'ETag' --output text)
        aws cloudfront get-distribution-config --id $CF_ID --query 'DistributionConfig' > /tmp/cf-disable.json
        jq '.Enabled = false' /tmp/cf-disable.json > /tmp/cf-disabled.json
        aws cloudfront update-distribution --id $CF_ID --if-match "$ETAG" --distribution-config file:///tmp/cf-disabled.json > /dev/null
        echo "Waiting for CloudFront to disable (this takes ~5 min)..."
        aws cloudfront wait distribution-deployed --id $CF_ID 2>/dev/null || sleep 300
        ETAG=$(aws cloudfront get-distribution --id $CF_ID --query 'ETag' --output text)
        aws cloudfront delete-distribution --id $CF_ID --if-match "$ETAG"
        echo "CloudFront deleted"
    fi
    
    # Delete OAC
    OAC_ID=$(aws cloudfront list-origin-access-controls --query "OriginAccessControlList.Items[?Name=='rag-cloud-frontend-oac'].Id" --output text 2>/dev/null || true)
    if [ -n "$OAC_ID" ] && [ "$OAC_ID" != "None" ]; then
        ETAG=$(aws cloudfront get-origin-access-control --id $OAC_ID --query 'ETag' --output text)
        aws cloudfront delete-origin-access-control --id $OAC_ID --if-match "$ETAG"
        echo "OAC deleted"
    fi
    
    # Delete K8s resources
    echo "Deleting K8s resources..."
    kubectl delete -f $SCRIPT_DIR/k8s/ingress.yaml 2>/dev/null || true
    kubectl delete -f $SCRIPT_DIR/k8s/worker.yaml 2>/dev/null || true
    kubectl delete -f $SCRIPT_DIR/k8s/backend.yaml 2>/dev/null || true
    kubectl delete -f $SCRIPT_DIR/k8s/serviceaccount.yaml 2>/dev/null || true
    helm uninstall redis -n rag 2>/dev/null || true
    helm uninstall aws-load-balancer-controller -n kube-system 2>/dev/null || true
    kubectl delete namespace rag 2>/dev/null || true
    
    # Delete IAM resources
    echo "Deleting IAM resources..."
    aws iam detach-role-policy --role-name rag-cloud-backend-role --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/rag-cloud-backend-policy 2>/dev/null || true
    aws iam delete-role --role-name rag-cloud-backend-role 2>/dev/null || true
    aws iam delete-policy --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/rag-cloud-backend-policy 2>/dev/null || true
    aws iam detach-role-policy --role-name AmazonEKSLoadBalancerControllerRole --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy 2>/dev/null || true
    aws iam delete-role --role-name AmazonEKSLoadBalancerControllerRole 2>/dev/null || true
    aws iam delete-policy --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy 2>/dev/null || true
    
    # Empty S3 buckets
    echo "Emptying S3 buckets..."
    aws s3 rm s3://rag-cloud-dev-documents-$ACCOUNT_ID --recursive --region $REGION 2>/dev/null || true
    aws s3 rm s3://rag-cloud-dev-frontend-$ACCOUNT_ID --recursive --region $REGION 2>/dev/null || true
    
    # Terraform destroy
    echo "Running terraform destroy..."
    cd $SCRIPT_DIR/terraform
    terraform destroy -auto-approve
    
    echo "=== Cleanup Complete ==="
    exit 0
fi

# === DEPLOY MODE ===

# Step 1: Terraform
echo "=== Step 1: Terraform Apply ==="
cd $SCRIPT_DIR/terraform
terraform init -input=false
terraform apply -auto-approve

# Get outputs
OPENSEARCH_ENDPOINT=$(terraform output -raw opensearch_endpoint)
EKS_CLUSTER=$(terraform output -raw eks_cluster_name)
VPC_ID=$(terraform output -raw vpc_id)

# Step 2: Configure kubectl
echo "=== Step 2: Configure kubectl ==="
aws eks update-kubeconfig --region $REGION --name $EKS_CLUSTER
kubectl get nodes

# Step 3: Update K8s ConfigMap
echo "=== Step 3: Update K8s ConfigMap ==="
sed -i "s|OPENSEARCH_ENDPOINT:.*|OPENSEARCH_ENDPOINT: \"$OPENSEARCH_ENDPOINT\"|" $SCRIPT_DIR/k8s/namespace.yaml

# Step 4: Create IAM resources
echo "=== Step 4: Create IAM resources ==="
OIDC_PROVIDER=$(aws eks describe-cluster --name $EKS_CLUSTER --region $REGION --query "cluster.identity.oidc.issuer" --output text | sed 's|https://||')

# Backend policy
cat > /tmp/rag-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {"Effect": "Allow", "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"], "Resource": "*"},
        {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"], "Resource": ["arn:aws:s3:::rag-cloud-dev-documents-$ACCOUNT_ID", "arn:aws:s3:::rag-cloud-dev-documents-$ACCOUNT_ID/*"]},
        {"Effect": "Allow", "Action": ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes"], "Resource": "arn:aws:sqs:$REGION:$ACCOUNT_ID:rag-cloud-dev-*"},
        {"Effect": "Allow", "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query", "dynamodb:Scan"], "Resource": "arn:aws:dynamodb:$REGION:$ACCOUNT_ID:table/rag-cloud-dev-*"},
        {"Effect": "Allow", "Action": ["aoss:APIAccessAll"], "Resource": "*"}
    ]
}
EOF
aws iam create-policy --policy-name rag-cloud-backend-policy --policy-document file:///tmp/rag-policy.json 2>/dev/null || true

# Backend role
cat > /tmp/trust-policy.json << EOF
{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Federated": "arn:aws:iam::$ACCOUNT_ID:oidc-provider/$OIDC_PROVIDER"}, "Action": "sts:AssumeRoleWithWebIdentity", "Condition": {"StringEquals": {"$OIDC_PROVIDER:sub": "system:serviceaccount:rag:rag-backend", "$OIDC_PROVIDER:aud": "sts.amazonaws.com"}}}]}
EOF
aws iam create-role --role-name rag-cloud-backend-role --assume-role-policy-document file:///tmp/trust-policy.json 2>/dev/null || true
aws iam attach-role-policy --role-name rag-cloud-backend-role --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/rag-cloud-backend-policy 2>/dev/null || true

# ALB controller policy
curl -s -o /tmp/alb-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json
aws iam create-policy --policy-name AWSLoadBalancerControllerIAMPolicy --policy-document file:///tmp/alb-policy.json 2>/dev/null || true

# ALB controller role
cat > /tmp/alb-trust.json << EOF
{"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Federated": "arn:aws:iam::$ACCOUNT_ID:oidc-provider/$OIDC_PROVIDER"}, "Action": "sts:AssumeRoleWithWebIdentity", "Condition": {"StringEquals": {"$OIDC_PROVIDER:sub": "system:serviceaccount:kube-system:aws-load-balancer-controller", "$OIDC_PROVIDER:aud": "sts.amazonaws.com"}}}]}
EOF
aws iam create-role --role-name AmazonEKSLoadBalancerControllerRole --assume-role-policy-document file:///tmp/alb-trust.json 2>/dev/null || true
aws iam attach-role-policy --role-name AmazonEKSLoadBalancerControllerRole --policy-arn arn:aws:iam::$ACCOUNT_ID:policy/AWSLoadBalancerControllerIAMPolicy 2>/dev/null || true

# Step 5: Deploy K8s resources
echo "=== Step 5: Deploy K8s resources ==="
kubectl apply -f $SCRIPT_DIR/k8s/namespace.yaml
helm repo add bitnami https://charts.bitnami.com/bitnami 2>/dev/null || true
helm install redis bitnami/redis -n rag -f $SCRIPT_DIR/k8s/redis-values.yaml 2>/dev/null || true
kubectl apply -f $SCRIPT_DIR/k8s/serviceaccount.yaml
kubectl apply -f $SCRIPT_DIR/k8s/backend.yaml
kubectl apply -f $SCRIPT_DIR/k8s/worker.yaml

# Step 6: Install ALB controller
echo "=== Step 6: Install ALB controller ==="
helm repo add eks https://aws.github.io/eks-charts 2>/dev/null || true
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=$EKS_CLUSTER \
  --set serviceAccount.create=true \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set serviceAccount.annotations."eks\.amazonaws\.com/role-arn"=arn:aws:iam::$ACCOUNT_ID:role/AmazonEKSLoadBalancerControllerRole \
  --set region=$REGION \
  --set vpcId=$VPC_ID 2>/dev/null || true

sleep 30

# Step 7: Create Ingress
echo "=== Step 7: Create Ingress ==="
kubectl apply -f $SCRIPT_DIR/k8s/ingress.yaml
echo "Waiting for ALB..."
sleep 60
ALB_URL=$(kubectl get ingress -n rag backend -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "ALB URL: $ALB_URL"

# Step 8: Deploy Frontend
echo "=== Step 8: Deploy Frontend ==="
cd $SCRIPT_DIR/frontend
npm install
npm run build
aws s3 sync dist/ s3://rag-cloud-dev-frontend-$ACCOUNT_ID/ --delete --region $REGION

# Step 9: Create CloudFront
echo "=== Step 9: Create CloudFront ==="
OAC_ID=$(aws cloudfront create-origin-access-control \
  --origin-access-control-config '{"Name": "rag-cloud-frontend-oac", "SigningProtocol": "sigv4", "SigningBehavior": "always", "OriginAccessControlOriginType": "s3"}' \
  --query 'OriginAccessControl.Id' --output text 2>/dev/null || \
  aws cloudfront list-origin-access-controls --query "OriginAccessControlList.Items[?Name=='rag-cloud-frontend-oac'].Id" --output text)

# Create CloudFront distribution config
cat > /tmp/cf-config.json << EOF
{
  "CallerReference": "rag-cloud-$(date +%s)",
  "Comment": "RAG Cloud Frontend",
  "Enabled": true,
  "DefaultRootObject": "index.html",
  "Origins": {
    "Quantity": 2,
    "Items": [
      {"Id": "S3Origin", "DomainName": "rag-cloud-dev-frontend-$ACCOUNT_ID.s3.$REGION.amazonaws.com", "S3OriginConfig": {"OriginAccessIdentity": ""}, "OriginAccessControlId": "$OAC_ID"},
      {"Id": "ALBOrigin", "DomainName": "$ALB_URL", "CustomOriginConfig": {"HTTPPort": 80, "HTTPSPort": 443, "OriginProtocolPolicy": "http-only", "OriginSslProtocols": {"Quantity": 1, "Items": ["TLSv1.2"]}}}
    ]
  },
  "DefaultCacheBehavior": {
    "TargetOriginId": "S3Origin",
    "ViewerProtocolPolicy": "redirect-to-https",
    "AllowedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"], "CachedMethods": {"Quantity": 2, "Items": ["GET", "HEAD"]}},
    "CachePolicyId": "658327ea-f89d-4fab-a63d-7e88639e58f6",
    "Compress": true
  },
  "CacheBehaviors": {
    "Quantity": 14,
    "Items": [
      {"PathPattern": "/auth/*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/query*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/documents*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/upload*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/health", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 2, "Items": ["GET","HEAD"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "Compress": true},
      {"PathPattern": "/agent*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/connectors/*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/pipeline/*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/history/*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/cache/*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/usage*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/audit*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/jobs*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true},
      {"PathPattern": "/evaluate*", "TargetOriginId": "ALBOrigin", "ViewerProtocolPolicy": "redirect-to-https", "AllowedMethods": {"Quantity": 7, "Items": ["GET","HEAD","OPTIONS","PUT","POST","PATCH","DELETE"], "CachedMethods": {"Quantity": 2, "Items": ["GET","HEAD"]}}, "CachePolicyId": "4135ea2d-6df8-44a3-9df3-4b5a84be39ad", "OriginRequestPolicyId": "216adef6-5c7f-47e4-b989-5492eafa07d3", "Compress": true}
    ]
  },
  "CustomErrorResponses": {"Quantity": 1, "Items": [{"ErrorCode": 403, "ResponsePagePath": "/index.html", "ResponseCode": "200", "ErrorCachingMinTTL": 10}]},
  "PriceClass": "PriceClass_All"
}
EOF

CF_RESPONSE=$(aws cloudfront create-distribution --distribution-config file:///tmp/cf-config.json)
CF_ID=$(echo "$CF_RESPONSE" | jq -r '.Distribution.Id')
CF_DOMAIN=$(echo "$CF_RESPONSE" | jq -r '.Distribution.DomainName')

# Update S3 bucket policy
cat > /tmp/bucket-policy.json << EOF
{"Version": "2012-10-17", "Statement": [{"Sid": "AllowCloudFrontServicePrincipal", "Effect": "Allow", "Principal": {"Service": "cloudfront.amazonaws.com"}, "Action": "s3:GetObject", "Resource": "arn:aws:s3:::rag-cloud-dev-frontend-$ACCOUNT_ID/*", "Condition": {"StringEquals": {"AWS:SourceArn": "arn:aws:cloudfront::$ACCOUNT_ID:distribution/$CF_ID"}}}]}
EOF
aws s3api put-bucket-policy --bucket rag-cloud-dev-frontend-$ACCOUNT_ID --policy file:///tmp/bucket-policy.json

echo ""
echo "=== Deployment Complete ==="
echo "Backend API: http://$ALB_URL"
echo "Frontend: https://$CF_DOMAIN (wait 5-10 min for CloudFront)"
echo ""
echo "Test: curl http://$ALB_URL/health"
