"""
Tests for Phase 6: Policy-Controlled Remediation and Self-Healing Engine.
"""

import pytest
from datetime import datetime, timezone

from ai_agent.schemas import (
    IncidentAlert,
    IncidentTriggerType,
    RemediationRecommendation,
    ToolEvidence,
)
from fault_injection.manager import fault_manager
from fault_injection.models import FaultInjectRequest, FaultType
from remediation.approval import ApprovalManager
from remediation.executor import RemediationExecutor
from remediation.orchestrator import SelfHealingOrchestrator
from remediation.policy import PolicyEngine
from remediation.schemas import (
    ActionRequest,
    RemediationStatus,
    RiskLevel,
    VerificationResult,
)
from remediation.verifier import PostActionVerifier


class TestPolicyEngine:
    def test_whitelisted_actions_and_risk(self):
        policy = PolicyEngine()

        # Low-risk action
        rec_low = RemediationRecommendation(
            action_type="clear_fault",
            target_service="payment-service",
            risk_level="LOW",
            description="Clear active latency fault",
        )
        act_low = policy.evaluate_recommendation(rec_low)
        assert act_low.status == RemediationStatus.APPROVED
        assert act_low.risk_level == RiskLevel.LOW
        assert not act_low.requires_human_approval

        # High-risk action
        rec_high = RemediationRecommendation(
            action_type="restart_service",
            target_service="order-service",
            risk_level="HIGH",
            description="Restart container",
        )
        act_high = policy.evaluate_recommendation(rec_high)
        assert act_high.status == RemediationStatus.PENDING_APPROVAL
        assert act_high.risk_level == RiskLevel.HIGH
        assert act_high.requires_human_approval

    def test_non_whitelisted_action_rejected(self):
        policy = PolicyEngine()
        rec_bad = RemediationRecommendation(
            action_type="drop_database_table",
            target_service="payment-service",
            risk_level="CRITICAL",
            description="Destructive action not permitted",
        )
        act_bad = policy.evaluate_recommendation(rec_bad)
        assert act_bad.status == RemediationStatus.REJECTED
        assert "not a whitelisted" in act_bad.description

    def test_cooldown_and_flapping_prevention(self):
        policy = PolicyEngine(cooldown_window_seconds=60, max_actions_per_window=2)
        service = "payment-service"

        # Record 2 actions
        policy.record_action_execution(service)
        policy.record_action_execution(service)

        rec = RemediationRecommendation(
            action_type="clear_fault",
            target_service=service,
            risk_level="LOW",
            description="Clear fault",
        )
        act = policy.evaluate_recommendation(rec)
        assert act.status == RemediationStatus.COOLDOWN_BLOCKED
        assert "flapping" in act.rejection_reason.lower()


class TestApprovalManager:
    def test_approval_lifecycle(self):
        mgr = ApprovalManager()
        action = ActionRequest(
            action_id="ACT-100",
            action_type="restart_service",
            target_service="payment-service",
            risk_level=RiskLevel.HIGH,
            description="Restart container",
            requires_human_approval=True,
            status=RemediationStatus.PENDING_APPROVAL,
        )

        mgr.register_request(action)
        pending = mgr.list_pending_requests()
        assert len(pending) == 1
        assert pending[0].action_id == "ACT-100"

        # Approve
        approved = mgr.approve_action("ACT-100", approver="sre_oncall")
        assert approved.status == RemediationStatus.APPROVED
        assert approved.approver == "sre_oncall"
        assert len(mgr.list_pending_requests()) == 0

    def test_rejection_lifecycle(self):
        mgr = ApprovalManager()
        action = ActionRequest(
            action_id="ACT-200",
            action_type="rollback_deployment",
            target_service="order-service",
            risk_level=RiskLevel.CRITICAL,
            description="Rollback to previous release",
            requires_human_approval=True,
            status=RemediationStatus.PENDING_APPROVAL,
        )

        mgr.register_request(action)
        rejected = mgr.reject_action("ACT-200", approver="lead_engineer", reason="Maintenance window closed")
        assert rejected.status == RemediationStatus.REJECTED
        assert rejected.rejection_reason == "Maintenance window closed"
        assert len(mgr.list_pending_requests()) == 0


class TestRemediationExecutor:
    def test_execution_requires_approved_status(self):
        executor = RemediationExecutor()
        unapproved_action = ActionRequest(
            action_id="ACT-300",
            action_type="clear_fault",
            target_service="order-service",
            risk_level=RiskLevel.LOW,
            description="Clear fault",
            status=RemediationStatus.PENDING_APPROVAL,
        )
        res = executor.execute(unapproved_action)
        assert res.status == RemediationStatus.FAILED
        assert "blocked" in res.execution_output.lower()

    def test_execute_clear_fault(self):
        # Inject fault into manager first
        fault_manager.inject_fault(
            FaultInjectRequest(
                service="order-service",
                fault_type=FaultType.LATENCY,
                latency_seconds=2.0,
            )
        )
        assert len(fault_manager.get_active_faults("order-service")) > 0

        executor = RemediationExecutor()
        action = ActionRequest(
            action_id="ACT-301",
            action_type="clear_fault",
            target_service="order-service",
            risk_level=RiskLevel.LOW,
            description="Clear fault",
            status=RemediationStatus.APPROVED,
            parameters={"fault_type": "latency"},
        )
        res = executor.execute(action)
        assert res.status == RemediationStatus.COMPLETED
        assert len(fault_manager.get_active_faults("order-service")) == 0
        assert "cleared" in res.execution_output.lower()


class TestSelfHealingOrchestrator:
    def test_autonomous_self_healing_for_db_incident(self):
        # 1. Inject simulated database fault
        fault_manager.inject_fault(
            FaultInjectRequest(
                service="payment-service",
                fault_type=FaultType.DATABASE_FAILURE,
            )
        )
        assert fault_manager.is_db_failure_simulated("payment-service")

        # 2. Trigger orchestrator
        orchestrator = SelfHealingOrchestrator()
        alert = IncidentAlert(
            alert_id="ALT-DB-001",
            service="payment-service",
            trigger_type=IncidentTriggerType.DATABASE_DISCONNECTED,
            description="Service reports database connection failure",
        )

        result = orchestrator.handle_incident(alert)
        assert result["incident_id"] is not None
        assert len(result["actions_executed"]) >= 1

        executed = result["actions_executed"][0]
        assert executed.action_type == "clear_fault"
        assert executed.status in (RemediationStatus.COMPLETED, RemediationStatus.VERIFIED)

        # Fault must have been cleared automatically
        assert not fault_manager.is_db_failure_simulated("payment-service")

        # Audit trail must record events
        audit = orchestrator.get_audit_trail()
        assert any(entry["action"] == "AUTONOMOUS_REMEDIATION_EXECUTED" for entry in audit)
        assert any(entry["action"] == "POST_REMEDIATION_VERIFICATION" for entry in audit)

    def test_human_in_the_loop_for_high_risk_incident(self):
        orchestrator = SelfHealingOrchestrator()
        alert = IncidentAlert(
            alert_id="ALT-DOWN-002",
            service="order-service",
            trigger_type=IncidentTriggerType.PROBE_FAILURE,
            description="Service order-service connection refused, completely down",
        )

        result = orchestrator.handle_incident(alert)
        # Because order-service is down (simulated connection refused), RCA recommends restart_service (HIGH risk)
        assert len(result["pending_approvals"]) >= 1
        pending_act = result["pending_approvals"][0]
        assert pending_act.requires_human_approval
        assert pending_act.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

        # Approve and execute via orchestrator
        orchestrator.approval_manager.approve_action(pending_act.action_id, approver="operator_bob")
        exec_res = orchestrator.execute_approved_action(pending_act.action_id)
        assert exec_res["action"].status in (RemediationStatus.COMPLETED, RemediationStatus.VERIFIED)
        assert exec_res["action"].approver == "operator_bob"
