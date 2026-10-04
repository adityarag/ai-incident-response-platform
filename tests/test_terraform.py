"""
Automated Validation Tests for Phase 9: AWS Cloud Infrastructure & Terraform.
"""

import os
import re
import glob
import pytest


TF_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "terraform")
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "scripts")


class TestTerraformManifests:
    def test_all_terraform_files_exist(self):
        expected_files = [
            "main.tf",
            "variables.tf",
            "vpc.tf",
            "security_groups.tf",
            "ecr.tf",
            "eks.tf",
            "rds.tf",
            "outputs.tf",
            "terraform.tfvars.example",
        ]
        for f in expected_files:
            path = os.path.join(TF_DIR, f)
            assert os.path.exists(path), f"Missing Terraform file: {f}"

    def test_operational_scripts_exist(self):
        expected_scripts = [
            "aws_deploy.sh",
            "aws_teardown.sh",
        ]
        for s in expected_scripts:
            path = os.path.join(SCRIPTS_DIR, s)
            assert os.path.exists(path), f"Missing operational script: {s}"

    def test_vpc_and_subnet_configuration(self):
        vpc_file = os.path.join(TF_DIR, "vpc.tf")
        with open(vpc_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'resource "aws_vpc"' in content
        assert 'resource "aws_subnet" "public"' in content
        assert 'resource "aws_subnet" "private"' in content
        assert 'resource "aws_subnet" "database"' in content
        assert 'resource "aws_nat_gateway"' in content

    def test_eks_configuration(self):
        eks_file = os.path.join(TF_DIR, "eks.tf")
        with open(eks_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'resource "aws_eks_cluster"' in content
        assert 'resource "aws_eks_node_group"' in content
        assert 'version  = "1.30"' in content
        assert "AmazonEKSClusterPolicy" in content
        assert "AmazonEKSWorkerNodePolicy" in content

    def test_rds_configuration(self):
        rds_file = os.path.join(TF_DIR, "rds.tf")
        with open(rds_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert 'resource "aws_db_instance"' in content
        assert 'engine                 = "postgres"' in content
        assert 'engine_version         = "16.3"' in content
        assert "aws_db_subnet_group" in content
        assert "skip_final_snapshot = true" in content

    def test_ecr_security_and_pruning(self):
        ecr_file = os.path.join(TF_DIR, "ecr.tf")
        with open(ecr_file, "r", encoding="utf-8") as f:
            content = f.read()
        assert "scan_on_push = true" in content
        assert 'resource "aws_ecr_lifecycle_policy"' in content
        assert "expire" in content

    def test_security_group_isolation(self):
        sg_file = os.path.join(TF_DIR, "security_groups.tf")
        with open(sg_file, "r", encoding="utf-8") as f:
            content = f.read()
        # RDS must only accept ingress from EKS nodes
        assert "aws_security_group.eks_nodes.id" in content
        assert "from_port       = 5432" in content

    def test_no_hardcoded_aws_credentials(self):
        """Security guardrail: ensure no real AWS keys or tokens are in repo."""
        for root, _, files in os.walk(TF_DIR):
            for file in files:
                path = os.path.join(root, file)
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    # Check for AWS Access Key pattern AKIA[0-9A-Z]{16}
                    assert not re.search(r"\bAKIA[0-9A-Z]{16}\b", content), f"Hardcoded AWS key in {file}"
                    assert "aws_secret_access_key" not in content.lower()
