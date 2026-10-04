# ── Application Load Balancer Security Group ──────────────────
resource "aws_security_group" "alb" {
  name        = "${var.environment}-alb-sg"
  description = "Controls HTTP/HTTPS ingress traffic to the Application Load Balancer"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "Allow inbound HTTP from internet"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Allow inbound HTTPS from internet"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound traffic to cluster nodes"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-alb-sg"
  }
}

# ── EKS Cluster Security Group ────────────────────────────────
resource "aws_security_group" "eks_cluster" {
  name        = "${var.environment}-eks-cluster-sg"
  description = "Security group for EKS control plane communication"
  vpc_id      = aws_vpc.main.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-eks-cluster-sg"
  }
}

# ── EKS Nodes Security Group ──────────────────────────────────
resource "aws_security_group" "eks_nodes" {
  name        = "${var.environment}-eks-nodes-sg"
  description = "Security group for EKS worker nodes and pod networking"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow traffic from ALB into NodePort / Pod endpoints"
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description = "Allow internal pod-to-pod communication"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-eks-nodes-sg"
  }
}

# ── RDS PostgreSQL Security Group ─────────────────────────────
resource "aws_security_group" "rds" {
  name        = "${var.environment}-rds-sg"
  description = "Controls PostgreSQL datastore ingress from EKS nodes only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "Allow PostgreSQL access strictly from EKS worker nodes"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.eks_nodes.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.environment}-rds-sg"
  }
}
