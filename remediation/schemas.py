"""
Schemas and Data Contracts for Self-Healing and Remediation Engine.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RemediationStatus(str, Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    VERIFIED = "VERIFIED"
    COOLDOWN_BLOCKED = "COOLDOWN_BLOCKED"


class ActionRequest(BaseModel):
    """
    Specific remediation action evaluated and tracked across its lifecycle.
    """
    action_id: str
    incident_id: Optional[str] = None
    action_type: str
    target_service: str
    risk_level: RiskLevel
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    status: RemediationStatus = RemediationStatus.PENDING_APPROVAL
    requires_human_approval: bool = False
    approver: Optional[str] = None
    approval_timestamp: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    executed_at: Optional[datetime] = None
    execution_output: Optional[str] = None


class VerificationResult(BaseModel):
    """
    Post-remediation health and SLA verification result.
    """
    action_id: str
    target_service: str
    verified: bool
    health_status: str
    summary: str
    metrics_snapshot: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
