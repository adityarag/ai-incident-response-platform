# Observability Architecture

## Overview

The observability architecture provides full-stack visibility across all cloud-native services in the AI Incident Response Platform. It combines:

1. **Prometheus**: Metric collection (scrape interval: 5s) for request count, latency (histograms), error rates, and system gauges.
2. **Loki**: Horizontally scalable log aggregation with structured JSON indexing.
3. **Grafana**: Real-time interactive dashboard visualizing service health, latencies, 5xx error spikes, and active workloads.
4. **OpenTelemetry & Correlation IDs**: Distributed tracing across service boundaries carrying W3C TraceContext and `X-Correlation-ID`.

---

## 1. Metrics (`Prometheus`)

Every service exposes a standard `/metrics` endpoint:
- **API Gateway**: `:8000/metrics`
- **Order Service**: `:8001/metrics`
- **Payment Service**: `:8002/metrics`

### Core Exported Metrics

| Metric Name | Type | Labels | Description |
|---|---|---|---|
| `http_requests_total` | Counter | `service`, `method`, `endpoint`, `status` | Total HTTP request counter |
| `http_request_duration_seconds` | Histogram | `service`, `method`, `endpoint` | Request duration buckets (5ms to 10s) |
| `http_requests_in_progress` | Gauge | `service`, `method`, `endpoint` | Current active in-flight requests |
| `service_health_status` | Gauge | `service` | 1 = Healthy, 0 = Unhealthy |

Prometheus UI is available at `http://localhost:9090`.

---

## 2. Distributed Tracing (`OpenTelemetry`)

Distributed requests propagate standard trace context:
- Trace ID (32-character hex)
- Span ID (16-character hex)
- Correlation ID (`X-Correlation-ID` header)

Whenever a request moves from `API Gateway` ➔ `Order Service` ➔ `Payment Service`, the `X-Correlation-ID` is forwarded in request headers and recorded in all downstream logs.

---

## 3. Structured Logging (`Loki`)

Logs are formatted as structured JSON:
```json
{
  "timestamp": "2026-10-03T14:48:12.102Z",
  "level": "INFO",
  "service": "order-service",
  "message": "Created order ORD-3E9ECA25 with status PENDING",
  "logger": "order-service",
  "correlation_id": "97e68fa2-6825-45d6-848d-6a3f47e09210",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7"
}
```

Promtail ships container logs directly into Loki (`http://localhost:3100`).

---

## 4. Grafana Dashboards

Grafana is pre-configured via declarative provisioning:
- **URL**: `http://localhost:3000` (Default credentials: `admin` / `admin`)
- **Data Sources**:
  - `Prometheus` (`http://prometheus:9090`)
  - `Loki` (`http://loki:3100`)
- **Pre-provisioned Dashboard**:
  - `Microservices Health & Telemetry` (`platform-overview`)
  - Displays real-time request rates, P95 latencies, 5xx error spikes, and in-flight requests by service.
