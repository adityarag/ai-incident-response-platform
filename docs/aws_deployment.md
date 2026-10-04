# AWS Cloud Deployment & Infrastructure Guide

## Overview

The platform uses Infrastructure-as-Code (IaC) with **Terraform** to provision a resilient, secure, and production-ready AWS cloud infrastructure.

```
                                  AWS Cloud
  ┌────────────────────────────────────────────────────────────────────────┐
  │ VPC (10.0.0.0/16)                                                      │
  │                                                                        │
  │  Public Subnets (AZ-1a, AZ-1b)                                         │
  │  ┌──────────────────────────────────────────────────────────────────┐  │
  │  │ Internet Gateway + NAT Gateway                                   │  │
  │  │ Application Load Balancer (ALB)                                  │  │
  │  └───────────────────────────────┬──────────────────────────────────┘  │
  │                                  │                                     │
  │  Private Subnets (AZ-1a, AZ-1b)  ▼                                     │
  │  ┌──────────────────────────────────────────────────────────────────┐  │
  │  │ Amazon EKS Managed Node Group (t3.medium)                        │  │
  │  │                                                                  │  │
  │  │   [api-gateway]       [order-service]       [payment-service]    │  │
  │  │         │                    │                     │             │  │
  │  └─────────┼────────────────────┼─────────────────────┼─────────────┘  │
  │            │                    │                     │                │
  │            ▼                    ▼                     ▼                │
  │  Database Subnets                                                      │
  │  ┌──────────────────────────────────────────────────────────────────┐  │
  │  │ Amazon RDS PostgreSQL 16 (db.t4g.micro / Isolated)               │  │
  │  └──────────────────────────────────────────────────────────────────┘  │
  └────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Cloud Architecture Components

| Component | AWS Resource | Purpose |
|---|---|---|
| **VPC & Subnets** | `aws_vpc`, `aws_subnet` | Dual-AZ virtual private cloud (10.0.0.0/16) with public, private, and database subnets |
| **Container Registry** | `aws_ecr_repository` | Private Docker registries with automated vulnerability scanning on push |
| **Kubernetes Control Plane**| `aws_eks_cluster` | Managed Amazon EKS control plane (v1.30) |
| **Worker Nodes** | `aws_eks_node_group` | Auto-scaling managed EC2 node group (`t3.medium`) |
| **Managed Database** | `aws_db_instance` | Amazon RDS PostgreSQL 16 instance with automated storage autoscaling |
| **Network Security** | `aws_security_group` | Strict security groups preventing direct public database access |

---

## 2. Security Guardrails

1. **Database Isolation**: The RDS PostgreSQL instance resides exclusively inside private database subnets with `publicly_accessible = false`. The security group only permits inbound port `5432` traffic originating from the EKS nodes security group.
2. **Container Security**: ECR repositories enforce `scan_on_push = true` to detect vulnerabilities in container images.
3. **IAM Least Privilege**: EKS cluster and node groups operate under isolated IAM roles with strictly scoped AWS-managed policies.
4. **Zero Hardcoded Secrets**: All passwords and API credentials are parameterized via sensitive Terraform variables and runtime Kubernetes Secrets.

---

## 3. Step-by-Step Deployment

### Prerequisites
- AWS CLI v2 configured (`aws configure`)
- Terraform >= 1.5.0
- Docker Desktop
- `kubectl`

### Quick Deployment via Automation Script
```bash
# 1. Set environment variables
export AWS_REGION="us-east-1"
export ENVIRONMENT="staging"

# 2. Run automated provisioning and deployment
./scripts/aws_deploy.sh
```

### Manual Step-by-Step Execution
```bash
# Step 1: Provision Infrastructure with Terraform
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# Step 2: Configure kubectl Context
aws eks --region us-east-1 update-kubeconfig --name incident-platform-eks

# Step 3: Build & Push Images to ECR
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BASE="${ACCOUNT_ID}.dkr.ecr.us-east-1.amazonaws.com"
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin "${ECR_BASE}"

docker build -t "${ECR_BASE}/staging-platform-api-gateway:latest" -f services/api-gateway/Dockerfile .
docker push "${ECR_BASE}/staging-platform-api-gateway:latest"

# Step 4: Apply Kubernetes Manifests
kubectl apply -k k8s/
```

---

## 4. Cost Optimization & Teardown

To avoid unnecessary cloud spending during academic evaluations and student development:

- Node groups utilize economical `t3.medium` instances with scale-down minimum of 1 node.
- ECR includes lifecycle policies that automatically prune images older than 14 days.
- **Immediate Teardown**: Run the automated teardown script when testing is complete:

```bash
./scripts/aws_teardown.sh
```
