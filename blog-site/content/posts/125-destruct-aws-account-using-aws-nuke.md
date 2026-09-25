---
title: "Destruct AWS account using AWS-Nuke"
date: 2025-02-18T08:16:01Z
slug: destruct-aws-account-using-aws-nuke
categories: ["AWS"]
aliases: ["/post/125/"]
legacy_id: 125
---
Here's a summary of the actions I took to delete an AWS account using an open source tool `aws-nuke` as it is at the end of free tier I donot need it anymore to aviod cost:

**1. Install [aws-nuke](https://github.com/ekristen/aws-nuke/blob/main/docs/quick-start.md):**

```bash
apt install aws-nuke
```

This command installs `aws-nuke`, a tool used to delete AWS resources in an account. It requires AWS credentials and the correct configuration file to specify what resources to remove.

**2. Create a nuke-config.yaml, which will be used during execution:**

```bash
root@zackz:/mnt/f/aws-nuke# vim nuke-config.yaml

regions:
  - ap-southeast-2
  - global

account-blocklist:
  - "85xxxxxxxx42"  # production account ID

accounts:
  "85xxxxxxxx15":   # Joe Account to be deleted
    filters:
      IAMUser:
        - "nuke"     # the user excluded from deletion action
      IAMUserPolicyAttachment:
        - "nuke -> AdministratorAccess"
      IAMUserAccessKey:
        - "nuke -> AKIA4MTWMCWF7T6HLYXE"
```

**regions:** Specifies which AWS regions the `aws-nuke` tool should scan.
**account-blocklist:** Ensures that certain accounts (like the production account) are not accidentally nuked.
**accounts:** Lists the accounts to be nuked and specifies any filters for exclusions (like the user "nuke" in this case). Filters prevent specific resources, like users or keys, from being deleted.
I execluded a user nuke so it can perform the remove action.

**3. Ensure AWS Credentials:**

Before running the command, make sure the AWS CLI is configured with credentials (using `aws configure` or a profile). I tested the credentials with:

```bash
root@zackz:/mnt/f/aws-nuke# ls -l ~/.aws/
total 8
drwxrwxrwx 1 root root  512 Oct 11 16:24 amazonq
drwxrwxrwx 1 root root  512 Sep  5 14:11 cli
-rwxrwxrwx 1 root root 6617 Feb 18 18:44 config
-rwxrwxrwx 1 root root  142 Feb 18 14:49 credentials
drwxrwxrwx 1 root root  512 Sep  5 14:11 sso

aws iam list-account-aliases --profile joe
```

This command checks if the alias for the `joe` account exists. If no alias exists, you must create one.

**4. Create an Account Alias:**

```bash
aws iam create-account-alias --account-alias aws-joe-85xxxxxxxx15 --profile joe
```

AWS requires an account alias for the `aws-nuke` process. Since my account did not have an alias, I just created one. The alias is important for `aws-nuke` because it checks the alias before proceeding with deletion to prevent accidentally deleting important accounts. If an alias is already taken, you need to choose a different one.

**5. Run aws-nuke with Dry-Run:**

```text
aws-nuke --profile joe --config /mnt/f/aws-nuke/nuke-config.yaml

aws-nuke version unknown - unknown - unknown

Do you really want to nuke the account with the ID 85xxxxxxxx15 and the alias 'aws-joe-85xxxxxxxx15'?
Do you want to continue? Enter account alias to continue.
> aws-joe-85xxxxxxxx15

ap-southeast-2 - EC2Instance - i-05xxxxxxxxxx7efc - [Identifier: "i-05xxxxxxxxxxefc", ImageIdentifier: "ami-09c8d5d747253fb7a", InstanceState: "running", InstanceType: "t2.micro", LaunchTime: "2024-03-17T08:51:40Z", tag:Application: "bb", tag:Businessunit: "dd", tag:Dataclassification: "aa", tag:Environment: "cc", tag:MSP-managed: "ee", tag:Name: "joe-site"] - would remove
global - IAMRolePolicyAttachment - AWSServiceRoleForTrustedAdvisor -> AWSTrustedAdvisorServiceRolePolicy - [PolicyArn: "arn:aws:iam::aws:policy/aws-service-role/AWSTrustedAdvisorServiceRolePolicy", PolicyName: "AWSTrustedAdvisorServiceRolePolicy", RoleName: "AWSServiceRoleForTrustedAdvisor"] - cannot detach from service roles
global - IAMRolePolicyAttachment - k8s-master-role -> k8s-ec2-master-policy - [PolicyArn: "arn:aws:iam::85xxxxxxxx15:policy/k8s-ec2-master-policy", PolicyName: "k8s-ec2-master-policy", RoleName: "k8s-master-role"] - would remove
global - IAMRolePolicyAttachment - k8s-worker-role -> k8s-worker-policy - [PolicyArn: "arn:aws:iam::85xxxxxxxx15:policy/k8s-worker-policy", PolicyName: "k8s-worker-policy", RoleName: "k8s-worker-role"] - would remove

Scan complete: 126 total, 52 nukeable, 74 filtered.

The above resources would be deleted with the supplied configuration. Provide --no-dry-run to actually destroy resources.
```

Dry-run allows you to see which resources will be deleted without actually performing the deletion. This is crucial for verifying the configuration before executing the destructive operation.

**6. Confirm the Resources to be Nuked:**

During the dry run, `aws-nuke` listed resources like EC2 instances, IAM roles, policies, and security groups that would be removed. You can review the list to ensure that only the intended resources are being marked for deletion.

**7. Run aws-nuke with --no-dry-run to Actually Delete:**

```bash
root@zackz:/mnt/f/aws-nuke# aws-nuke --profile joe --config /mnt/f/aws-nuke/nuke-config.yaml --no-dry-run
aws-nuke version unknown - unknown - unknown

Do you really want to nuke the account with the ID 85xxxxxxxx15 and the alias 'aws-joe-85xxxxxxxx15'?
Do you want to continue? Enter account alias to continue.
> aws-joe-85xxxxxxxx15

ERRO[0014] Listing CloudSearchDomain failed:
    NotAuthorized: New domain creation not supported on this account. Please reach out to AWS Support for assistance.
        status code: 401, request id: c46572cb-2f72-41d7-ad7c-64ebe2dfb41a
ap-southeast-2 - EC2Instance - i-052b0511339457efc - [Identifier: "i-052b0511339457efc", ImageIdentifier: "ami-09c8d5d747253fb7a", InstanceState: "running", InstanceType: "t2.micro", LaunchTime: "2024-03-17T08:51:40Z", tag:Application: "bb", tag:Businessunit: "dd", tag:Dataclassification: "aa", tag:Environment: "cc", tag:MSP-managed: "ee", tag:Name: "joe-site"] - would remove
ap-southeast-2 - CloudWatchEventsTarget - Rule: AutoScalingManagedRule Target ID: autoscaling - would remove
ap-southeast-2 - EC2InternetGatewayAttachment - igw-0df8477f1aab5f7c2 -> vpc-0f5edc76a16636145 - [] - would remove
ap-southeast-2 - EC2SecurityGroup - sg-087d7e1df8bf8197a - [Name: "launch-wizard-2"] - triggered remove
ap-southeast-2 - EC2SecurityGroup - sg-089842a753c9309bb - [Name: "blog-sg"] - triggered remove
ap-southeast-2 - EC2Subnet - subnet-04dc2cab029adbd46 - [DefaultForAz: "true"] - triggered remove
ap-southeast-2 - EC2RouteTable - rtb-098b56bf20b6d2f97 - [] - failed
ap-southeast-2 - EC2VPC - vpc-0f5edc76a16636145 - [ID: "vpc-0f5edc76a16636145", IsDefault: "true"] - failed
ap-southeast-2 - EC2InternetGatewayAttachment - igw-0df8477f1aab5f7c2 -> vpc-0f5edc76a16636145 - [] - triggered remove
ap-southeast-2 - EC2DHCPOption - dopt-0f0b2ab768476bd8e - [] - failed
ap-southeast-2 - EC2InternetGateway - igw-0df8477f1aab5f7c2 - [] - triggered remove
global - IAMGroup - z101_admin_group - triggered remove
global - IAMVirtualMFADevice - arn:aws:iam::85xxxxxxxx15:mfa/z101-joe - failed
global - IAMPolicy - arn:aws:iam::85xxxxxxxx15:policy/k8s-worker-policy - [ARN: "arn:aws:iam::85xxxxxxxx15:policy/k8s-worker-policy", Name: "k8s-worker-policy", Path: "/", PolicyID: "ANPA4MTWMCWFXWYIWRI7S"] - triggered remove
global - IAMPolicy - arn:aws:iam::85xxxxxxxx15:policy/k8s-ec2-master-policy - [ARN: "arn:aws:iam::85xxxxxxxx15:policy/k8s-ec2-master-policy", Name: "k8s-ec2-master-policy", Path: "/", PolicyID: "ANPA4MTWMCWFZY4I4LD2S"] - triggered remove
global - IAMUser - BobJ - triggered remove
global - IAMUser - infra_team_user - triggered remove
global - IAMUser - joe - triggered remove
global - IAMUser - MattS - triggered remove
global - IAMUser - ZackZ - triggered remove
global - IAMRole - k8s-master-role - [Name: "k8s-master-role", Path: "/"] - triggered remove
global - IAMRole - k8s-worker-role - [Name: "k8s-worker-role", Path: "/"] - triggered remove

Removal requested: 15 waiting, 2 failed, 78 skipped, 2 finished
```

The `--no-dry-run` flag actually trigger and performs the deletion, removing the specified resources from the AWS account. You were prompted to confirm the deletion by entering the account alias (`aws-joe-85xxxxxxxx15`) twice to prevent accidental nuking.

[![image tooltip here](/images/nuke3.png)](/images/nuke3.png)

**8. Encountered Errors and Failures:**

During the final run, I encountered one error:

- **Failed Removal of one Resources:** Resources such as `IAMVirtualMFADevice` failed after 3 times attempts due to issues like the device being in use, so maybe we need to remove all MFADevice configuration before we start nuke an account.

**9. Once close account, you will not be able to console login anymore :**

[![image tooltip here](/images/nuke2.png)](/images/nuke2.png)

**Key Takeaways:**

- **Why Create an Account Alias:** AWS requires an account alias for safety purposes. This prevents accidental deletions by ensuring that only the intended account is nuked.
- **Why Use Filters:** Filters prevent critical resources (like specific IAM users or access keys) from being deleted.
- **Dry Run Is Crucial:** Always perform a dry run to verify what resources are marked for deletion, after nuke, there will be only the last user in the filter and the IAMVirtualMFADevice left.
- **After aws-nuke:** You can see from above, many default resources had been already deleted, which make the account unable to be reused, so this is a tool best for account resource final clean before close .
