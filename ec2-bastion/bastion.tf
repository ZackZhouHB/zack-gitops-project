resource "aws_security_group" "launch-wizard-1" {
  name        = "launch-wizard-1"
  description = "launch-wizard-1 created 2023-12-10T10:45:49.619Z"
}

resource "aws_instance" "testbastion" {
  ami                    = "ami-0df4b2961410d4cff"
  key_name               = "terraform-new-key1"
  instance_type          = "t2.micro"
  vpc_security_group_ids = ["sg-0d26b562d826b91e9"]

  user_data = <<-EOF
    #!/bin/bash
    sudo apt update
    sudo apt install software-properties-common
    sudo add-apt-repository --yes --update ppa:ansible/ansible
    sudo apt install ansible -y
  EOF

}
resource "null_resource" "wait_for_bastion" {
  triggers = {
    # Add a dummy trigger to force a refresh
    timestamp = "${timestamp()}"
  }
  provisioner "remote-exec" {
    connection {
      type        = "ssh"
      user        = "ubuntu"
      private_key = file("terraform-new-key1.pem")
      host        = aws_instance.testbastion.public_ip
    }

    inline = [
      "until ansible --version; do sleep 5; done"
    ]
  }
}
# Upload playbook using file provisioner after Ansible is installed
resource "null_resource" "upload_playbook" {
  triggers = {
    # Add a dummy trigger to force a refresh
    timestamp = "${timestamp()}"
  }
  depends_on = [null_resource.wait_for_bastion]
  connection {
    type        = "ssh"
    user        = "ubuntu"
    private_key = file("terraform-new-key1.pem")
    host        = aws_instance.testbastion.public_ip
  }
  provisioner "file" {
    source      = "terraform-new-key1.pem"
    destination = "/home/ubuntu/terraform-new-key1.pem"
  }

  provisioner "file" {
    source      = "pb1.yaml"
    destination = "/home/ubuntu/pb1.yaml"
  }

  provisioner "file" {
    source      = "aws_ec2.yaml"
    destination = "/home/ubuntu/aws_ec2.yaml"
  }

  provisioner "file" {
    source      = "ansible.sh"
    destination = "/home/ubuntu/ansible.sh"
  }


  provisioner "remote-exec" {
    inline = [
      "cd /home/ubuntu/",
      "sudo chmod 600 terraform-new-key1.pem",
      "sudo chmod +x pb1.yaml",
      "sudo ansible-playbook pb1.yaml",
      "sudo chmod +x ansible.sh",
      "sudo ./ansible.sh",
      "sudo ansible-inventory -i aws_ec2.yaml --list",
      "sudo ansible-inventory --graph"

    ]
  }

}





