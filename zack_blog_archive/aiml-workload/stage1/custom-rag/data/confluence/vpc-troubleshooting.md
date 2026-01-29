# AWS VPC Troubleshooting Guide

## Common Issues and Resolutions

### Issue: EC2 Instance Cannot Reach Internet

**Symptoms:**
- `ping 8.8.8.8` times out
- `yum update` fails
- Cannot download packages

**Resolution Steps:**
1. Check if instance is in a public subnet (has route to IGW)
2. Verify Security Group allows outbound traffic on port 443/80
3. Check NACL rules for the subnet
4. Ensure instance has public IP or is behind NAT Gateway
5. Verify route table has 0.0.0.0/0 -> igw-xxx or nat-xxx

**ServiceNow Ticket Reference:** INC0012345

---

### Issue: Cannot Connect to RDS from EC2

**Symptoms:**
- Connection timeout to RDS endpoint
- Application shows database connection errors

**Resolution Steps:**
1. Verify RDS Security Group allows inbound from EC2 SG
2. Check RDS is in same VPC or has VPC peering
3. Verify RDS subnet group includes AZs where EC2 runs
4. Check if RDS is publicly accessible (should be false for prod)
5. Test with: `nc -zv <rds-endpoint> 3306`

**ServiceNow Ticket Reference:** INC0012456

---

### Issue: VPC Peering Not Working

**Symptoms:**
- Cannot ping across peered VPCs
- Applications cannot communicate cross-VPC

**Resolution Steps:**
1. Check peering connection status is "Active"
2. Verify route tables in BOTH VPCs have routes to peer
3. Check Security Groups allow traffic from peer CIDR
4. Ensure no overlapping CIDR blocks
5. Check NACLs in both VPCs

**ServiceNow Ticket Reference:** INC0012567

---

## Escalation Path

1. L1: Cloud Operations Team (cloud-ops@company.com)
2. L2: Network Engineering (network-eng@company.com)
3. L3: AWS TAM (for Enterprise Support customers)

## Related Documentation

- VPC Design Document: SharePoint/Cloud/VPC-Design-v2.pdf
- Network Diagram: Confluence/Infrastructure/Network-Topology
