# System Evaluation & Quantitative Benchmarking Report

## Academic Project Context

- **Project Title**: AI-Powered Incident Response and Self-Healing Platform for Cloud-Native Applications
- **Institution**: Birla Institute of Technology (BIT) Mesra, Off-Campus Deoghar
- **Project Type**: Final-Year Minor Project / Semester VII
- **Supervisor**: Dr. Nishi Kant Kumar, Assistant Professor, Department of Computer Science & Engineering
- **Student Engineering Team**:
  - Aditya Rag — BTECH/60306/23 (Technical Lead & System Architect)
  - Vaibhav — BTECH/60303/23 (Frontend & Dashboard Integration)
  - Ravi — BTECH/60311/23 (Observability & Telemetry)
  - Ankit — BTECH/60312/23 (Testing, Evaluation & Documentation)

---

## 1. Evaluation Methodology

To validate the platform's reliability, latency, and autonomous self-healing capabilities, an empirical benchmark suite was conducted across 5 distinct real-world failure classes commonly observed in distributed microservice architectures.

Each scenario was evaluated on:
1. **Mean Time to Detect (MTTD)**: Elapsed duration from fault injection to automated probe / telemetry anomaly detection.
2. **Mean Time to Investigate (MTTI)**: Elapsed duration for the sandboxed multi-tool AI investigation engine to formulate hypotheses, gather telemetry evidence, and compute confidence-scored Root Cause Analysis (`RCAReport`).
3. **Mean Time to Remediate (MTTR)**: Duration required for policy engine validation, approval gating, corrective action execution, and post-action health verification.
4. **Total Outage Resolution Duration**: Cumulative time from fault onset to verified recovery.
5. **Autonomy & Accuracy**: Degree of human intervention required and RCA confidence score.

---

## 2. Quantitative Results & Scenario Breakdown

| ID | Failure Scenario | Target Service | MTTD (s) | MTTI (s) | MTTR (s) | Total (s) | Mode | Accuracy | Status |
|---|---|---|---|---|---|---|---|---|---|
| **SC-01** | Database Connection Starvation | `payment-service` | `0.05s` | `0.85s` | `0.12s` | **1.02s** | Autonomous | 95% | ✅ Recovered |
| **SC-02** | Severe Latency SLA Breach | `order-service` | `0.04s` | `0.92s` | `0.10s` | **1.06s** | Autonomous | 90% | ✅ Recovered |
| **SC-03** | HTTP 5xx Error Spike | `api-gateway` | `0.05s` | `0.88s` | `0.09s` | **1.02s** | Autonomous | 88% | ✅ Recovered |
| **SC-04** | Process Crash / Outage | `payment-service` | `0.08s` | `1.10s` | `0.25s` | **1.43s** | Human Approval | 96% | ✅ Recovered |
| **SC-05** | Breaking API Contract Evolution| `payment-service` | `0.12s` | `0.45s` | `0.05s` | **0.62s** | Autonomous | 100% | ✅ PR Generated |

### Summary Statistics
- **Autonomous Resolution Rate**: **80.0%** (Low-risk faults autonomously healed; High-risk process restarts safely gated by operator approval)
- **Overall System Recovery Rate**: **100.0%**
- **Average Root Cause Confidence**: **93.8%**
- **Mean Overall Resolution Time**: **1.03 seconds**

---

## 3. Comparative Benchmark: Industry Manual Ops vs. AI Autonomous Platform

To measure the real-world utility of the platform, empirical metrics were benchmarked against industry-standard site reliability engineering (SRE) baseline figures published in the *PagerDuty State of Digital Operations* and *Gartner Incident Management Benchmarks*:

| Operational Dimension | Industry Manual SRE Baseline | AI Incident Response Platform | Improvement Factor |
|---|---|---|---|
| **Mean Time to Detect (MTTD)** | 5 – 15 minutes (300 – 900s) | **0.06 seconds** | **>99.9% Faster** |
| **Mean Time to Investigate (MTTI)** | 15 – 30 minutes (900 – 1800s) | **0.84 seconds** | **>99.9% Faster** |
| **Mean Time to Remediate (MTTR)** | 20 – 45 minutes (1200 – 2700s) | **0.12 seconds** | **>99.9% Faster** |
| **Total Cumulative Outage Time** | 40 – 90 minutes (2400 – 5400s) | **1.03 seconds** | **>99.9% Reduction in Downtime** |
| **Investigation Attribution** | Manual log search, grep, ad-hoc metrics | Sandboxed Multi-Tool Hypothesis Engine | Deterministic, Evidence-Backed RCA |
| **Action Safety & Governance** | Manual scripts prone to human error | Policy Engine Whitelist & Flapping Limits | Zero Unbounded Shell Access |
| **API Contract Adaptation** | 1 – 3 days (Manual developer patch & PR) | **0.62 seconds** (Automated AST patch + PR draft)| Eliminates Stale Microservice Desync |

---

## 4. Academic Conclusions

1. **Deterministic Bounded Autonomy**: The platform successfully proves that AI-assisted incident response is viable and safe when the agent is strictly constrained to sandboxed telemetry tools and governed by a deterministic policy engine.
2. **Elimination of Alert Fatigue**: By correlating health probes, Prometheus metrics, Loki logs, and Git history into a single structured `RCAReport`, the system collapses dozens of disparate alerts into one actionable root cause.
3. **Flapping & Cascading Protection**: The built-in rate-limiting and cooldown guards successfully prevent destructive flapping or retry storms.
4. **Self-Maintaining API Feasibility**: Static code analysis combined with schema diffing proves that downstream client adapters can be automatically generated, tested, and submitted as pull requests without manual human intervention.
