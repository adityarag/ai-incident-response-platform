locals {
  services = [
    "api-gateway",
    "order-service",
    "payment-service",
    "migrations"
  ]
}

resource "aws_ecr_repository" "repos" {
  for_each             = toset(locals.services)
  name                 = "${var.environment}-platform-${each.key}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name    = "${var.environment}-platform-${each.key}"
    Service = each.key
  }
}

resource "aws_ecr_lifecycle_policy" "pruning" {
  for_each   = aws_ecr_repository.repos
  repository = each.value.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images to manage storage costs"
        selection = {
          tagStatus   = "any"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 14
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}
