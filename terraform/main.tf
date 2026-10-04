terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.30"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AI-Incident-Response-Platform"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Owner       = "BIT-Mesra-Minor-Project"
    }
  }
}
