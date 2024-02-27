provider "aws" {
  region = var.region
}

# Create a security group for the Kubernetes cluster
resource "aws_security_group" "kubernetes_sg" {
  name        = "kubernetes-sg"
  description = "Security group for Kubernetes cluster"

  # Allow communication within the cluster
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = [var.default_vpc_cidr_block]
  }

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Allow communication from bastion host
resource "aws_security_group_rule" "bastion_to_ec2-cluster" {
  type                     = "ingress"
  from_port                = 22
  to_port                  = 22
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.launch-wizard-1.id
  security_group_id        = aws_security_group.kubernetes_sg.id
}

resource "aws_instance" "kubernetes_instances" {
  count         = 3
  ami           = var.ami_id        # Specify your desired AMI
  instance_type = var.instance_type # Set your desired instance type
  subnet_id     = var.default_subnet_id

  key_name = var.key_pair # Specify the name of your key pair

  security_groups = [aws_security_group.kubernetes_sg.id]

  tags = {
    Name = "kubernetes-instance-${count.index}"
  }

  # Ensure the instance gets a public IP address
  associate_public_ip_address = true

  depends_on = [aws_security_group.kubernetes_sg]
}