"""Observability package."""

from observability.telemetry import (
    REGISTRY,
    HTTP_REQUESTS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_IN_PROGRESS,
    SERVICE_HEALTH_STATUS,
    setup_service_logger,
    setup_opentelemetry,
    attach_observability,
)

__all__ = [
    "REGISTRY",
    "HTTP_REQUESTS_TOTAL",
    "HTTP_REQUEST_DURATION_SECONDS",
    "HTTP_REQUESTS_IN_PROGRESS",
    "SERVICE_HEALTH_STATUS",
    "setup_service_logger",
    "setup_opentelemetry",
    "attach_observability",
]
