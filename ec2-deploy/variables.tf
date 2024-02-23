variable "region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"
}

variable "default_vpc_id" {
  description = "vpc-04344774f8470fd0f"
}

variable "default_subnet_id" {
  description = "subnet-0f95f94337c008c52"
}

variable "default_vpc_cidr_block" {
  description = "CIDR block for the VPC"
  default     = "172.31.0.0/16"
}

variable "ami_id" {
  description = "AMI ID for the EC2 instances"
  default     = "ami-04f5097681773b989" # Specify your desired default AMI ID
}

variable "instance_type" {
  description = "EC2 instance type"
  default     = "t2.micro" # Specify your desired default instance type
}

variable "key_pair" {
  description = "Name of the existing key pair for SSH access"
  default     = "terraform-new-key1" # Specify the name of your key pair
}

variable "availability_zones" {
  description = "Availability Zone for subnets"
  default     = "ap-southeast-2a, ap-southeast-2b, ap-southeast-2c"
}

variable "my_ip" {
  description = "Your public IP address"
  type        = string
  default     = "163.53.144.82/32"
}