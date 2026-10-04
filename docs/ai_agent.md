# AI Incident Investigation & Root Cause Analysis (RCA) Agent

## Overview

The **AI Incident Investigation Agent** (Phase 5) is an evidence-driven, tool-augmented system designed to autonomously investigate production-like anomalies in microservice environments. 

Rather than granting an LLM unrestricted execution privileges or shell access, the agent operates through **strictly bounded telemetry inspection tools**. It evaluates hypotheses against collected observability data, computes probabilistic confidence scores, and outputs a structured Root Cause Analysis (`RCAReport`) complete with policy-compliant remediation recommendations.

```
       [Incident Alert / Anomaly Detection]
                       │
                       ▼
            ┌─────────────────────┐
            │  AI Investigator    │
            └──────────┬──────────┘
                       │ 
        ┌──────────────┼──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
   [HealthTool]  [MetricsTool]   [LogsTool]     [GitTool]
   (/health,     (Prometheus     (Grafana Loki  (Recent Git
    /ready)       PromQL)         LogQL)         Commits)
        │              │              │              │
        └──────────────┼──────────────┴──────────────┘
                       │  Evidence Aggregation
                       ▼
            ┌─────────────────────┐
            │ Hypothesis Evaluator│
            └──────────┬──────────┘
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
 [Confidence Scoring]         [Remediation Plan]
 (0.0 to 1.0)                 (LOW: Auto-heal / HIGH: Approval)
       │                               │
       └───────────────┬───────────────┘
                       │
                       ▼
             [Structured RCA Report]
```

---

## 1. Safety Guardrails & Principles

1. **No Arbitrary Shell Execution**: The agent does not execute unbounded bash or terminal commands. Every telemetry probe runs through validated, read-only Python tool adapters.
2. **Deterministic Hypothesis Evaluation**: Candidate failure causes are evaluated against telemetry thresholds (e.g., HTTP 5xx ratios, P95 latency quantiles, database ping status).
3. **Evidence-Backed Attribution**: Every conclusion in an `RCAReport` references specific telemetry evidence (promql queries, loki log snippets, health check payloads).
4. **Graded Risk Recommendations**: Remediation actions are classified into `LOW` risk (safe for autonomous self-healing in Phase 6) and `HIGH` risk (mandates human operator approval).

---

## 2. Telemetry Tools Architecture

The agent interfaces with the environment via modular tools in `ai_agent/tools/`:

| Tool | Source | Purpose | Example Query |
|---|---|---|---|
| `HealthTool` | Microservices `/health`, `/ready` | Probes service availability, database connectivity, and readiness state | `GET http://localhost:8002/health` |
| `MetricsTool` | Prometheus (`:9090`) | Evaluates 5xx request error rates, request throughput, and P95 latency quantiles | `histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket[1m])))` |
| `LogsTool` | Grafana Loki (`:3100`) | Searches for stack traces, exception logs, and error occurrences | `{service="payment-service"} \|= "ERROR"` |
| `GitTool` | Local Git Repository | Detects recent code merges, releases, and deployment revisions | `git log -n 5 --oneline` |

All tools include resilient network exception handlers and offline fallbacks to ensure testability without active daemons.

---

## 3. Evaluated Hypotheses

The agent methodically tests for key failure classes:

1. **Database Failure / Connection Pool Starvation**:
   - *Evidence*: Health probe reports `checks.database.status: disconnected` or Loki logs indicate connection timeouts.
   - *Confidence*: `0.95`
   - *Suggested Action*: Clear database fault (`LOW` risk, autonomous safe).

2. **Severe Latency SLA Breach**:
   - *Evidence*: P95 latency > 2.0s or trigger type `latency_spike`.
   - *Confidence*: `0.90`
   - *Suggested Action*: Clear artificial latency or scale service replicas (`LOW`/`MEDIUM` risk).

3. **HTTP 5xx Error Spike**:
   - *Evidence*: Prometheus error rate > 5.0 req/s or Loki reports high error frequency.
   - *Confidence*: `0.88`
   - *Suggested Action*: Clear error injection, verify downstream dependencies.

4. **Service Outage / Process Crash**:
   - *Evidence*: Health probe connection refused / liveness check failure.
   - *Confidence*: `0.96`
   - *Suggested Action*: Restart container/service (`HIGH` risk, requires operator approval).

5. **Deployment Regression**:
   - *Evidence*: Recent git commit within incident timeframe correlating with sudden failure.
   - *Confidence*: Evaluated alongside runtime metrics.
   - *Suggested Action*: Rollback deployment (`HIGH` risk, requires operator approval).

---

## 4. Structured RCA Schema

Investigations yield a validated Pydantic model (`RCAReport`):

```json
{
  "incident_id": "INC-09C7261B",
  "timestamp": "2026-10-04T09:49:07.033768Z",
  "affected_service": "payment-service",
  "affected_endpoint": "/payments/process",
  "summary": "Service 'payment-service' is experiencing severe latency degradation (P95 > 2.0s).",
  "probable_root_cause": "Artificial latency injection or downstream bottleneck on /payments/process.",
  "confidence_score": 0.90,
  "evidence_gathered": [
    {
      "tool_name": "health_tool",
      "query_used": "http://localhost:8002/health",
      "raw_result": { "status": "ok" },
      "summary": "Service 'payment-service' is healthy (HTTP 200)."
    },
    {
      "tool_name": "metrics_tool",
      "query_used": "histogram_quantile(0.95, ...)",
      "raw_result": { "p95_latency": 3.42 },
      "summary": "P95 latency for 'payment-service' is 3.420s (SLA breach > 2.0s)."
    }
  ],
  "hypotheses_evaluated": [
    {
      "hypothesis": "Severe Endpoint Latency Degradation",
      "matched": true,
      "confidence": 0.90,
      "reason": "Observed P95 latency is 3.42s or incident flagged for high latency."
    }
  ],
  "remediation_recommendations": [
    {
      "action_type": "clear_fault",
      "target_service": "payment-service",
      "risk_level": "LOW",
      "description": "Clear active latency simulation fault.",
      "parameters": { "fault_type": "latency" },
      "requires_human_approval": false
    }
  ],
  "investigation_duration_seconds": 0.84
}
```

---

## 5. CLI Usage

### A. Detect Active Incidents
Continuously or manually probe all services for anomalies:
```bash
python -m ai_agent.cli detect
```

### B. Execute Targeted Investigation
Investigate a specific service or endpoint on demand:
```bash
python -m ai_agent.cli investigate --service payment-service --reason "Payment timeouts reported"
```

Output formatted JSON report:
```bash
python -m ai_agent.cli investigate --service payment-service --json
```

### C. Full Scan & Diagnose
Scan all microservices and trigger automated RCA for any detected incident:
```bash
python -m ai_agent.cli scan-and-diagnose
```

---

## 6. Testing

Run the automated test suite for the AI Agent:
```bash
pytest tests/test_ai_agent.py -v
```

The test suite covers:
- Isolated tool mocking (`HealthTool`, `MetricsTool`, `LogsTool`, `GitTool`)
- Hypothesis evaluation for Database Starvation, Latency Spikes, Error Spikes, and Crashes
- Detector polling and alert creation
- Edge cases including offline daemons and network refusals
