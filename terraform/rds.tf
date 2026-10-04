# ── RDS Subnet Group ─────────────────────────────────────────
resource "aws_db_subnet_group" "rds" {
  name        = "${var.environment}-rds-subnet-group"
  description = "Isolated subnets for Amazon RDS PostgreSQL instance"
  subnet_ids  = aws_subnet.database[*].id

  tags = {
    Name = "${var.environment}-rds-subnet-group"
  }
}

# ── RDS Parameter Group ──────────────────────────────────────
resource "aws_db_parameter_group" "pg16" {
  name        = "${var.environment}-pg16-params"
  family      = "postgres16"
  description = "Optimized parameters for cloud-native microservices"

  parameter {
    name  = "rds.force_ssl"
    value = "0"
  }

  tags = {
    Name = "${var.environment}-pg16-params"
  }
}

# ── Amazon RDS PostgreSQL Instance ───────────────────────────
resource "aws_db_instance" "postgres" {
  identifier             = "${var.environment}-platform-postgres"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage
  max_allocated_storage  = 50
  storage_type           = "gp3"

  db_name  = var.db_name
  username = var.db_username
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.rds.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  parameter_group_name   = aws_db_parameter_group.pg16.name

  publicly_accessible = false
  skip_final_snapshot = true
  deletion_protection = false

  tags = {
    Name = "${var.environment}-platform-postgres"
  }
}
