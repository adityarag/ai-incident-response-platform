"""Fault Injection Package."""

from fault_injection.evidence import capture_incident_evidence
from fault_injection.manager import FaultManager, fault_manager
from fault_injection.middleware import attach_fault_injection, create_fault_router
from fault_injection.models import (
    FaultClearRequest,
    FaultConfig,
    FaultInjectRequest,
    FaultType,
    IncidentEvidence,
)

__all__ = [
    "FaultType",
    "FaultConfig",
    "FaultInjectRequest",
    "FaultClearRequest",
    "IncidentEvidence",
    "FaultManager",
    "fault_manager",
    "create_fault_router",
    "attach_fault_injection",
    "capture_incident_evidence",
]
