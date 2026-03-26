# =============================================================================
# Application Load Balancer
# =============================================================================

# -----------------------------------------------------------------------------
# ALB Security Group
# -----------------------------------------------------------------------------
resource "aws_security_group" "alb" {
  name_prefix = "${var.project_name}-alb-"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-alb"
  }
}

# -----------------------------------------------------------------------------
# ALB
# -----------------------------------------------------------------------------
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = data.aws_subnets.default.ids
  idle_timeout       = 120

  tags = {
    Project = var.project_name
  }
}

# -----------------------------------------------------------------------------
# Target Groups
# -----------------------------------------------------------------------------
resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-frontend"
  port        = 8501
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    path                = "/_stcore/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }
}

resource "aws_lb_target_group" "backend" {
  name        = "${var.project_name}-backend"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.default.id
  target_type = "ip"

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
  }

  stickiness {
    type    = "lb_cookie"
    enabled = false
  }
}

# -----------------------------------------------------------------------------
# Listener & Rules
# -----------------------------------------------------------------------------
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# Route API paths to backend
resource "aws_lb_listener_rule" "backend_chat" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/chat", "/chat/*", "/health", "/sessions", "/sessions/*"]
    }
  }
}
