resource "aws_instance" "blog" {
  ami = "ami-0df4b2961410d4cff"

  instance_type = "t2.micro"

  connection {
    type        = "ssh"
    user        = "ubuntu"                       # Replace with your EC2 user
    private_key = file("terraform-new-key1.pem") # Replace with the path to your private key
    host        = self.public_ip
  }

  provisioner "file" {
    source      = "terraform-new-key1.pem"
    destination = "/home/ubuntu/terraform-new-key1.pem"
  }

  provisioner "file" {
    source      = "ansible.sh"
    destination = "/home/ubuntu/ansible.sh"
  }

  provisioner "remote-exec" {
    inline = [
      "cd /home/ubuntu/",
      "sudo chmod 600 terraform-new-key1.pem",
      "sudo chmod +x ansible.sh",
      "sudo ./ansible.sh",
      "sudo ansible-inventory -i aws_ec2.yaml --list",
      "sudo ansible-inventory --graph"
      ]
  }

  provisioner "file" {
    source      = "aws_ec2.yaml"
    destination = "etc/ansible/aws_ec2.yaml"
  }
}

resource "aws_security_group" "launch-wizard-1" {
  name        = "launch-wizard-1"
  description = "launch-wizard-1 created 2023-12-10T10:45:49.619Z"

}

resource "aws_ebs_volume" "blog_ebs" {
  # No configuration is specified here
  availability_zone = "ap-southeast-2b"
  type              = "gp2"
  size              = 8
}

