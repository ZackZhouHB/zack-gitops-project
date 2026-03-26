resource "aws_efs_file_system" "chat_history" {
  creation_token = "${var.project_name}-efs"
  encrypted      = true

  tags = {
    Name = "${var.project_name}-chat-history"
  }
}

resource "aws_efs_mount_target" "chat_history" {
  for_each = toset(data.aws_subnets.default.ids)

  file_system_id  = aws_efs_file_system.chat_history.id
  subnet_id       = each.value
  security_groups = [aws_security_group.efs.id]
}

resource "aws_security_group" "efs" {
  name_prefix = "${var.project_name}-efs-"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-efs"
  }
}
