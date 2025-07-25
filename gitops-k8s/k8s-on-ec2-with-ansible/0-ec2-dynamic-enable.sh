#!/bin/bash
sudo apt update
sudo apt install software-properties-common -y
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt install ansible -y


ansible --version



sudo echo [defaults] > /etc/ansible/ansible.cfg
sudo echo [inventory] >> /etc/ansible/ansible.cfg
sudo echo [ssh_connection] >> /etc/ansible/ansible.cfg
sudo sed -i '/\[ssh_connection\]/a\ssh_args = -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' /etc/ansible/ansible.cfg
sudo sed -i '/\[inventory\]/a\enable_plugins = aws_ec2' /etc/ansible/ansible.cfg
sudo sed -i '/\[defaults\]/a\inventory = /home/ubuntu/aws_ec2.yaml' /etc/ansible/ansible.cfg
sudo sed -i '/aws_ec2.yaml/a\remote_user = ubuntu' /etc/ansible/ansible.cfg
sudo sed -i '/remote_user = ubuntu/a\private_key_file = /home/ubuntu/z101.pem' /etc/ansible/ansible.cfg