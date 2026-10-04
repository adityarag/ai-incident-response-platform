variable "aws_region" {
  description = "AWS deployment region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "staging"
}

variable "cluster_name" {
  description = "Name of the Amazon EKS cluster"
  type        = string
  default     = "incident-platform-eks"
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets (EKS nodes & pods)"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.20.0/24"]
}

variable "database_subnet_cidrs" {
  description = "CIDR blocks for isolated database subnets (RDS PostgreSQL)"
  type        = list(string)
  default     = ["10.0.30.0/24", "10.0.40.0/24"]
}

variable "eks_node_instance_types" {
  description = "EC2 instance types for EKS managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "eks_min_size" {
  description = "Minimum number of worker nodes in EKS node group"
  type        = number
  default     = 1
}

variable "eks_desired_size" {
  description = "Desired number of worker nodes in EKS node group"
  type        = number
  default     = 2
}

variable "eks_max_size" {
  description = "Maximum number of worker nodes in EKS node group"
  type        = number
  default     = 4
}

variable "db_instance_class" {
  description = "Instance class for Amazon RDS PostgreSQL"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "Allocated storage in GB for RDS PostgreSQL"
  type        = number
  default     = 20
}

variable "db_name" {
  description = "Initial database name for RDS PostgreSQL"
  type        = string
  default     = "incident_platform"
}

variable "db_username" {
  description = "Master username for RDS PostgreSQL"
  type        = string
  default     = "platform_admin"
}

variable "db_password" {
  description = "Master password for RDS PostgreSQL"
  type        = string
  sensitive   = true
  default     = "changeme_in_production_secure_pwd"
}
