"""
Automated Validation Tests for Phase 8: Kubernetes Manifests & CI/CD Pipelines.
"""

import os
import glob
import yaml
import pytest


K8S_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "k8s")
WORKFLOWS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".github", "workflows")


class TestKubernetesManifests:
    def test_all_manifest_files_exist(self):
        expected_files = [
            "00-namespace.yaml",
            "01-configmap.yaml",
            "02-secrets.yaml",
            "03-postgres.yaml",
            "04-migrations-job.yaml",
            "05-order-service.yaml",
            "06-payment-service.yaml",
            "07-api-gateway.yaml",
            "08-ingress.yaml",
            "09-hpa.yaml",
            "kustomization.yaml",
        ]
        for f in expected_files:
            file_path = os.path.join(K8S_DIR, f)
            assert os.path.exists(file_path), f"Missing manifest: {f}"

    def test_yaml_syntax_validity(self):
        yaml_files = glob.glob(os.path.join(K8S_DIR, "*.yaml"))
        assert len(yaml_files) >= 11
        for yf in yaml_files:
            with open(yf, "r", encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))
                assert len(docs) > 0, f"Empty YAML file: {yf}"

    def test_deployment_manifest_specifications(self):
        deployment_files = [
            "05-order-service.yaml",
            "06-payment-service.yaml",
            "07-api-gateway.yaml",
        ]
        for df in deployment_files:
            path = os.path.join(K8S_DIR, df)
            with open(path, "r", encoding="utf-8") as f:
                docs = list(yaml.safe_load_all(f))
            
            # Find the Deployment doc
            deployments = [d for d in docs if d and d.get("kind") == "Deployment"]
            assert len(deployments) == 1, f"Deployment not found in {df}"
            dep = deployments[0]

            # Replicas & selectors
            assert dep["spec"]["replicas"] >= 2
            assert "matchLabels" in dep["spec"]["selector"]

            # Containers & Probes
            container = dep["spec"]["template"]["spec"]["containers"][0]
            assert "resources" in container
            assert "requests" in container["resources"]
            assert "limits" in container["resources"]
            assert "livenessProbe" in container
            assert container["livenessProbe"]["httpGet"]["path"] == "/health"
            assert "readinessProbe" in container
            assert container["readinessProbe"]["httpGet"]["path"] == "/ready"

    def test_ingress_rules(self):
        path = os.path.join(K8S_DIR, "08-ingress.yaml")
        with open(path, "r", encoding="utf-8") as f:
            ingress = yaml.safe_load(f)
        
        assert ingress["kind"] == "Ingress"
        rules = ingress["spec"]["rules"][0]["http"]["paths"]
        routed_paths = [r["path"] for r in rules]
        assert "/" in routed_paths
        assert "/orders" in routed_paths
        assert "/payments" in routed_paths

    def test_hpa_specifications(self):
        path = os.path.join(K8S_DIR, "09-hpa.yaml")
        with open(path, "r", encoding="utf-8") as f:
            hpas = list(yaml.safe_load_all(f))

        assert len(hpas) == 3
        for h in hpas:
            assert h["kind"] == "HorizontalPodAutoscaler"
            assert h["spec"]["minReplicas"] == 2
            assert h["spec"]["maxReplicas"] == 5


class TestCicdWorkflows:
    def test_github_action_workflows_exist_and_valid(self):
        expected_workflows = ["ci.yml", "docker-build.yml", "k8s-validate.yml"]
        for wf in expected_workflows:
            wf_path = os.path.join(WORKFLOWS_DIR, wf)
            assert os.path.exists(wf_path), f"Missing workflow: {wf}"
            with open(wf_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                assert "name" in data
                assert "on" in data or True in data
                assert "jobs" in data
