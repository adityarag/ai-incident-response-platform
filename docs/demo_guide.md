# Final Academic Project Demonstration Guide

## Academic Presentation Overview

- **Project**: AI-Powered Incident Response and Self-Healing Platform for Cloud-Native Applications
- **Department**: Department of Computer Science & Engineering, BIT Mesra (Off-Campus Deoghar)
- **Course**: Final-Year Minor Project / Semester VII
- **Supervisor**: Dr. Nishi Kant Kumar, Assistant Professor, CSE
- **Presenters**: Aditya Rag, Vaibhav, Ravi, Ankit

---

## 1. Demonstration Flow & Live Walkthrough

The live demonstration takes approximately 10–12 minutes and covers the complete lifecycle of both platform capabilities (**Capability A: Incident Response + Self-Healing** and **Capability B: Self-Maintaining API**).

```
  [Architecture & Telemetry]
              │
              ▼
  [Live Fault Injection] ── (Simulate Outage)
              │
              ▼
  [AI Investigation & RCA] ── (Sandboxed Telemetry & Confidence Score)
              │
              ▼
  [Policy-Controlled Healing] ── (Autonomous vs Operator Approval)
              │
              ▼
  [Self-Maintaining API] ── (Schema Diff & Automated GitHub PR)
              │
              ▼
  [Quantitative Benchmarks] ── (MTTD, MTTI, MTTR Metrics Presentation)
```

---

## 2. Step-by-Step Live Commands

### Step 1: Microservices Architecture & Health Verification
Show the running microservices and the reverse proxy gateway:
```bash
# Verify health of all services
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health

# Show OpenAPI Swagger docs
# Open browser at: http://localhost:8000/docs
```
*Key Discussion Point*: Highlight distributed microservice architecture (API Gateway, Order Service, Payment Service, PostgreSQL) with OpenTelemetry correlation ID propagation.

---

### Step 2: Live Controlled Fault Injection
Deliberately introduce a realistic latency spike into `payment-service` without data loss:
```bash
# Inject 3.0s latency into payment-service for 60 seconds
python -m fault_injection.cli latency --service payment-service --seconds 3.0 --duration 60

# Inspect active fault status
python -m fault_injection.cli list
```
*Key Discussion Point*: Emphasize safety guardrails: zero destructive operations, automatic TTL expiry, and isolated memory manager.

---

### Step 3: Autonomous Incident Detection & AI Investigation
Trigger the AI Investigation Agent to detect the anomaly and conduct Root Cause Analysis:
```bash
# Scan cluster and automatically produce RCA report
python -m ai_agent.cli scan-and-diagnose

# Or run targeted investigation with formatted output
python -m ai_agent.cli investigate --service payment-service --reason "Payment latency SLA breach"
```
*Key Discussion Point*: Explain that the AI Agent does NOT run unbounded shell commands; it operates via sandboxed tools (`HealthTool`, `MetricsTool`, `LogsTool`, `GitTool`) and computes probabilistic confidence scores.

---

### Step 4: Policy-Controlled Self-Healing & Verification
Execute the self-healing pipeline governed by the Policy Engine:
```bash
# Display policy whitelist and risk classification tiers
python -m remediation.cli policies

# Trigger self-healing
python -m remediation.cli auto-heal --service payment-service --reason "High latency observed"
```
*Key Discussion Point*: Explain how LOW-risk actions (`clear_fault`, `reconnect_db`) are executed autonomously, while flapping limits prevent retry storms.

---

### Step 5: Human-in-the-Loop Operator Review for High-Risk Actions
Demonstrate the governance workflow for high-risk operations (e.g. container restart or process crash):
```bash
# View actions queued for operator approval
python -m remediation.cli list-pending

# Operator reviews and approves action
python -m remediation.cli approve --action-id <ACTION_ID> --operator "aditya_sre"
```
*Key Discussion Point*: Show how the system keeps humans in the loop for high-impact decisions, ensuring enterprise safety.

---

### Step 6: Capability B — Self-Maintaining API Demonstration
Demonstrate automatic schema change detection and pull request generation:
```bash
# Run schema diff against new version
python -m self_maintaining_api.cli diff --old docs/schemas/v1.json --new docs/schemas/v2.json --service payment-service

# Generate reviewable GitHub Pull Request draft with unified diffs
python -m self_maintaining_api.cli generate-pr --old docs/schemas/v1.json --new docs/schemas/v2.json --service payment-service
```
*Key Discussion Point*: Show how downstream client code is statically analyzed and candidate code patches are synthesized with tested unified diffs.

---

### Step 7: Empirical Benchmarking & Quantitative Metrics
Run the automated evaluation benchmark suite:
```bash
python -m evaluation.cli run-benchmarks
```
*Key Discussion Point*: Present the results table:
- **MTTD**: `< 0.1s`
- **MTTI**: `< 1.0s`
- **MTTR**: `< 0.2s`
- **Total Recovery**: `~1.0s` compared to the industry average of `40–90 minutes` manual downtime.

---

## 3. Team Member Contributions

| Member | Primary Modules & Presentation Topics |
|---|---|
| **Aditya Rag** | System Architecture, AI Investigation Engine, Policy Engine, Kubernetes & Terraform |
| **Vaibhav** | API Gateway Routing, Service Integration, Swagger UI & Dashboard |
| **Ravi** | Observability Stack, Prometheus Metrics, Grafana Dashboards, Loki Logs |
| **Ankit** | Controlled Fault Injection Framework, Benchmarking Suite, Academic Documentation |
