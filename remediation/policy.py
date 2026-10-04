"""
Policy Engine for Remediation Guardrails and Risk Classification.

Enforces:
1. Permitted action whitelist
2. Strict risk classification (LOW, MEDIUM, HIGH, CRITICAL)
3. Mandatory human approval for high-impact operations
4. Flapping & oscillation prevention (cooldown limits)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set

from ai_agent.schemas import RemediationRecommendation
from remediation.schemas import ActionRequest, RemediationStatus, RiskLevel

logger = logging.getLogger("remediation-policy")

# Whitelist of strictly permitted actions
WHITELISTED_ACTIONS: Set[str] = {
    "clear_fault",
    "flush_cache",
    "reconnect_db",
    "scale_service",
    "restart_service",
    "rollback_deployment",
}

# Baseline risk mappings
ACTION_RISK_MAP: Dict[str, RiskLevel] = {
    "clear_fault": RiskLevel.LOW,
    "flush_cache": RiskLevel.LOW,
    "reconnect_db": RiskLevel.LOW,
    "scale_service": RiskLevel.MEDIUM,
    "restart_service": RiskLevel.HIGH,
    "rollback_deployment": RiskLevel.CRITICAL,
}


class PolicyEngine:
    def __init__(
        self,
        cooldown_window_seconds: int = 300,
        max_actions_per_window: int = 3,
    ):
        self.cooldown_window_seconds = cooldown_window_seconds
        self.max_actions_per_window = max_actions_per_window
        self._execution_history: Dict[str, List[datetime]] = {}

    def evaluate_recommendation(
        self,
        rec: RemediationRecommendation,
        incident_id: Optional[str] = None,
    ) -> ActionRequest:
        """
        Evaluates an AI recommendation against safety policies, risk matrices,
        and flapping guardrails.
        """
        action_type = rec.action_type.strip().lower()
        target_service = rec.target_service.strip().lower()
        action_id = f"ACT-{uuid.uuid4().hex[:8].upper()}"

        # 1. Action Whitelist Verification
        if action_type not in WHITELISTED_ACTIONS:
            logger.warning(f"Action '{action_type}' is NOT in approved whitelist. Rejecting.")
            return ActionRequest(
                action_id=action_id,
                incident_id=incident_id,
                action_type=action_type,
                target_service=target_service,
                risk_level=RiskLevel.CRITICAL,
                description=f"REJECTED: '{action_type}' is not a whitelisted remediation action.",
                status=RemediationStatus.REJECTED,
                requires_human_approval=True,
                rejection_reason="Action not in permitted whitelist",
            )

        # 2. Risk Classification
        # Use higher of baseline risk and recommendation specified risk
        baseline_risk = ACTION_RISK_MAP.get(action_type, RiskLevel.HIGH)
        rec_risk = RiskLevel(rec.risk_level.upper()) if hasattr(RiskLevel, rec.risk_level.upper()) else baseline_risk
        
        # Take the most conservative (highest risk)
        risk_rank = {RiskLevel.LOW: 1, RiskLevel.MEDIUM: 2, RiskLevel.HIGH: 3, RiskLevel.CRITICAL: 4}
        final_risk = rec_risk if risk_rank[rec_risk] >= risk_rank[baseline_risk] else baseline_risk

        # 3. Flapping / Cooldown check
        if self.is_service_in_cooldown(target_service):
            logger.warning(f"Target service '{target_service}' is flapping. Cooldown active.")
            return ActionRequest(
                action_id=action_id,
                incident_id=incident_id,
                action_type=action_type,
                target_service=target_service,
                risk_level=final_risk,
                description=f"Action blocked: '{target_service}' has exceeded {self.max_actions_per_window} remediations in {self.cooldown_window_seconds}s.",
                parameters=rec.parameters,
                status=RemediationStatus.COOLDOWN_BLOCKED,
                requires_human_approval=True,
                rejection_reason="Rate limit / flapping protection triggered",
            )

        # 4. Human Approval Requirement
        # LOW risk actions are autonomous; HIGH and CRITICAL mandate human approval
        requires_approval = final_risk in (RiskLevel.HIGH, RiskLevel.CRITICAL) or rec.requires_human_approval
        initial_status = RemediationStatus.PENDING_APPROVAL if requires_approval else RemediationStatus.APPROVED

        return ActionRequest(
            action_id=action_id,
            incident_id=incident_id,
            action_type=action_type,
            target_service=target_service,
            risk_level=final_risk,
            description=rec.description,
            parameters=rec.parameters,
            status=initial_status,
            requires_human_approval=requires_approval,
        )

    def is_service_in_cooldown(self, service_name: str) -> bool:
        """Checks if a service has triggered too many recent remediation actions."""
        now = datetime.now(timezone.utc)
        history = self._execution_history.get(service_name, [])
        # filter to recent window
        recent = [
            ts for ts in history
            if (now - ts).total_seconds() < self.cooldown_window_seconds
        ]
        self._execution_history[service_name] = recent
        return len(recent) >= self.max_actions_per_window

    def record_action_execution(self, service_name: str) -> None:
        """Records an execution event timestamp for flapping tracking."""
        now = datetime.now(timezone.utc)
        if service_name not in self._execution_history:
            self._execution_history[service_name] = []
        self._execution_history[service_name].append(now)
