# Architecture

## Overview

The AI Incident Response Platform is a multi-layered system designed to monitor, investigate, and remediate incidents in cloud-native applications.

## System Layers

### 1. Application Layer (Monitored Services)

The target application consists of microservices:

```
Client
  ↓
API Gateway (:8000)
  ↓
Order Service (:8001)      [Phase 2]
  ↓
Payment Service (:8002)    [Phase 2]
  ↓
PostgreSQL (:5432)
```

Each service provides:
- Health endpoint (`GET /health`)
- Readiness endpoint (`GET /ready`)
- Structured JSON logging
- Metrics exposition (Phase 3)
- Trace context propagation (Phase 3)

### 2. Observability Layer [Phase 3]

```
Services → OpenTelemetry → Prometheus (metrics)
                         → Loki (logs)
                         → Grafana (dashboards)
```

### 3. Incident Detection Engine [Phase 5]

Deterministic rules-based detection:
- HTTP 5xx rate threshold
- Latency threshold
- Health endpoint failures
- Pod crash loops
- Database connection exhaustion
- API schema changes

### 4. AI Investigation Agent [Phase 5]

Tool-calling agent with bounded capabilities:
- Telemetry queries
- Kubernetes inspection
- Deployment history
- Git history
- Database health

### 5. Policy / Risk Engine [Phase 6]

Risk classification for all remediation actions:
- **LOW**: Auto-execute (restart, scale within bounds)
- **MEDIUM**: Requires confirmation (rollback, config change)
- **HIGH**: Requires human approval (DB changes, production merges)

### 6. Remediation Engine [Phase 6]

Deterministic playbooks:
1. Service Restart
2. Scaling
3. Deployment Rollback

### 7. Verification Engine [Phase 6]

Post-remediation verification with configurable success conditions.

## Data Model

```
services          — Registered microservices
incidents         — Detected incidents (state machine)
incident_events   — Timeline events        [future]
investigations    — AI investigation results [future]
evidence          — Collected evidence       [future]
remediation_actions — Executed actions       [future]
approvals         — Human approval records   [future]
verification_results — Recovery checks       [future]
audit_logs        — Immutable audit trail
```

## Incident State Machine

```
DETECTED → INVESTIGATING → ROOT_CAUSE_IDENTIFIED → REMEDIATION_PROPOSED
    → AWAITING_APPROVAL → REMEDIATING → VERIFYING → RESOLVED
                                                  → FAILED → ESCALATED
```

## Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Runtime | Python 3.12+ | Language |
| Framework | FastAPI | Web framework |
| ORM | SQLAlchemy 2.0 | Database access |
| Migrations | Alembic | Schema management |
| Database | PostgreSQL 16 | Persistent storage |
| Containers | Docker, Compose | Local orchestration |
| Observability | OpenTelemetry, Prometheus, Grafana, Loki | Monitoring |
| AI | LLM API + LangGraph | Investigation agent |
| Orchestration | Kubernetes | Production deployment |
| CI/CD | GitHub Actions | Automation |
| IaC | Terraform | AWS infrastructure |
