# Self-Maintaining API Engine

## Overview

The **Self-Maintaining API Engine** (Phase 7) realizes Capability B of the Master Project Specification. When microservice API contracts evolve or introduce breaking changes, modern microservice teams typically encounter client runtime failures and cumbersome manual patch cycles. 

The platform autonomously:
1. Detects schema discrepancies between OpenAPI 3.x contract revisions.
2. Identifies breaking changes (removed endpoints, altered field types, newly required fields).
3. Conducts repository-wide static analysis to discover affected consumer microservices.
4. Synthesizes candidate code transformations (patches) in downstream codebases.
5. Verifies compatibility by running automated test suites.
6. Generates complete, reviewable GitHub Pull Request drafts with formatted markdown change summaries and unified diffs.

```
       [OpenAPI Baseline] vs [OpenAPI Target]
                         │
                         ▼
             ┌────────────────────────┐
             │   SchemaDiffEngine     │
             │ - Identifies breaking  │
             │   vs non-breaking delta│
             └───────────┬────────────┘
                         │
                         ▼
             ┌────────────────────────┐
             │     ImpactAnalyzer     │
             │ - Scans consumer files │
             │ - Pinpoints code lines │
             └───────────┬────────────┘
                         │
                         ▼
             ┌────────────────────────┐
             │    PatchSynthesizer    │
             │ - Rewrites symbols     │
             │ - Formats unified diff │
             └───────────┬────────────┘
                         │
                         ▼
             ┌────────────────────────┐
             │   Automated Testing    │
             │ - Runs pytest suites   │
             │ - Validates regression │
             └───────────┬────────────┘
                         │
                         ▼
             ┌────────────────────────┐
             │  PullRequestGenerator  │
             │ - Branch, Title & Body │
             │ - Reviewable PR Draft  │
             └────────────────────────┘
```

---

## 1. Schema Change Classification

Changes between OpenAPI specifications are categorized into strict compatibility levels:

| Change Type | Compatibility | Example Scenario |
|---|---|---|
| `ENDPOINT_REMOVED` | **`BREAKING`** | `GET /payments/{id}` was deleted or moved |
| `FIELD_REMOVED` | **`BREAKING`** | Property `currency` removed from `PaymentRequest` |
| `FIELD_TYPE_CHANGED` | **`BREAKING`** | `amount` changed from `number` (float) to `integer` |
| `REQUIRED_FIELD_ADDED`| **`BREAKING`** | `payment_method` added to required fields list |
| `ENDPOINT_ADDED` | `NON_BREAKING` | New endpoint `GET /payments/v2/summary` added |
| `FIELD_ADDED` | `NON_BREAKING` | New optional property `notes` added to payload |

---

## 2. Downstream Impact Analysis

The `ImpactAnalyzer` performs static code analysis across consumer microservices (e.g. `services/order-service` making downstream calls to `services/payment-service`).

It isolates:
- Specific file paths (`services/order-service/app/clients/payment.py`)
- Line numbers where the altered endpoint or data field is referenced
- The exact code snippet and matched symbol

---

## 3. Candidate Patch Synthesis & Unified Diff

The `PatchSynthesizer` generates candidate source modifications, adapting downstream invocations to conform to the new schema:
- Generates standard GNU unified diff strings (`--- a/...`, `+++ b/...`)
- Supports safe pre-commit file application and rollback if automated tests fail.

---

## 4. GitHub Pull Request Draft Generation

The `PullRequestGenerator` packages the adaptation into a standard, reviewable GitHub Pull Request draft:
- **Branch**: `auto-api-maintenance/adapt-<service>-v<version>`
- **Title**: `fix(api-contract): adapt consumer clients to <service> v<version> breaking schema`
- **Markdown Body**:
  - Detailed summary of upstream schema deltas
  - Table of affected downstream files and line numbers
  - Test validation outcome (`✅ YES` / `❌ FAILED`)
  - Syntax-highlighted unified diff snippets

---

## 5. CLI Usage

### A. Compare OpenAPI Schemas
```bash
python -m self_maintaining_api.cli diff --old docs/schemas/v1.json --new docs/schemas/v2.json --service payment-service
```

### B. Analyze Downstream Code Impact
```bash
python -m self_maintaining_api.cli impact --old docs/schemas/v1.json --new docs/schemas/v2.json --service payment-service --search-dir services/
```

### C. Generate GitHub Pull Request Draft
```bash
python -m self_maintaining_api.cli generate-pr --old docs/schemas/v1.json --new docs/schemas/v2.json --service payment-service --search-dir services/
```

---

## 6. Automated Testing

Run the Phase 7 test suite:
```bash
pytest tests/test_self_maintaining_api.py -v
```
