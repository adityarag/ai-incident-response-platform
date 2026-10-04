# Policy-Controlled Remediation & Self-Healing Engine

## Overview

The **Self-Healing and Remediation Engine** (Phase 6) translates diagnostic findings from the AI Investigation Agent (Phase 5) into safe, policy-governed corrective actions.

To protect system integrity in cloud-native environments, the platform strictly rejects unconstrained AI autonomy. Instead, it enforces a deterministic **Policy Engine**, a **Whitelisted Action Matrix**, **Rate-Limiting / Flapping Safeguards**, **Mandatory Human-in-the-Loop Approvals** for high-impact actions, and **Post-Action Verification** with audit logging.

```
                     [RCAReport from Phase 5]
                                │
                                ▼
                     ┌──────────────────────┐
                     │    Policy Engine     │
                     │  - Action Whitelist  │
                     │  - Risk Tier Matrix  │
                     │  - Flapping Cooldown │
                     └──────────┬───────────┘
                                │
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
          [LOW RISK ACTION]           [HIGH / CRITICAL RISK]
        (Autonomous Execution)        (Mandatory Human Review)
                  │                           │
                  │                   ┌───────▼───────┐
                  │                   │ Operator CLI  │ ── Reject ──► [Escalated]
                  │                   │  or Dashboard │
                  │                   └───────┬───────┘
                  │                           │ Approved
                  └─────────────┬─────────────┘
                                ▼
                     ┌──────────────────────┐
                     │ Remediation Executor │
                     │  - clear_fault       │
                     │  - reconnect_db      │
                     │  - restart_service   │
                     │  - scale_service     │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │ Post-Action Verifier │
                     │  - Health Probes     │
                     │  - SLA / Metrics     │
                     └──────────┬───────────┘
                                │
                  ┌─────────────┴─────────────┐
                  ▼                           ▼
            [RECOVERED]                 [UNRESOLVED]
         Incident Closed             Escalate to On-Call
                  │                           │
                  └─────────────┬─────────────┘
                                ▼
                     ┌──────────────────────┐
                     │ Tamper-Evident Audit │
                     │ (PostgreSQL AuditLog)│
                     └──────────────────────┘
```

---

## 1. Risk Tier Taxonomy & Whitelisted Actions

All candidate remediations are evaluated against the following classification:

| Action | Risk Tier | Approval Required | Execution Mode | Description |
|---|---|---|---|---|
| `clear_fault` | `LOW` | No | **Autonomous** | Clears synthetic fault injections (latency, error spikes, timeouts) |
| `flush_cache` | `LOW` | No | **Autonomous** | Clears cache stores or in-memory caches |
| `reconnect_db` | `LOW` | No | **Autonomous** | Resets connection pool or clears DB failure simulation |
| `scale_service` | `MEDIUM` | Yes | **Human Approval** | Adjusts service replica count |
| `restart_service` | `HIGH` | Yes | **Human Approval** | Restarts container or worker process |
| `rollback_deployment` | `CRITICAL` | Yes | **Human Approval** | Reverts deployment to prior stable Git commit |

> [!IMPORTANT]
> Any action not present in the approved whitelist is **strictly rejected** by the Policy Engine with `CRITICAL` risk and logged as a security alert.

---

## 2. Guardrails & Safety Controls

1. **Flapping / Rate Limiting**:
   - The Policy Engine tracks remediation frequency per microservice.
   - If a service exceeds `max_actions_per_window` (default: 3 actions) within `cooldown_window_seconds` (default: 300s), further automatic actions are blocked with status `COOLDOWN_BLOCKED`.
2. **Deterministic Bounded Tools**:
   - Remediation execution does not execute arbitrary shell commands.
   - Actions are dispatched to dedicated adapters (`fault_manager`, Docker control plane, or service APIs).
3. **Non-Destructive Guarantee**:
   - Remediation operations cannot drop tables, delete databases, or destroy persistent volumes.

---

## 3. Human-in-the-Loop Review

For `HIGH` and `CRITICAL` risk recommendations:
1. The orchestrator creates an `ActionRequest` in `PENDING_APPROVAL` status.
2. The action is held in queue until an operator reviews the RCA findings.
3. Operators can approve or reject the request via CLI or API.
4. If approved, the orchestrator dispatches execution and verifies recovery.
5. If rejected, the incident is flagged for manual triage.

---

## 4. Post-Remediation Verification

Following action execution:
1. Probes `/health` and `/ready` endpoints of the target service.
2. Evaluates error rate metrics in Prometheus to ensure drop to 0.
3. Assesses P95 latency against SLA thresholds.
4. If healthy: updates status to `VERIFIED` and closes incident.
5. If unhealthy: alerts on-call team for immediate escalation.

---

## 5. CLI Commands

### View Policies & Risk Tiers
```bash
python -m remediation.cli policies
```

### Run Self-Healing Loop on Service
```bash
python -m remediation.cli auto-heal --service payment-service --reason "High latency observed"
```

### Review Pending Actions Requiring Approval
```bash
python -m remediation.cli list-pending
```

### Approve Action
```bash
python -m remediation.cli approve --action-id ACT-123456 --operator "alice_sre"
```

### Reject Action
```bash
python -m remediation.cli reject --action-id ACT-123456 --operator "alice_sre" --reason "Scheduled maintenance"
```

---

## 6. Testing

Run the automated test suite for Phase 6:
```bash
pytest tests/test_remediation.py -v
```
