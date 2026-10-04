"""
Self-Healing Orchestrator.

Glues the incident response cycle:
Detection ➔ AI Investigation (RCA) ➔ Policy Evaluation ➔
Approval / Autonomous Remediation ➔ Verification ➔ Audit Trail.
"""

import logging
from typing import Any, Dict, List, Optional

from ai_agent.investigator import AIInvestigator
from ai_agent.schemas import IncidentAlert, RCAReport
from remediation.approval import ApprovalManager
from remediation.executor import RemediationExecutor
from remediation.policy import PolicyEngine
from remediation.schemas import ActionRequest, RemediationStatus, VerificationResult
from remediation.verifier import PostActionVerifier

logger = logging.getLogger("self-healing-orchestrator")


class SelfHealingOrchestrator:
    """
    End-to-end coordinator for autonomous and human-assisted remediation.
    """

    def __init__(
        self,
        investigator: Optional[AIInvestigator] = None,
        policy_engine: Optional[PolicyEngine] = None,
        executor: Optional[RemediationExecutor] = None,
        approval_manager: Optional[ApprovalManager] = None,
        verifier: Optional[PostActionVerifier] = None,
    ):
        self.investigator = investigator or AIInvestigator()
        self.policy_engine = policy_engine or PolicyEngine()
        self.executor = executor or RemediationExecutor()
        self.approval_manager = approval_manager or ApprovalManager()
        self.verifier = verifier or PostActionVerifier()
        self._audit_trail: List[Dict[str, Any]] = []

    def handle_incident(self, alert: IncidentAlert) -> Dict[str, Any]:
        """
        Processes an incoming incident through the full self-healing lifecycle.
        """
        logger.info(f"[*] Orchestrator handling incident '{alert.alert_id}' for '{alert.service}'")

        # 1. Investigate and produce RCA
        rca_report: RCAReport = self.investigator.investigate(alert)

        actions_taken: List[ActionRequest] = []
        pending_approvals: List[ActionRequest] = []
        verifications: List[VerificationResult] = []

        # 2. Evaluate recommendations against policy
        for rec in rca_report.remediation_recommendations:
            action_req = self.policy_engine.evaluate_recommendation(
                rec=rec,
                incident_id=rca_report.incident_id,
            )

            # 3. High-Risk / Needs Approval
            if action_req.requires_human_approval or action_req.status == RemediationStatus.PENDING_APPROVAL:
                self.approval_manager.register_request(action_req)
                pending_approvals.append(action_req)
                self._record_audit(
                    action="APPROVAL_REQUESTED",
                    details=f"High-risk action {action_req.action_id} ({action_req.action_type}) queued for review.",
                    target_service=action_req.target_service,
                )
                continue

            # 4. Low-Risk / Autonomous Remediation
            if action_req.status == RemediationStatus.APPROVED:
                executed_action = self.executor.execute(action_req)
                actions_taken.append(executed_action)
                self.policy_engine.record_action_execution(executed_action.target_service)

                self._record_audit(
                    action="AUTONOMOUS_REMEDIATION_EXECUTED",
                    details=f"Executed {executed_action.action_type}: {executed_action.execution_output}",
                    target_service=executed_action.target_service,
                )

                # 5. Post-Remediation Verification
                if executed_action.status == RemediationStatus.COMPLETED:
                    verif_result = self.verifier.verify(executed_action)
                    verifications.append(verif_result)
                    if verif_result.verified:
                        executed_action.status = RemediationStatus.VERIFIED

                    self._record_audit(
                        action="POST_REMEDIATION_VERIFICATION",
                        details=f"Verification result: {verif_result.summary}",
                        target_service=executed_action.target_service,
                    )

        return {
            "incident_id": rca_report.incident_id,
            "rca_report": rca_report,
            "actions_executed": actions_taken,
            "pending_approvals": pending_approvals,
            "verifications": verifications,
            "recovered": any(v.verified for v in verifications) if verifications else False,
        }

    def execute_approved_action(self, action_id: str) -> Dict[str, Any]:
        """
        Executes a previously pending action that has been approved by an operator.
        """
        action = self.approval_manager.get_request(action_id)
        if not action:
            raise KeyError(f"Action '{action_id}' not found.")

        if action.status != RemediationStatus.APPROVED:
            raise ValueError(f"Action '{action_id}' is not in APPROVED state (current: {action.status.value}).")

        executed_action = self.executor.execute(action)
        self.policy_engine.record_action_execution(executed_action.target_service)

        self._record_audit(
            action="MANUAL_APPROVED_REMEDIATION_EXECUTED",
            details=f"Executed {executed_action.action_type} by approver {action.approver}: {executed_action.execution_output}",
            target_service=executed_action.target_service,
        )

        verification = self.verifier.verify(executed_action)
        if verification.verified:
            executed_action.status = RemediationStatus.VERIFIED

        self._record_audit(
            action="POST_REMEDIATION_VERIFICATION",
            details=f"Post-approval verification: {verification.summary}",
            target_service=executed_action.target_service,
        )

        return {
            "action": executed_action,
            "verification": verification,
        }

    def _record_audit(self, action: str, details: str, target_service: str) -> None:
        """Appends an event to internal audit log trail."""
        event = {
            "action": action,
            "target_service": target_service,
            "details": details,
        }
        self._audit_trail.append(event)
        logger.info(f"[AUDIT] {action} on '{target_service}': {details}")

    def get_audit_trail(self) -> List[Dict[str, Any]]:
        return self._audit_trail
