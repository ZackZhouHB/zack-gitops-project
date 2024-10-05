variable "service_name" {}
variable "cluster_arn" {}
variable "task_definition_arn" {}
variable "subnets" { type = list(string) }
variable "security_groups" { type = list(string) }
variable "desired_count" { default = 2 }
variable "target_group_arn" {}
variable "container_name" {}
variable "container_port" {}
variable "dependency" {}
