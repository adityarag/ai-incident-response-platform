"""
Incident Evidence Generator.

Builds structured IncidentEvidence objects from runtime state, metrics,
and logs for incident analysis.
"""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fault_injection.models import IncidentEvidence


def capture_incident_evidence(
    affected_service: str,
    fault_type: str,
    severity: str = "HIGH",
    affected_endpoint: Optional[str] = None,
    correlation_id: Optional[str] = None,
    status_code: Optional[int] = None,
    latency_observed_seconds: Optional[float] = None,
    relevant_logs: Optional[List[Dict[str, Any]]] = None,
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
) -> IncidentEvidence:
    """
    Creates a normalized IncidentEvidence record.
    """
    incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

    metrics_snapshot = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": affected_service,
        "endpoint": affected_endpoint,
        "status_code": status_code,
        "latency_seconds": latency_observed_seconds,
    }

    return IncidentEvidence(
        incident_id=incident_id,
        timestamp=datetime.now(timezone.utc),
        affected_service=affected_service,
        affected_endpoint=affected_endpoint,
        fault_type=fault_type,
        severity=severity,
        correlation_id=correlation_id,
        trace_id=trace_id,
        span_id=span_id,
        status_code=status_code,
        latency_observed_seconds=latency_observed_seconds,
        metrics_snapshot=metrics_snapshot,
        relevant_logs=relevant_logs or [],
        recovery_status="DETECTED",
    )
