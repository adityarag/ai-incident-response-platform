output "vpc_id" {
  description = "ID of the created AWS VPC"
  value       = aws_vpc.main.id
}

output "eks_cluster_name" {
  description = "Name of the Amazon EKS cluster"
  value       = aws_eks_cluster.main.name
}

output "eks_cluster_endpoint" {
  description = "Endpoint URL for Amazon EKS control plane"
  value       = aws_eks_cluster.main.endpoint
}

output "eks_cluster_certificate_authority_data" {
  description = "Base64 encoded certificate data required to communicate with the cluster"
  value       = aws_eks_cluster.main.certificate_authority[0].data
  sensitive   = true
}

output "rds_endpoint" {
  description = "Connection endpoint hostname for Amazon RDS PostgreSQL"
  value       = aws_db_instance.postgres.endpoint
}

output "rds_address" {
  description = "Host address for Amazon RDS PostgreSQL"
  value       = aws_db_instance.postgres.address
}

output "ecr_repository_urls" {
  description = "URLs of the created Amazon ECR container registries"
  value       = { for k, v in aws_ecr_repository.repos : k => v.repository_url }
}

output "kubeconfig_command" {
  description = "AWS CLI command to update local kubeconfig for the EKS cluster"
  value       = "aws eks --region ${var.aws_region} update-kubeconfig --name ${aws_eks_cluster.main.name}"
}
