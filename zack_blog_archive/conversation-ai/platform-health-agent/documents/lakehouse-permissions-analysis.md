# Lakehouse Implementation - AWS Permissions Analysis

## Executive Summary

Based on the lakehouse solution design and current AWS environment analysis, Chen Chen currently has access to the nonprod account (851725643444) through a GROUP assignment, but the existing permission set (NESANonProd_MARS_Admin) is **insufficient** for implementing the proposed lakehouse architecture.

## Current State Analysis

### 1. Account Information
- **NonProd Account ID**: 851725643444
- **Analytics Account ID**: 594282448067
- **Management Account ID**: 958462689380
- **Region**: ap-southeast-2 (Sydney)

### 2. Chen Chen's Current Access

**User Details:**
- Username: chen.chen@nesa.nsw.edu.au
- User ID: 390ee478-30c1-709a-2812-95342d0b508c
- Display Name: Chen Chen

**Current Assignment:**
- Chen Chen is assigned to nonprod account through **GROUP** membership (Group ID: 697e24b8-20a1-70cb-31ce-6bd964951cd9)
- Permission Set: **NESANonProd_MARS_Admin** (ps-c056bd21eebcf174)
- Session Duration: 8 hours

### 3. Current Permission Set Analysis

The **NESANonProd_MARS_Admin** permission set includes:

#### ✅ **Adequate Permissions:**
1. **S3 Full Access** - Covers all S3 operations needed for data lake
2. **IAM Policy Management** - Can create/manage policies
3. **IAM Role Management** - Can create/manage roles
4. **IAM Instance Profile** - Can manage EC2 instance profiles
5. **IAM PassRole** - Limited to EC2 service

#### ❌ **Missing Critical Permissions for Lakehouse:**

1. **AWS Glue** - NO permissions at all
   - Need: Glue database, table, crawler, job, workflow management
   - Need: Glue Data Catalog operations
   - Need: Glue connection management for DB2

2. **Amazon Athena** - NO permissions
   - Need: Query execution
   - Need: Workgroup management
   - Need: Query result access

3. **AWS Lake Formation** - NO permissions
   - Need: Data lake admin capabilities
   - Need: Table/database permissions
   - Need: Fine-grained access control

4. **AWS Transfer Family** - NO permissions
   - Need: SFTP server creation/management
   - Need: User management
   - Need: Server configuration

5. **Amazon AppFlow** - NO permissions
   - Need: Flow creation for SharePoint integration
   - Need: Connection management
   - Need: Flow execution

6. **Amazon EventBridge** - NO permissions
   - Need: Rule creation for orchestration
   - Need: Event pattern management
   - Need: Target configuration

7. **AWS KMS** - NO permissions
   - Need: Key creation/management for encryption
   - Need: Grant management
   - Need: Key policy updates

8. **Amazon CloudWatch** - NO permissions
   - Need: Log group creation
   - Need: Metric creation
   - Need: Alarm management

9. **VPC/Networking** - NO permissions
   - Need: VPC endpoint creation
   - Need: Security group management
   - Need: Subnet configuration

10. **EC2 Limitations**
    - Current: Only MARS-tagged instances
    - Need: Broader EC2 access for jump boxes and workstations

### 4. Current Infrastructure State

**Existing Resources in NonProd:**
- S3 Buckets: 8 buckets exist (mostly non-lakehouse related)
- Glue Databases: **NONE**
- Glue Jobs: **NONE**
- IAM Roles: No data/lakehouse-specific roles found

**Assessment:** This is a **greenfield implementation** - no existing lakehouse infrastructure.

## Lakehouse Architecture Requirements

Based on the lakehouse.md document, the solution requires:

### Data Sources
1. **DB2 (iSeries)** - via Glue JDBC connections
2. **Manual CSV/Excel uploads** - to S3
3. **External SFTP** - via AWS Transfer Family
4. **Kiteworks** - via SFTP/Transfer Family
5. **SharePoint Online** - via Amazon AppFlow

### Core Services Needed
1. **Amazon S3** - Data lake storage (landing, bronze, silver, gold, export zones)
2. **AWS Glue** - ETL jobs, Data Catalog, Crawlers, Workflows
3. **Amazon Athena** - Query engine for Iceberg tables
4. **AWS Transfer Family** - SFTP endpoints for partners
5. **Amazon AppFlow** - SharePoint integration
6. **Amazon EventBridge** - Orchestration triggers
7. **AWS Lake Formation** - Fine-grained access control (optional but recommended)
8. **Amazon VPC** - Network isolation
9. **AWS KMS** - Encryption at rest
10. **Amazon CloudWatch** - Monitoring and logging

### EC2 Requirements (from document)
- Secure Admin Jump Box (t3.large)
- Data Engineering Workstation (r7i.xlarge, 1-2 instances)
- XML Feed Generation & Testing (r7i.xlarge)
- Integration Testing Server (t3.large)

## Recommendations

### Phase 1: Immediate Actions (Week 1)

#### 1.1 Create New Permission Set: **DataEngineer-Lakehouse-Full**

This should be a **separate permission set** from MARS_Admin to follow principle of least privilege and separation of concerns.

**Recommended Managed Policies:**
```
- AWSGlueConsoleFullAccess
- AmazonAthenaFullAccess
- AWSLakeFormationDataAdmin
- CloudWatchLogsFullAccess
- AmazonEventBridgeFullAccess
```

**Custom Inline Policy Required:**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3DataLakeAccess",
      "Effect": "Allow",
      "Action": [
        "s3:*"
      ],
      "Resource": [
        "arn:aws:s3:::nesa-lakehouse-*",
        "arn:aws:s3:::nesa-lakehouse-*/*"
      ]
    },
    {
      "Sid": "TransferFamilyManagement",
      "Effect": "Allow",
      "Action": [
        "transfer:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AppFlowManagement",
      "Effect": "Allow",
      "Action": [
        "appflow:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "KMSKeyManagement",
      "Effect": "Allow",
      "Action": [
        "kms:CreateKey",
        "kms:CreateAlias",
        "kms:DescribeKey",
        "kms:ListAliases",
        "kms:PutKeyPolicy",
        "kms:CreateGrant",
        "kms:Encrypt",
        "kms:Decrypt",
        "kms:GenerateDataKey"
      ],
      "Resource": "*"
    },
    {
      "Sid": "VPCNetworkingForGlue",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVpcEndpoint",
        "ec2:DescribeVpcEndpoints",
        "ec2:ModifyVpcEndpoint",
        "ec2:DeleteVpcEndpoint",
        "ec2:CreateSecurityGroup",
        "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:DescribeSubnets",
        "ec2:DescribeVpcs",
        "ec2:DescribeNetworkInterfaces",
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:DescribeRouteTables"
      ],
      "Resource": "*"
    },
    {
      "Sid": "EC2ForDataEngineering",
      "Effect": "Allow",
      "Action": [
        "ec2:RunInstances",
        "ec2:TerminateInstances",
        "ec2:StartInstances",
        "ec2:StopInstances",
        "ec2:DescribeInstances",
        "ec2:DescribeInstanceTypes",
        "ec2:DescribeImages",
        "ec2:CreateTags"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": "ap-southeast-2"
        }
      }
    },
    {
      "Sid": "IAMRoleCreationForServices",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:AttachRolePolicy",
        "iam:PutRolePolicy",
        "iam:PassRole",
        "iam:GetRole",
        "iam:GetRolePolicy",
        "iam:ListAttachedRolePolicies",
        "iam:ListRolePolicies"
      ],
      "Resource": [
        "arn:aws:iam::851725643444:role/LakehouseGlue*",
        "arn:aws:iam::851725643444:role/LakehouseAthena*",
        "arn:aws:iam::851725643444:role/LakehouseTransfer*",
        "arn:aws:iam::851725643444:role/LakehouseAppFlow*"
      ]
    },
    {
      "Sid": "SecretsManagerForConnections",
      "Effect": "Allow",
      "Action": [
        "secretsmanager:CreateSecret",
        "secretsmanager:GetSecretValue",
        "secretsmanager:PutSecretValue",
        "secretsmanager:DescribeSecret",
        "secretsmanager:TagResource"
      ],
      "Resource": "arn:aws:secretsmanager:ap-southeast-2:851725643444:secret:lakehouse/*"
    }
  ]
}
```

#### 1.2 Assign Permission Set to Chen Chen

**Action Required:**
```bash
aws sso-admin create-account-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-825984f2564c10aa \
  --target-id 851725643444 \
  --target-type AWS_ACCOUNT \
  --permission-set-arn <NEW_PERMISSION_SET_ARN> \
  --principal-type USER \
  --principal-id 390ee478-30c1-709a-2812-95342d0b508c \
  --region ap-southeast-2 \
  --profile mgmt
```

### Phase 2: Infrastructure Setup (Week 1-2)

#### 2.1 Create Service Roles

**Required IAM Roles:**

1. **LakehouseGlueServiceRole**
   - Trust: glue.amazonaws.com
   - Policies: AWSGlueServiceRole, S3 access, KMS access

2. **LakehouseAthenaServiceRole**
   - Trust: athena.amazonaws.com
   - Policies: S3 access, Glue Data Catalog access

3. **LakehouseTransferServiceRole**
   - Trust: transfer.amazonaws.com
   - Policies: S3 access, CloudWatch Logs

4. **LakehouseAppFlowServiceRole**
   - Trust: appflow.amazonaws.com
   - Policies: S3 access, SharePoint connector

#### 2.2 Create S3 Bucket Structure

**Bucket Naming Convention:**
```
nesa-lakehouse-nonprod-landing
nesa-lakehouse-nonprod-bronze
nesa-lakehouse-nonprod-silver
nesa-lakehouse-nonprod-gold
nesa-lakehouse-nonprod-export
nesa-lakehouse-nonprod-athena-results
```

**Folder Structure within each bucket:**
```
landing/
  ├── db2/
  ├── files/csv/
  ├── files/excel/
  ├── sftp/partnerX/
  ├── kiteworks/
  └── sharepoint/

bronze/
  ├── db2_*/
  ├── files_*/
  ├── sftp_*/
  ├── kiteworks_*/
  └── sharepoint_*/

silver/
  ├── customers/
  ├── orders/
  └── payments/

gold/
  ├── sales_summary_daily/
  ├── partnerX_feed/
  └── kiteworks_feed/

export/
  ├── partnerX/
  └── kiteworks/
```

### Phase 3: Additional Considerations

#### 3.1 Lake Formation Setup (Recommended)

**Why Lake Formation:**
- Fine-grained access control at table/column level
- Centralized permissions management
- Audit trail for data access
- Easier to manage as team grows

**Setup Steps:**
1. Enable Lake Formation in nonprod account
2. Register S3 locations (bronze, silver, gold)
3. Create Lake Formation permissions for Chen Chen
4. Grant database/table permissions as needed

#### 3.2 Networking Considerations

**VPC Requirements:**
- Glue needs VPC endpoints for S3, Glue, and other services
- Transfer Family needs VPC endpoint for SFTP
- Security groups for EC2 instances
- Private subnets for data processing

#### 3.3 Monitoring and Logging

**CloudWatch Setup:**
- Log groups for Glue jobs
- Log groups for Transfer Family
- Metrics for data pipeline monitoring
- Alarms for job failures

### Phase 4: Migration to Analytics Account

Once POC is successful in nonprod, migration to analytics account (594282448067) will require:

1. **Create identical permission set** in analytics account
2. **Replicate IAM roles** with analytics account ID
3. **Create S3 buckets** with production naming convention
4. **Setup Lake Formation** in analytics account
5. **Configure cross-account access** if needed between nonprod and analytics

## Security Recommendations

### 1. Principle of Least Privilege
- Keep MARS_Admin separate from Lakehouse permissions
- Create specific roles for each service
- Use resource-based policies where possible

### 2. Encryption
- Enable S3 bucket encryption with KMS
- Use separate KMS keys for different data zones
- Encrypt Glue Data Catalog
- Enable encryption for Athena query results

### 3. Network Security
- Use VPC endpoints for AWS services
- Implement security groups with minimal required access
- Use private subnets for data processing
- Enable VPC Flow Logs

### 4. Audit and Compliance
- Enable CloudTrail for all API calls
- Enable S3 access logging
- Use Lake Formation for data access audit
- Implement tagging strategy for cost allocation

## Implementation Timeline

### Week 1: Permissions and Foundation
- [ ] Create DataEngineer-Lakehouse-Full permission set
- [ ] Assign to Chen Chen
- [ ] Create service IAM roles
- [ ] Setup S3 bucket structure

### Week 2: Core Services
- [ ] Configure AWS Glue connections (DB2)
- [ ] Setup Transfer Family SFTP endpoints
- [ ] Configure AppFlow for SharePoint
- [ ] Create initial Glue databases

### Week 3-4: ETL Development
- [ ] Develop Glue jobs for data ingestion
- [ ] Create Iceberg table schemas
- [ ] Setup Glue workflows
- [ ] Configure EventBridge triggers

### Week 5-6: Testing and Validation
- [ ] Test end-to-end data flow
- [ ] Validate Athena queries
- [ ] Test partner SFTP access
- [ ] Performance testing

### Week 7-8: EC2 Setup and Tools
- [ ] Provision EC2 instances
- [ ] Install required tools
- [ ] Configure access and security
- [ ] Setup monitoring

### Week 9-12: Production Migration
- [ ] Replicate setup in analytics account
- [ ] Data migration
- [ ] User acceptance testing
- [ ] Go-live

## Cost Estimation

### Monthly Costs (Estimated for POC in NonProd)

**Compute:**
- EC2 instances (4 instances, mixed usage): ~$500-800/month
- Glue ETL jobs (assuming 100 DPU-hours/day): ~$1,100/month

**Storage:**
- S3 (1TB data): ~$23/month
- S3 requests and data transfer: ~$50/month

**Data Processing:**
- Athena queries (1TB scanned/month): ~$5/month
- Transfer Family (2 SFTP servers): ~$432/month
- AppFlow (1 flow, daily runs): ~$20/month

**Other Services:**
- KMS: ~$1/month per key
- CloudWatch Logs: ~$10/month
- EventBridge: Minimal cost

**Total Estimated Monthly Cost: ~$2,200-2,500/month for POC**

## Next Steps

### Immediate Actions Required:

1. **Review and Approve** this analysis with stakeholders
2. **Create new permission set** as specified above
3. **Assign permission set** to Chen Chen
4. **Schedule kickoff meeting** with Chen Chen to review:
   - Architecture design
   - Permission requirements
   - Implementation timeline
   - Resource requirements

5. **Prepare for Phase 1 implementation**:
   - Finalize S3 bucket naming conventions
   - Prepare IAM role policies
   - Document network requirements
   - Identify DB2 connection details

### Questions to Resolve:

1. **DB2 Connection**: What are the network connectivity requirements? VPN? Direct Connect?
2. **SharePoint**: Which SharePoint sites/libraries need to be integrated?
3. **SFTP Partners**: How many external partners? What are their requirements?
4. **Kiteworks**: Is Kiteworks already configured? What are the connection details?
5. **Data Volume**: Confirm the ~1TB estimate and daily ingestion rates
6. **Compliance**: Any specific compliance requirements (e.g., data residency, encryption standards)?

## Conclusion

Chen Chen currently has **insufficient permissions** to implement the lakehouse architecture. The existing MARS_Admin permission set is focused on EC2/S3/IAM for MARS application and lacks critical services like Glue, Athena, Lake Formation, Transfer Family, and AppFlow.

**Recommendation**: Create a new, comprehensive **DataEngineer-Lakehouse-Full** permission set with all required services and assign it to Chen Chen for the nonprod account. This will enable the POC implementation while maintaining security through least-privilege access and proper service role separation.

The nonprod account (851725643444) is the correct starting point as it's a clean slate with no existing lakehouse infrastructure, allowing for a proper POC before production deployment to the analytics account (594282448067).
