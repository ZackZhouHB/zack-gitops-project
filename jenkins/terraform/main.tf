provider "aws" {
  region = "ap-southeast-2"
}

# Security Group Data
data "aws_security_group" "existing_sg" {
  filter {
    name   = "group-name"
    values = ["launch-wizard-1"]
  }
}

# Key Pair Data
data "aws_key_pair" "existing_key" {
  key_name = "zhbsoftboy20240406"
}

# EC2 Instance Definition
resource "aws_instance" "web" {
  ami           = "ami-040e71e7b8391cae4" # Choose your AMI
  instance_type = "t2.micro"
  key_name      = data.aws_key_pair.existing_key.key_name
  security_groups = [
    data.aws_security_group.existing_sg.name
  ]

  user_data = <<-EOF
              #!/bin/bash
              sudo apt-get update
              sudo apt-get install -y docker.io
              sudo systemctl start docker
              sudo systemctl enable docker
              sudo docker pull zackz001/jenkins:latest
              sudo docker run -d --restart unless-stopped -p 80:80 zackz001/jenkins:latest
              EOF

  tags = {
    Name = "Jenkins-EC2"
  }
}

# Output EC2 Public IP
output "ec2_public_ip" {
  value = aws_instance.web.public_ip
}
