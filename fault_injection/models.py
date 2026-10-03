"""
Fault Injection and Incident Evidence Data Models.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FaultType(str, Enum):
    LATENCY = "latency"
    ERROR_SPIKE = "error_spike"
    DATABASE_FAILURE = "database_failure"
    SERVICE_CRASH = "service_crash"
    DEPENDENCY_TIMEOUT = "dependency_timeout"


class FaultConfig(BaseModel):
    """Configuration for an active fault scenario."""
    fault_id: str = Field(..., description="Unique identifier for the fault instance")
    service: str = Field(..., description="Target service (api-gateway, order-service, payment-service, or all)")
    fault_type: FaultType = Field(..., description="Type of fault injected")
    endpoint: Optional[str] = Field(default=None, description="Target endpoint or path prefix (None for all)")
    latency_seconds: float = Field(default=0.0, ge=0.0, description="Latency to add in seconds")
    error_rate: float = Field(default=1.0, ge=0.0, le=1.0, description="Probability (0.0 to 1.0) of triggering error")
    status_code: int = Field(default=500, description="HTTP status code to return during error spike")
    error_message: str = Field(default="Injected fault failure", description="Custom error message")
    duration_seconds: Optional[int] = Field(default=None, ge=1, description="Automatic expiration in seconds (None for indefinite)")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

    model_config = {"use_enum_values": True}


class FaultInjectRequest(BaseModel):
    service: str = Field(..., description="Target service name")
    fault_type: FaultType = Field(..., description="Type of fault")
    endpoint: Optional[str] = Field(default=None, description="Optional target endpoint pattern")
    latency_seconds: float = Field(default=2.0, ge=0.0)
    error_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    status_code: int = Field(default=500)
    error_message: str = Field(default="Controlled fault injection triggered")
    duration_seconds: Optional[int] = Field(default=60)


class FaultClearRequest(BaseModel):
    service: Optional[str] = Field(default=None, description="Specific service or None to clear all")
    fault_id: Optional[str] = Field(default=None, description="Specific fault ID or None to clear all on service")


class IncidentEvidence(BaseModel):
    """
    Standard incident evidence schema capturing symptoms, metrics,
    logs, and trace correlation for downstream AI investigation.
    """
    incident_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    affected_service: str
    affected_endpoint: Optional[str] = None
    fault_type: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    correlation_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    status_code: Optional[int] = None
    latency_observed_seconds: Optional[float] = None
    metrics_snapshot: Dict[str, Any] = Field(default_factory=dict)
    relevant_logs: List[Dict[str, Any]] = Field(default_factory=list)
    recovery_status: str = "DETECTED"  # DETECTED, REMEDIATING, RECOVERED, FAILED
