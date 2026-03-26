# Lakehouse Permission Setup - Azure AD Group Approach

## Current Setup Understanding

Your company uses:
1. **Azure AD** → Create groups and add users
2. **Azure AD Sync** → Groups sync to AWS SSO via External Identity Provider
3. **AWS SSO** → Assign permission sets to groups for target accounts

**Example**: Chen Chen is in Azure AD group `AZP_AWS_NESANonProd_MARS_Admin` which syncs to AWS SSO.

## Recommended Approach

### Step 1: Create Azure AD Group (Azure Portal)

**Group Name**: `AZP_AWS_NESANonProd_DataEngineer_Lakehouse`

**Naming Convention**: Following your existing pattern:
- `AZP_AWS_` = Prefix for AWS-related groups
- `NESANonProd_` = Target account identifier
- `DataEngineer_Lakehouse` = Permission set purpose

**Members to Add**:
- Chen Chen (chen.chen@nesa.nsw.edu.au)
- Any other data engineers who need lakehouse access

**Action Required**: 
- Azure AD admin creates this group in Azure Portal
- Add Chen Chen as member
- Wait for sync to AWS SSO (usually automatic, check sync schedule)

---

### Step 2: Verify Group Sync to AWS SSO

After Azure AD sync completes, verify the group appears in AWS:

```bash
# Check if group synced
aws identitystore list-groups \
  --identity-store-id d-97671c8e22 \
  --region ap-southeast-2 \
  --profile mgmt \
  --filters AttributePath=DisplayName,AttributeValue=AZP_AWS_NESANonProd_DataEngineer_Lakehouse
```

**Expected Output**: Group with matching DisplayName and a GroupId

**Note the GroupId** - you'll need it for Step 4.

---

### Step 3: Create Permission Set in AWS SSO

**Option A: Via AWS Console** (Recommended for first time)

1. Go to AWS SSO Console → Permission sets
2. Click "Create permission set"
3. Choose "Custom permission set"
4. **Name**: `DataEngineer-Lakehouse`
5. **Description**: `Full access for lakehouse implementation - Glue, Athena, S3, Transfer Family, AppFlow, Lake Formation`
6. **Session duration**: 8 hours
7. **Attach policies**: None (we'll use inline policy)
8. **Inline policy**: Paste content from `lakehouse-permission-set.json`
9. Click "Create"

**Option B: Via AWS CLI**

```bash
# Create permission set
aws sso-admin create-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-825984f2564c10aa \
  --name "DataEngineer-Lakehouse" \
  --description "Full access for lakehouse implementation" \
  --session-duration "PT8H" \
  --region ap-southeast-2 \
  --profile mgmt

# Note the PermissionSetArn from output

# Attach inline policy
aws sso-admin put-inline-policy-to-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-825984f2564c10aa \
  --permission-set-arn <PERMISSION_SET_ARN> \
  --inline-policy file://lakehouse-permission-set.json \
  --region ap-southeast-2 \
  --profile mgmt
```

---

### Step 4: Assign Permission Set to Group

**Option A: Via AWS Console** (Recommended)

1. Go to AWS SSO Console → AWS accounts
2. Select **NonProd account** (851725643444)
3. Click "Assign users or groups"
4. Select "Groups" tab
5. Search for `AZP_AWS_NESANonProd_DataEngineer_Lakehouse`
6. Select the group
7. Click "Next"
8. Select permission set: `DataEngineer-Lakehouse`
9. Click "Finish"

**Option B: Via AWS CLI**

```bash
# Assign permission set to group for NonProd account
aws sso-admin create-account-assignment \
  --instance-arn arn:aws:sso:::instance/ssoins-825984f2564c10aa \
  --target-id 851725643444 \
  --target-type AWS_ACCOUNT \
  --permission-set-arn <PERMISSION_SET_ARN> \
  --principal-type GROUP \
  --principal-id <GROUP_ID_FROM_STEP2> \
  --region ap-southeast-2 \
  --profile mgmt

# Provision the permission set
aws sso-admin provision-permission-set \
  --instance-arn arn:aws:sso:::instance/ssoins-825984f2564c10aa \
  --permission-set-arn <PERMISSION_SET_ARN> \
  --target-type AWS_ACCOUNT \
  --target-id 851725643444 \
  --region ap-southeast-2 \
  --profile mgmt
```

---

### Step 5: Chen Chen Access

After assignment, Chen Chen needs to:

1. **Logout and login** to AWS SSO portal (https://nesa.awsapps.com/start)
2. He should now see **two** permission sets for NonProd account:
   - `NESANonProd_MARS_Admin` (existing)
   - `DataEngineer-Lakehouse` (new)
3. Click on `DataEngineer-Lakehouse` to access NonProd with lakehouse permissions

---

## For Production (Analytics Account) - Later

When POC is successful and ready for production:

### Option 1: Same Group, Different Account
Assign the same group to Analytics account:
- Group: `AZP_AWS_NESANonProd_DataEngineer_Lakehouse`
- Permission Set: `DataEngineer-Lakehouse`
- Target Account: Analytics (594282448067)

### Option 2: Separate Group (Recommended)
Create new Azure AD group:
- Name: `AZP_AWS_Analytics_DataEngineer_Lakehouse`
- Add Chen Chen and production data engineers
- Assign to Analytics account with same permission set

---

## Comparison: Group vs Direct User Assignment

### ✅ Group Assignment (Your Approach - Recommended)
**Pros:**
- Centralized management in Azure AD
- Easy to add/remove users
- Follows your company's existing pattern
- Audit trail in Azure AD
- Consistent with MARS_Admin approach

**Cons:**
- Requires Azure AD admin involvement
- Sync delay (usually minutes)

### ❌ Direct User Assignment (My Initial Approach)
**Pros:**
- Immediate assignment
- No Azure AD dependency

**Cons:**
- Doesn't follow your company pattern
- Harder to manage multiple users
- No centralized audit in Azure AD
- Inconsistent with existing approach

---

## Summary of Actions

### Your Azure AD Admin Needs To:
1. ✅ Create Azure AD group: `AZP_AWS_NESANonProd_DataEngineer_Lakehouse`
2. ✅ Add Chen Chen to the group
3. ✅ Wait for sync (automatic)

### You (Cloud Engineer) Need To:
1. ✅ Verify group synced to AWS SSO
2. ✅ Create permission set `DataEngineer-Lakehouse` with inline policy
3. ✅ Assign permission set to group for NonProd account
4. ✅ Notify Chen Chen to logout/login to AWS SSO portal

### Chen Chen Will:
1. ✅ Login to AWS SSO portal
2. ✅ See new `DataEngineer-Lakehouse` permission set
3. ✅ Use it to access NonProd account
4. ✅ Implement lakehouse architecture

---

## Files Provided

1. **lakehouse-permission-set.json** - The IAM policy (ready to use)
2. **AZURE-AD-GROUP-APPROACH.md** - This document
3. **create-permission-set-for-group.sh** - CLI script (if you prefer CLI)

---

## Timeline

1. **Day 1**: Azure AD admin creates group, adds Chen Chen
2. **Day 1**: Wait for sync (15-30 minutes typically)
3. **Day 1**: You create permission set and assign to group
4. **Day 1**: Chen Chen can start working

**Total Time**: ~1 hour (mostly waiting for sync)

---

## Questions to Confirm

1. ✅ **Azure AD Group Naming**: Is `AZP_AWS_NESANonProd_DataEngineer_Lakehouse` acceptable?
2. ✅ **Sync Schedule**: How often does Azure AD sync to AWS SSO? (Usually automatic)
3. ✅ **Who Creates Groups**: Who is your Azure AD admin to create the group?
4. ✅ **Other Users**: Besides Chen Chen, who else needs lakehouse access?
5. ✅ **Production Timing**: When do you expect to move to Analytics account?

---

## Next Steps

**No rush to deploy** - Review this approach and:
1. Confirm the Azure AD group naming convention
2. Identify who will create the Azure AD group
3. Confirm Chen Chen is the only user for now
4. Let me know if you want me to prepare the CLI script for Step 3 & 4
