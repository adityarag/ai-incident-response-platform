# Kubernetes Deployment Guide

## Overview

The platform supports cloud-native deployment to Kubernetes clusters (Minikube, Kind, K3s, Amazon EKS, GKE, or self-hosted).

The architecture isolates all resources inside the `incident-platform` namespace, decoupling stateful databases, asynchronous migrations, and stateless microservices while establishing auto-scaling and ingress routing.

```
                         [Client / Ingress Controller]
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
           Path: /              Path: /orders           Path: /payments
      ┌───────────────┐       ┌───────────────┐       ┌───────────────┐
      │  api-gateway  │       │ order-service │       │payment-service│
      │  (ClusterIP)  │       │  (ClusterIP)  │       │  (ClusterIP)  │
      └───────┬───────┘       └───────┬───────┘       └───────┬───────┘
              │                       │                       │
              └───────────────────────┼───────────────────────┘
                                      ▼
                             ┌─────────────────┐
                             │    postgres     │
                             │  (StatefulSet)  │
                             └─────────────────┘
```

---

## 1. Resource Manifests

All manifests reside in the [`k8s/`](file:///c:/Users/adity/Desktop/ai-incident-response-platform/k8s/) directory:

| Manifest | Kind | Purpose |
|---|---|---|
| `00-namespace.yaml` | `Namespace` | Defines isolated `incident-platform` boundary |
| `01-configmap.yaml` | `ConfigMap` | Non-sensitive connection URLs and service configurations |
| `02-secrets.yaml` | `Secret` | Base64/Opaque database passwords and credentials |
| `03-postgres.yaml` | `StatefulSet` + `Service` | PostgreSQL 16 datastore with 2Gi PersistentVolumeClaim |
| `04-migrations-job.yaml` | `Job` | One-off Alembic database migration runner |
| `05-order-service.yaml` | `Deployment` + `Service` | Order lifecycle microservice (2 replicas, CPU/Memory limits, probes) |
| `06-payment-service.yaml`| `Deployment` + `Service` | Payment microservice (2 replicas, CPU/Memory limits, probes) |
| `07-api-gateway.yaml` | `Deployment` + `Service` | Reverse proxy and API Gateway (2 replicas) |
| `08-ingress.yaml` | `Ingress` | NGINX path-based routing (`/`, `/orders`, `/payments`) |
| `09-hpa.yaml` | `HorizontalPodAutoscaler` | Auto-scales deployments between 2 to 5 replicas at 75% CPU |
| `kustomization.yaml` | `Kustomization` | Bundles and manages the complete resource graph |

---

## 2. Health & Readiness Probes

Every stateless microservice specifies robust probes for container lifecycle management:

- **Liveness Probe** (`/health`):
  - Initial delay: 10 seconds
  - Period: 10 seconds
  - Timeout: 3 seconds
  - Ensures Kubernetes automatically restarts crashed or locked-up application containers.

- **Readiness Probe** (`/ready`):
  - Initial delay: 5 seconds
  - Period: 5 seconds
  - Timeout: 3 seconds
  - Ensures traffic is only routed once the service is initialized and dependencies are connected.

---

## 3. Local Cluster Deployment

### Prerequisites
- `kubectl` installed
- `minikube` or `kind` installed
- Docker running

### Using Minikube
```bash
# 1. Start Minikube cluster
minikube start --cpus=4 --memory=8192

# 2. Enable Ingress addon
minikube addons enable ingress
minikube addons enable metrics-server

# 3. Build local Docker images inside Minikube
eval $(minikube docker-env)
docker build -t platform-api-gateway:latest -f services/api-gateway/Dockerfile .
docker build -t platform-order-service:latest -f services/order-service/Dockerfile .
docker build -t platform-payment-service:latest -f services/payment-service/Dockerfile .
docker build -t platform-migrations:latest -f database/Dockerfile .

# 4. Deploy using Kustomize
kubectl apply -k k8s/

# 5. Verify Rollout Status
kubectl rollout status statefulset/postgres -n incident-platform
kubectl wait --for=condition=complete job/platform-migrations -n incident-platform --timeout=60s
kubectl rollout status deployment/order-service -n incident-platform
kubectl rollout status deployment/payment-service -n incident-platform
kubectl rollout status deployment/api-gateway -n incident-platform
```

### Accessing the Cluster
```bash
# Forward API Gateway locally
kubectl port-forward svc/api-gateway -n incident-platform 8000:8000

# Access Swagger UI
curl http://localhost:8000/docs
```
