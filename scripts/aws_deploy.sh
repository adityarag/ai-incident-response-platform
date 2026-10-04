#!/usr/bin/env bash
# ==============================================================================
# AWS Cloud Deployment Automation Script
# AI-Powered Incident Response and Self-Healing Platform
# ==============================================================================
set -euo pipefail

REGION="${AWS_REGION:-us-east-1}"
ENV="${ENVIRONMENT:-staging}"
CLUSTER_NAME="${CLUSTER_NAME:-incident-platform-eks}"

echo "============================================================"
echo " Starting AWS Cloud Deployment: ${ENV} (${REGION})"
echo "============================================================"

# 1. Initialize and Apply Terraform
echo "[*] Step 1: Initializing and applying Terraform..."
cd terraform
terraform init
terraform plan -out=tfplan
terraform apply -auto-approve tfplan

# 2. Extract Outputs
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_BASE="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
cd ..

# 3. Authenticate with Amazon ECR
echo "[*] Step 2: Authenticating with Amazon ECR..."
aws ecr get-login-password --region "${REGION}" | docker login --username AWS --password-stdin "${ECR_BASE}"

# 4. Build and Push Container Images
echo "[*] Step 3: Building and pushing container images to ECR..."
services=("api-gateway" "order-service" "payment-service" "migrations")
dockerfiles=(
  "services/api-gateway/Dockerfile"
  "services/order-service/Dockerfile"
  "services/payment-service/Dockerfile"
  "database/Dockerfile"
)

for i in "${!services[@]}"; do
  svc="${services[$i]}"
  df="${dockerfiles[$i]}"
  repo_tag="${ECR_BASE}/${ENV}-platform-${svc}:latest"
  echo "  -> Building and pushing ${svc}..."
  docker build -t "${repo_tag}" -f "${df}" .
  docker push "${repo_tag}"
done

# 5. Configure kubectl Context
echo "[*] Step 4: Updating local kubeconfig..."
aws eks --region "${REGION}" update-kubeconfig --name "${CLUSTER_NAME}"

# 6. Apply Kubernetes Manifests
echo "[*] Step 5: Deploying platform resources to Amazon EKS..."
kubectl apply -k k8s/

echo "============================================================"
echo " AWS Deployment Completed Successfully!"
echo " Monitor rollout with: kubectl get pods -n incident-platform"
echo "============================================================"
