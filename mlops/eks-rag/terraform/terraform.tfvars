aws_region = "ap-southeast-2"
aws_profile = "sandboxtest"

vpc_cidr = "10.0.0.0/16"

# Optimal spot instances: t3.large at ~$0.077/hour with burstable performance
node_group_instance_types = ["t3.large"]
node_group_min_size = 2
node_group_max_size = 3
node_group_desired_size = 2
