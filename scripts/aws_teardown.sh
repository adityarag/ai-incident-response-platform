#!/usr/bin/env bash
# ==============================================================================
# AWS Cloud Teardown Automation Script
# Cleanly destroys cloud resources to prevent unintended billing
# ==============================================================================
set -euo pipefail

echo "============================================================"
echo " Starting AWS Cloud Teardown & Resource Cleanup"
echo "============================================================"

# 1. Remove Kubernetes workloads
echo "[*] Step 1: Deleting Kubernetes resources from EKS..."
if kubectl get namespace incident-platform > /dev/null 2>&1; then
  kubectl delete -k k8s/ --ignore-not-found=true
fi

# 2. Destroy AWS Infrastructure via Terraform
echo "[*] Step 2: Destroying Terraform-managed infrastructure..."
cd terraform
terraform destroy -auto-approve

echo "============================================================"
echo " AWS Cloud Teardown Completed Successfully."
echo " All billable resources destroyed."
echo "============================================================"
