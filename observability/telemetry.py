"""
Observability and Telemetry package.

Provides Prometheus metrics registry, middleware, and OpenTelemetry
instrumentation helpers for distributed tracing and correlated JSON logging.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Callable

from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    CollectorRegistry,
    generate_latest,
)

# ── Metric Definitions ────────────────────────────────────

# Create a custom registry or use standard
REGISTRY = CollectorRegistry(auto_describe=True)

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP request count partitioned by service, method, path, and status code",
    ["service", "method", "endpoint", "status"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency histogram in seconds",
    ["service", "method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

HTTP_REQUESTS_IN_PROGRESS = Gauge(
    "http_requests_in_progress",
    "Current active in-flight HTTP requests",
    ["service", "method", "endpoint"],
    registry=REGISTRY,
)

SERVICE_HEALTH_STATUS = Gauge(
    "service_health_status",
    "Current service health state (1 = healthy, 0 = unhealthy/degraded)",
    ["service"],
    registry=REGISTRY,
)


# ── Structured JSON Correlated Logging ─────────────────────

class CorrelatedJSONFormatter(logging.Formatter):
    """
    Formatter outputting logs in structured JSON format with
    correlation_id, trace_id, span_id, and service name.
    """

    def __init__(self, service_name: str):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "message": record.getMessage(),
            "logger": record.name,
        }

        # Inject correlation_id if set
        if hasattr(record, "correlation_id") and record.correlation_id:
            log_entry["correlation_id"] = record.correlation_id

        # OpenTelemetry Trace Context injection
        try:
            from opentelemetry import trace
            span = trace.get_current_span()
            ctx = span.get_span_context()
            if ctx and ctx.is_valid:
                log_entry["trace_id"] = format(ctx.trace_id, "032x")
                log_entry["span_id"] = format(ctx.span_id, "016x")
        except Exception:
            pass

        return json.dumps(log_entry)


def setup_service_logger(service_name: str, level=logging.INFO) -> logging.Logger:
    """Configures structured JSON logging for a microservice."""
    logger = logging.getLogger(service_name)
    logger.setLevel(level)

    # Avoid duplicate handlers
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(CorrelatedJSONFormatter(service_name))
        logger.addHandler(handler)
        logger.propagate = False

    return logger


# ── OpenTelemetry Tracer Setup ─────────────────────────────

def setup_opentelemetry(service_name: str, app: FastAPI | None = None):
    """
    Configures OpenTelemetry TracerProvider with OTLP exporter
    (if OTLP endpoint is available) and instruments FastAPI.
    """
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME

        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)

        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        trace.set_tracer_provider(provider)

        if app:
            from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
            FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)

        return provider
    except Exception as exc:
        logging.getLogger(service_name).warning(f"OTel setup skipped/failed: {exc}")
        return None


# ── Metrics Middleware & Route ─────────────────────────────

def attach_observability(app: FastAPI, service_name: str):
    """
    Attaches Prometheus metric collection middleware and /metrics
    endpoint to a FastAPI service.
    """

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: Callable) -> Response:
        # Don't meter the /metrics endpoint itself to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        # Normalize endpoints with path params (e.g. /orders/ORD-123 -> /orders/{id})
        parts = endpoint.strip("/").split("/")
        if len(parts) >= 2 and parts[0] in ("orders", "payments"):
            normalized_endpoint = f"/{parts[0]}/{{id}}"
        elif len(parts) >= 4 and parts[0] == "api" and parts[1] == "v1" and parts[2] in ("orders", "payments"):
            normalized_endpoint = f"/api/v1/{parts[2]}/{{id}}"
        else:
            normalized_endpoint = endpoint

        HTTP_REQUESTS_IN_PROGRESS.labels(
            service=service_name,
            method=method,
            endpoint=normalized_endpoint,
        ).inc()

        start_time = time.time()
        try:
            response = await call_next(request)
            status_code = str(response.status_code)
            return response
        except Exception:
            status_code = "500"
            raise
        finally:
            duration = time.time() - start_time
            HTTP_REQUEST_DURATION_SECONDS.labels(
                service=service_name,
                method=method,
                endpoint=normalized_endpoint,
            ).observe(duration)

            HTTP_REQUESTS_TOTAL.labels(
                service=service_name,
                method=method,
                endpoint=normalized_endpoint,
                status=status_code,
            ).inc()

            HTTP_REQUESTS_IN_PROGRESS.labels(
                service=service_name,
                method=method,
                endpoint=normalized_endpoint,
            ).dec()

    @app.get("/metrics", tags=["observability"])
    def metrics():
        """Exposes Prometheus scraped metrics."""
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST,
        )
