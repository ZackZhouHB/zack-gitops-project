# Migration To New AWS Account (Free Tier Refresh)

## Context

- Current app is the Django website under `django_project/`.
- Current deployment region is `ap-southeast-2`.
- Current deployment model is:
  - GitHub Actions builds image and pushes to Docker Hub.
  - GitHub Actions SSHes into EC2 and runs Docker container.
  - Cloudflare fronts the domain `zackblog.work`.

Target migration window: around **March 17, 2026**.

## Reusable Infra Assets Prepared In Repo

Created under:

- `django_project/aws_migration/`

Contents:

- `django_project/aws_migration/cloudformation/ec2-django-origin.yaml`
- `django_project/aws_migration/scripts/deploy_stack.sh`
- `django_project/aws_migration/scripts/delete_stack.sh`
- `django_project/aws_migration/README.md`

Purpose:

- Recreate EC2 + SG in a new AWS account with current-like settings.
- Bootstrap instance via user-data (install Docker/Git and clone repo).
- Reuse the same scripts for future rebuilds.

## Validated Findings (Current Environment)

### 1. GitHub Actions workflow

- Workflow file: `.github/workflows/zack-django.yaml`
- Trigger: push to `editing` (for `django_project/**`) and PR to `main`.
- CI/CD actions:
  - Build and tag Docker image `zackz001/zackblog-django`.
  - Push image to Docker Hub (`latest` + versioned tag).
  - Configure AWS credentials with secrets.
  - SSH to EC2 and deploy container:
    - pull latest image
    - stop/remove old container
    - run new container on `-p 80:8000`
- Workflow AWS region: `ap-southeast-2`.

### 2. Current AWS EC2

- Instance ID: `i-043528a1948e9a8b9`
- Name tag: `zackblog`
- State: `running`
- Type: `t2.micro`
- AZ: `ap-southeast-2a`
- Public IP: `54.252.169.101`
- Key pair name: `aws20250317key`
- SSH access with local key is confirmed working.

### 3. DNS and Cloudflare

- `zackblog.work` is proxied by Cloudflare (edge IPs resolve).
- Nameservers are Cloudflare-managed.
- Public HTTPS response includes `server: cloudflare`.
- Conclusion: Cloudflare is in front of origin as expected.

### 4. SSL/TLS state

- Public certificate presented to users is currently valid (Cloudflare edge cert).
- On EC2:
  - Nginx is installed but inactive.
  - Old Let's Encrypt certificate exists and is expired.
  - Docker container serves the app on port 80.
- Conclusion: production TLS is effectively terminated at Cloudflare now.

### 5. Security group (current)

- Inbound currently allows:
  - `22/tcp` from `0.0.0.0/0`
  - `80/tcp` from `0.0.0.0/0`
  - `443/tcp` from `0.0.0.0/0`
  - `8000/tcp` from `0.0.0.0/0`
- Note: `8000` is unnecessary if Docker publishes on `80`.

## Migration Plan (New AWS Account)

### Phase 1: Prepare new account (before cutover day)

1. Create new AWS account and use region `ap-southeast-2`.
2. Create IAM user for GitHub Actions deployment.
3. Create new EC2 key pair and store `.pem` securely.
4. Use repo infra to create EC2 + SG:
   - `cd django_project/aws_migration`
   - run `./scripts/deploy_stack.sh ...` with new account profile, key name, VPC, subnet
5. Confirm stack outputs (instance ID, public IP, SG ID).

### Phase 2: Update CI/CD secrets (same repo)

Update GitHub repository secrets:

1. `AWS_ACCESS_KEY_ID` -> new account IAM key
2. `AWS_SECRET_ACCESS_KEY` -> new account IAM secret
3. `HOST_NAME` -> new EC2 public IP or DNS
4. `SSH_PRIVATE_KEY` -> new key pair private key
5. `USER_NAME` -> `ubuntu` (if Ubuntu AMI)

### Phase 3: Deploy and validate on new EC2

1. Trigger workflow from `editing` branch with a small commit to `django_project/**`.
2. Verify workflow can:
   - build image
   - push image
   - SSH into new host
   - run container successfully
3. Validate origin directly:
   - `http://<new-ec2-public-ip>` should return app response.

Suggested deploy command (to run on migration day):

```bash
cd django_project/aws_migration

./scripts/deploy_stack.sh \
  --profile default \
  --region ap-southeast-2 \
  --stack-name zackblog-migration-ec2 \
  --key-name <new-keypair-name> \
  --vpc-id <vpc-id> \
  --subnet-id <subnet-id> \
  --ssh-cidr <your-public-ip/32>
```

### Phase 4: Cloudflare cutover (final migration day)

1. In Cloudflare DNS, update `A` record(s) for:
   - `zackblog.work`
   - `www` (if used)
   to the new EC2 public IP.
2. Keep Cloudflare proxy enabled.
3. Validate:
   - `https://zackblog.work` loads correctly
   - app login and core pages work
   - GitHub Actions deploy still works end-to-end.

### Phase 5: Post-cutover cleanup

1. Keep old EC2 running for 24-48 hours as rollback.
2. If stable, stop and terminate old EC2.
3. Remove old IAM keys/secrets no longer needed.
4. Tighten security group rules further if possible.

## Notes for March 17, 2026 Session

- Free tier is tied to account age, not PEM key age.
- Use this checklist as the runbook on migration day.
- Infrastructure creation should use `django_project/aws_migration/` assets first, not manual console clicks.
- During cutover, prioritize:
  1. successful deploy to new EC2
  2. DNS switch in Cloudflare
  3. validation tests
  4. controlled decommission of old resources
