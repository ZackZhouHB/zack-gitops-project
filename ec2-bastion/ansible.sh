#!/bin/bash

ansible --version



echo [defaults] > /etc/ansible/ansible.cfg
echo [inventory] >> /etc/ansible/ansible.cfg
echo [ssh_connection] >> /etc/ansible/ansible.cfg
sed -i '/\[ssh_connection\]/a\ssh_args = -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null' /etc/ansible/ansible.cfg
sed -i '/\[inventory\]/a\enable_plugins = aws_ec2' /etc/ansible/ansible.cfg
sed -i '/\[defaults\]/a\inventory = /home/ubuntu/aws_ec2.yaml' /etc/ansible/ansible.cfg
sed -i '/aws_ec2.yaml/a\remote_user = ubuntu' /etc/ansible/ansible.cfg
sed -i '/remote_user = ubuntu/a\private_key_file = /home/ubuntu/terraform-new-key1.pem' /etc/ansible/ansible.cfg