# AI-Powered Incident Response and Self-Healing Platform

> An AI-assisted operational platform that observes cloud-native applications, investigates incidents using real system evidence, proposes safe actions, executes policy-approved remediation, verifies recovery, maintains an audit trail, and creates reviewable code changes when APIs evolve.

## Architecture

```
Client → API Gateway → [Order Service] → [Payment Service] → PostgreSQL
              ↓
     Observability Layer (Metrics, Logs, Traces)
              ↓
       Incident Engine → AI Investigation Agent
              ↓
       Policy / Risk Engine → Remediation Engine
              ↓
       Post-Action Verification → Audit Log
```

## Current Status: Phase 3 — Observability ✅

| Component | Status | Port |
|---|---|---|
| API Gateway | ✅ Running | :8000 |
| Order Service | ✅ Running | :8001 |
| Payment Service | ✅ Running | :8002 |
| PostgreSQL | ✅ Running | :5432 |
| Prometheus | ✅ Metric Scraping | :9090 |
| Loki | ✅ Log Aggregation | :3100 |
| Grafana | ✅ Provisioned Dashboards | :3000 |
| OpenTelemetry | ✅ Traces & Correlation | - |
| Database Migrations | ✅ Applied (001, 002) | - |
| Health & Metrics Probes | ✅ All Services (`/metrics`) | - |

## Prerequisites

- Python 3.12+
- Docker & Docker Compose
- Git

## Quick Start

### 1. Clone and configure

```bash
git clone <repository-url>
cd ai-incident-response-platform
cp .env.example .env
```

### 2. Start with Docker Compose

```bash
docker compose up --build
```

This starts:
- **PostgreSQL 16** on port 5432
- **Alembic migrations** (runs once, applies schema)
- **API Gateway** on port 8000

### 3. Verify

```bash
# Health check
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "api-gateway",
#   "version": "0.1.0",
#   "timestamp": "...",
#   "checks": { "database": { "status": "connected" } }
# }

# API docs
open http://localhost:8000/docs
```

### 4. Stop

```bash
docker compose down       # Keep data
docker compose down -v    # Remove data volumes
```

## Local Development (without Docker)

### Setup Python environment

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

pip install -e ".[dev]"
```

### Run tests

```bash
# Model tests (no database required)
pytest tests/ -v

# API Gateway tests (no database required)
cd services/api-gateway
pip install -r requirements.txt
pytest tests/ -v
```

### Run API Gateway locally

```bash
# Requires PostgreSQL running on localhost:5432
cd services/api-gateway
uvicorn app.main:app --reload --port 8000
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | PostgreSQL hostname |
| `POSTGRES_PORT` | `5432` | PostgreSQL port |
| `POSTGRES_DB` | `incident_platform` | Database name |
| `POSTGRES_USER` | `platform` | Database user |
| `POSTGRES_PASSWORD` | `changeme_in_production` | Database password |
| `API_GATEWAY_PORT` | `8000` | API Gateway exposed port |

## Project Structure

```
ai-incident-response-platform/
├── services/
│   └── api-gateway/           # API Gateway microservice
│       ├── app/
│       │   ├── main.py        # FastAPI application
│       │   └── config.py      # Pydantic settings
│       ├── tests/
│       │   ├── conftest.py    # Test fixtures
│       │   └── test_health.py # Endpoint tests
│       ├── Dockerfile
│       └── requirements.txt
├── database/
│   ├── models.py              # SQLAlchemy models
│   ├── session.py             # DB session management
│   ├── migrations/            # Alembic migrations
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── alembic.ini
│   ├── init.sql
│   └── Dockerfile             # Migration runner
├── tests/
│   └── test_models.py         # Model unit tests
├── docs/
├── .env.example
├── .gitignore
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | API information |
| GET | `/health` | Liveness probe with DB check |
| GET | `/ready` | Readiness probe |
| GET | `/docs` | Swagger UI |

## Roadmap

- [x] **Phase 1** — Foundation (API Gateway, PostgreSQL, Docker)
- [x] **Phase 2** — Microservices (Order Service, Payment Service)
- [x] **Phase 3** — Observability (OpenTelemetry, Prometheus, Grafana, Loki)
- [ ] **Phase 4** — Fault Injection
- [ ] **Phase 5** — AI Investigation Agent
- [ ] **Phase 6** — Self-Healing (Policy, Remediation, Verification)
- [ ] **Phase 7** — Self-Maintaining API
- [ ] **Phase 8** — Kubernetes + CI/CD
- [ ] **Phase 9** — AWS Deployment
- [ ] **Phase 10** — Evaluation & Demo

## Team

| Member | Role |
|--------|------|
| Aditya Rag | Technical Lead — Architecture, Backend, AI, DevOps |
| Vaibhav | Frontend/Dashboard, UI, API Integration |
| Ravi | Observability, Prometheus, Grafana, Logging |
| Ankit | Testing, Evaluation, Documentation |

## Supervisor

Dr. Nishi Kant Kumar — Assistant Professor, CSE, BIT Mesra

## License

Academic project — BIT Mesra, Semester VII Minor Project.
