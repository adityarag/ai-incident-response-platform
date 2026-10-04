"""
Schemas for AI Investigation Agent and Root Cause Analysis (RCA).
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IncidentTriggerType(str, Enum):
    PROBE_FAILURE = "probe_failure"
    ERROR_SPIKE = "error_spike"
    LATENCY_SPIKE = "latency_spike"
    DATABASE_DISCONNECTED = "database_disconnected"
    MANUAL = "manual"


class IncidentAlert(BaseModel):
    """Trigger payload initiating an investigation."""
    alert_id: str
    service: str
    trigger_type: IncidentTriggerType
    description: str
    endpoint: Optional[str] = None
    metric_value: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ToolEvidence(BaseModel):
    """Evidence item collected from an observability tool."""
    tool_name: str
    query_used: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    raw_result: Any
    summary: str


class RemediationRecommendation(BaseModel):
    """Action suggested by the AI agent to resolve the incident."""
    action_type: str  # restart_service, clear_fault, scale_up, rollback_deployment, run_db_migration
    target_service: str
    risk_level: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    requires_human_approval: bool = False


class RCAReport(BaseModel):
    """
    Structured Root Cause Analysis Report produced by the AI Agent.
    """
    incident_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    affected_service: str
    affected_endpoint: Optional[str] = None
    summary: str
    probable_root_cause: str
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence in RCA (0.0 to 1.0)")
    evidence_gathered: List[ToolEvidence] = Field(default_factory=list)
    hypotheses_evaluated: List[Dict[str, Any]] = Field(default_factory=list)
    remediation_recommendations: List[RemediationRecommendation] = Field(default_factory=list)
    investigation_duration_seconds: float = 0.0
