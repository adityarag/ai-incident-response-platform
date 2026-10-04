"""
Command Line Interface for AI Incident Investigation Agent.

Usage:
    python -m ai_agent.cli detect
    python -m ai_agent.cli investigate --service payment-service --reason "High latency observed"
    python -m ai_agent.cli scan-and-diagnose
"""

import argparse
import json
import logging
import sys
import uuid

from ai_agent.detector import IncidentDetector
from ai_agent.investigator import AIInvestigator
from ai_agent.schemas import IncidentAlert, IncidentTriggerType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai-agent-cli")


def cmd_detect(args):
    detector = IncidentDetector()
    alerts = detector.check_for_incidents()
    if not alerts:
        print("[+] No active incidents detected across services. System is healthy.")
        return 0

    print(f"[!] Detected {len(alerts)} incident(s):")
    for a in alerts:
        print(f"  - [{a.alert_id}] {a.service} ({a.trigger_type.value}): {a.description}")
    return 0


def cmd_investigate(args):
    investigator = AIInvestigator()
    alert = IncidentAlert(
        alert_id=f"ALT-{uuid.uuid4().hex[:6].upper()}",
        service=args.service,
        trigger_type=IncidentTriggerType(args.trigger_type),
        description=args.reason or f"Manual investigation triggered for {args.service}",
        endpoint=args.endpoint,
    )

    print(f"[*] Starting AI Investigation for service '{args.service}'...")
    report = investigator.investigate(alert)

    if args.json:
        print(report.model_dump_json(indent=2))
    else:
        print("\n" + "=" * 60)
        print(f"  ROOT CAUSE ANALYSIS REPORT: {report.incident_id}")
        print("=" * 60)
        print(f"Affected Service:   {report.affected_service}")
        print(f"Probable Root Cause:{report.probable_root_cause}")
        print(f"Confidence Score:   {report.confidence_score * 100:.1f}%")
        print(f"Summary:            {report.summary}")
        print("\nEvidence Gathered:")
        for ev in report.evidence_gathered:
            print(f"  - [{ev.tool_name}] {ev.summary}")

        print("\nHypotheses Evaluated:")
        for hyp in report.hypotheses_evaluated:
            status = "CONFIRMED" if hyp.get("supported") else "REJECTED"
            print(f"  - [{status}] {hyp.get('hypothesis')}: {hyp.get('reason')}")

        print("\nRemediation Recommendations:")
        for rec in report.remediation_recommendations:
            approval = " [Requires Approval]" if rec.requires_human_approval else " [Autonomous Safe]"
            print(f"  - [{rec.risk_level}] {rec.action_type}: {rec.description}{approval}")
        print("=" * 60)

    return 0


def cmd_scan_and_diagnose(args):
    detector = IncidentDetector()
    investigator = AIInvestigator()

    print("[*] Scanning cluster for incidents...")
    alerts = detector.check_for_incidents()
    if not alerts:
        print("[+] All services healthy. No investigations required.")
        return 0

    print(f"[!] Found {len(alerts)} active incident(s). Triggering investigations...")
    for alert in alerts:
        report = investigator.investigate(alert)
        print(f"\n[+] RCA for {report.affected_service} (Confidence: {report.confidence_score*100:.1f}%):")
        print(f"    Cause: {report.probable_root_cause}")
        print(f"    Action: {', '.join(r.action_type for r in report.remediation_recommendations)}")

    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="ai-agent",
        description="Autonomous AI Incident Response & RCA Agent CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # detect
    subparsers.add_parser("detect", help="Poll microservices and detect anomalous incidents")

    # investigate
    inv_parser = subparsers.add_parser("investigate", help="Execute AI investigation on a service")
    inv_parser.add_argument("--service", required=True, help="Target service name (e.g. payment-service)")
    inv_parser.add_argument("--endpoint", default=None, help="Target endpoint (e.g. /payments/process)")
    inv_parser.add_argument(
        "--trigger-type",
        default="manual",
        choices=[t.value for t in IncidentTriggerType],
        help="Trigger type",
    )
    inv_parser.add_argument("--reason", default="", help="Reason / symptom description")
    inv_parser.add_argument("--json", action="store_true", help="Output raw JSON RCAReport")

    # scan-and-diagnose
    subparsers.add_parser("scan-and-diagnose", help="Detect active incidents and automatically run RCA")

    args = parser.parse_args()

    if args.command == "detect":
        sys.exit(cmd_detect(args))
    elif args.command == "investigate":
        sys.exit(cmd_investigate(args))
    elif args.command == "scan-and-diagnose":
        sys.exit(cmd_scan_and_diagnose(args))


if __name__ == "__main__":
    main()
