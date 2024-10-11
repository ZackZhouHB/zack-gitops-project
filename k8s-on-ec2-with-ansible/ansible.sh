#!/bin/bash

sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt install ansible -y
sudo apt-get install python3 -y
sudo apt-get install python3-pip -y
pip3 install boto3

ansible --version



echo [defaults] > /etc/ansible/ansible.cfg
echo [inventory] >> /etc/ansible/ansible.cfg
echo [ssh_connection] >> /etc/ansible/ansible.cfg
sed -i '/\[ssh_connection\]/a\ssh_args = -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' /etc/ansible/ansible.cfg
sed -i '/\[inventory\]/a\enable_plugins = aws_ec2' /etc/ansible/ansible.cfg
sed -i '/\[defaults\]/a\inventory = /home/ubuntu/aws_ec2.yaml' /etc/ansible/ansible.cfg
sed -i '/aws_ec2.yaml/a\remote_user = ubuntu' /etc/ansible/ansible.cfg
sed -i '/remote_user = ubuntu/a\private_key_file = /home/ubuntu/terraform-new-key1.pem' /etc/ansible/ansible.cfg