"""
Command Line Interface for Remediation Engine and Approval Workflow.

Usage:
    python -m remediation.cli policies
    python -m remediation.cli auto-heal --service payment-service --reason "Database disconnected"
    python -m remediation.cli list-pending
    python -m remediation.cli approve --action-id ACT-123456
"""

import argparse
import logging
import sys
import uuid

from ai_agent.schemas import IncidentAlert, IncidentTriggerType
from remediation.approval import ApprovalManager
from remediation.orchestrator import SelfHealingOrchestrator
from remediation.policy import ACTION_RISK_MAP, WHITELISTED_ACTIONS, PolicyEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("remediation-cli")

# Shared global state for CLI sessions
_orchestrator = SelfHealingOrchestrator()


def cmd_policies(args):
    print("=" * 60)
    print("  SELF-HEALING REMEDIATION POLICIES & GUARDRAILS")
    print("=" * 60)
    print("Permitted Action Whitelist:")
    for act in sorted(WHITELISTED_ACTIONS):
        risk = ACTION_RISK_MAP.get(act, "UNKNOWN")
        autonomy = "Autonomous (Low Risk)" if risk.value == "LOW" else "Mandatory Approval"
        print(f"  - {act.ljust(22)} | Risk: {risk.value.ljust(8)} | {autonomy}")
    print("=" * 60)
    return 0


def cmd_auto_heal(args):
    alert = IncidentAlert(
        alert_id=f"ALT-{uuid.uuid4().hex[:6].upper()}",
        service=args.service,
        trigger_type=IncidentTriggerType(args.trigger_type),
        description=args.reason or f"Incident auto-heal triggered for {args.service}",
    )

    print(f"[*] Initiating Self-Healing pipeline for service '{args.service}'...")
    res = _orchestrator.handle_incident(alert)

    rca = res["rca_report"]
    print("\n" + "=" * 60)
    print(f"  INVESTIGATION: {rca.incident_id}")
    print(f"  Cause:         {rca.probable_root_cause} (Confidence: {rca.confidence_score*100:.1f}%)")
    print("=" * 60)

    if res["actions_executed"]:
        print("\n[+] Autonomous Actions Executed:")
        for act in res["actions_executed"]:
            print(f"  - [{act.status.value}] {act.action_type}: {act.execution_output}")

    if res["pending_approvals"]:
        print("\n[!] Actions Requiring Operator Approval:")
        for act in res["pending_approvals"]:
            print(f"  - [{act.action_id}] {act.action_type} (Risk: {act.risk_level.value}): {act.description}")

    if res["verifications"]:
        print("\n[+] Post-Action Verifications:")
        for v in res["verifications"]:
            v_status = "RECOVERED" if v.verified else "UNRESOLVED"
            print(f"  - [{v_status}] {v.target_service}: {v.summary}")

    print("=" * 60)
    return 0


def cmd_list_pending(args):
    pending = _orchestrator.approval_manager.list_pending_requests()
    if not pending:
        print("[+] No pending remediation actions awaiting approval.")
        return 0

    print(f"[!] {len(pending)} remediation action(s) awaiting approval:")
    for req in pending:
        print(f"  - [{req.action_id}] {req.target_service} -> {req.action_type} (Risk: {req.risk_level.value})")
        print(f"    Description: {req.description}")
        print(f"    Parameters:  {req.parameters}")
    return 0


def cmd_approve(args):
    try:
        _orchestrator.approval_manager.approve_action(args.action_id, approver=args.operator)
        print(f"[+] Action {args.action_id} successfully approved by '{args.operator}'.")
        print(f"[*] Executing approved remediation...")
        res = _orchestrator.execute_approved_action(args.action_id)
        act = res["action"]
        ver = res["verification"]
        print(f"[+] Execution Status: {act.status.value}")
        print(f"    Output: {act.execution_output}")
        print(f"    Verification: {ver.summary}")
        return 0
    except KeyError:
        print(f"[-] Error: Action '{args.action_id}' not found.")
        return 1
    except Exception as exc:
        print(f"[-] Approval/Execution failed: {exc}")
        return 1


def cmd_reject(args):
    try:
        _orchestrator.approval_manager.reject_action(
            args.action_id,
            approver=args.operator,
            reason=args.reason,
        )
        print(f"[-] Action {args.action_id} rejected by '{args.operator}'. Reason: {args.reason}")
        return 0
    except KeyError:
        print(f"[-] Error: Action '{args.action_id}' not found.")
        return 1


def main():
    parser = argparse.ArgumentParser(
        prog="remediation",
        description="Policy-Controlled Self-Healing & Remediation CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # policies
    subparsers.add_parser("policies", help="Display remediation whitelist and risk tiers")

    # auto-heal
    heal_parser = subparsers.add_parser("auto-heal", help="Trigger full investigation and self-healing loop")
    heal_parser.add_argument("--service", required=True, help="Target service name")
    heal_parser.add_argument(
        "--trigger-type",
        default="manual",
        choices=[t.value for t in IncidentTriggerType],
        help="Trigger type",
    )
    heal_parser.add_argument("--reason", default="", help="Description of incident symptoms")

    # list-pending
    subparsers.add_parser("list-pending", help="List actions requiring human operator review")

    # approve
    app_parser = subparsers.add_parser("approve", help="Approve and execute a pending high-risk action")
    app_parser.add_argument("--action-id", required=True, help="Action ID to approve")
    app_parser.add_argument("--operator", default="sre_oncall", help="Operator name or ID")

    # reject
    rej_parser = subparsers.add_parser("reject", help="Reject a pending high-risk action")
    rej_parser.add_argument("--action-id", required=True, help="Action ID to reject")
    rej_parser.add_argument("--operator", default="sre_oncall", help="Operator name or ID")
    rej_parser.add_argument("--reason", default="Declined by operator", help="Rejection rationale")

    args = parser.parse_args()

    if args.command == "policies":
        sys.exit(cmd_policies(args))
    elif args.command == "auto-heal":
        sys.exit(cmd_auto_heal(args))
    elif args.command == "list-pending":
        sys.exit(cmd_list_pending(args))
    elif args.command == "approve":
        sys.exit(cmd_approve(args))
    elif args.command == "reject":
        sys.exit(cmd_reject(args))


if __name__ == "__main__":
    main()
