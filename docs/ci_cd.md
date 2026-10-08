# Continuous Integration & Deployment (CI/CD)

## Overview

The platform uses GitHub Actions to automate code validation, container builds, and deployment verification on every push and pull request.

```
       [Developer Push / PR to master]
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   [ci.yml]    [docker-build]   [k8s-validate]
  - Multi-Py     - Multi-image    - Dry-run validation
    test suite     Docker build     of K8s manifests
  - Microservice - Container      - Kustomize build
    unit tests     integrity check  verification
```

---

## 1. Automated Workflows

Workflows are maintained under [`.github/workflows/`](file:///c:/Users/adity/Desktop/ai-incident-response-platform/.github/workflows/):

### A. Test Suite (`ci.yml`)
- **Triggers**: Push and pull request on `master` branch.
- **Matrix**: Runs against Python `3.12` and `3.13`.
- **Steps**:
  1. Installs project dependencies via `pip install -e ".[dev]"`.
  2. Executes complete platform test suite (`pytest tests/ -v`).
  3. Executes microservices unit tests with isolated package paths:
     - API Gateway tests (`services/api-gateway/tests/`)
     - Order Service tests (`services/order-service/tests/`)
     - Payment Service tests (`services/payment-service/tests/`)

### B. Container Image Build Check (`docker-build.yml`)
- **Triggers**: Push and pull request on `master` branch.
- **Steps**:
  1. Sets up Docker Buildx with layer caching.
  2. Verifies Dockerfile builds for:
     - `api-gateway`
     - `order-service`
     - `payment-service`
     - `database` (migrations)

### C. Kubernetes Manifest Validation (`k8s-validate.yml`)
- **Triggers**: Push and pull request on `master` branch.
- **Steps**:
  1. Installs `kubeconform` to perform strict offline OpenAPI schema validation on all resource manifests in `k8s/`.
  2. Compiles the resource graph via `kubectl kustomize k8s/` and pipes the output into `kubeconform` to ensure end-to-end bundle integrity.

---

## 2. Local CI Emulation

To run CI checks locally prior to pushing:

```bash
# 1. Run all tests
pytest tests/ -v
export PYTHONPATH="services/api-gateway"; pytest services/api-gateway/tests/ -v
export PYTHONPATH="services/order-service"; pytest services/order-service/tests/ -v
export PYTHONPATH="services/payment-service"; pytest services/payment-service/tests/ -v

# 2. Test Docker builds
docker compose build

# 3. Test Kubernetes validation
kubectl kustomize k8s/
```
