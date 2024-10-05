resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.role_prefix}-ecsTaskExecutionRole"  # Use variable for unique name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_task_execution_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = var.execution_policy_arn  # Parameterized
}

resource "aws_iam_role" "ecs_task_role" {
  name = "${var.role_prefix}-ecsTaskRole"  # Use variable for unique name

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}
