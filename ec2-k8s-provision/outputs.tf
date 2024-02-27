output "master_public_ip" {
  value = aws_instance.kubernetes_instances[0].public_ip
}

output "worker_public_ips" {
  value = [for instance in aws_instance.kubernetes_instances : instance.public_ip]
}

output "ssh_command_master" {
  value = "ssh -i ec2-k8s.pem ubuntu@${aws_instance.kubernetes_instances[0].public_ip}"
}

output "ssh_commands_workers" {
  value = [for instance in aws_instance.kubernetes_instances : "ssh -i ec2-k8s.pem ubuntu@${instance.public_ip}"]
}
