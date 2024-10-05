resource "aws_lb" "app" {
  name               = var.name        # Parameterized
  internal           = var.internal    # Parameterized
  load_balancer_type = var.load_balancer_type  # Optional but useful
  security_groups    = var.security_groups
  subnets            = var.subnets
}

resource "aws_lb_target_group" "app" {
  name        = var.target_group_name  # Parameterized
  port        = var.target_group_port  # Parameterized
  protocol    = var.target_group_protocol  # Parameterized
  vpc_id      = var.vpc_id
  target_type = var.target_type  # Parameterized

  health_check {
    path                = var.health_check_path
    interval            = var.health_check_interval
    timeout             = var.health_check_timeout
    healthy_threshold   = var.healthy_threshold
    unhealthy_threshold = var.unhealthy_threshold
    matcher             = var.matcher
  }
}

resource "aws_lb_listener" "front_end" {
  load_balancer_arn = aws_lb.app.arn
  port              = var.listener_port
  protocol          = var.listener_protocol  # Parameterized

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.app.arn
  }
}
