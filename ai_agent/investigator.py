"""
AI Investigation Engine.

Coordinates investigation workflows:
1. Gathers evidence via HealthTool, MetricsTool, LogsTool, and GitTool.
2. Evaluates hypotheses (Database Disconnection, Artificial Latency, Error Spikes, Downstream Service Outage).
3. Produces a structured Root Cause Analysis (RCAReport) with confidence scores and actionable recommendations.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ai_agent.schemas import (
    IncidentAlert,
    RCAReport,
    RemediationRecommendation,
    ToolEvidence,
)
from ai_agent.tools import GitTool, HealthTool, LogsTool, MetricsTool

logger = logging.getLogger("ai-investigator")


class AIInvestigator:
    """
    Autonomous Root Cause Analysis Investigator.
    Operates using strictly sandboxed tools.
    """

    def __init__(
        self,
        health_tool: Optional[HealthTool] = None,
        metrics_tool: Optional[MetricsTool] = None,
        logs_tool: Optional[LogsTool] = None,
        git_tool: Optional[GitTool] = None,
    ):
        self.health_tool = health_tool or HealthTool()
        self.metrics_tool = metrics_tool or MetricsTool()
        self.logs_tool = logs_tool or LogsTool()
        self.git_tool = git_tool or GitTool()

    def investigate(self, alert: IncidentAlert) -> RCAReport:
        """
        Executes a thorough investigation given an incoming incident alert.
        """
        start_time = time.time()
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        target_service = alert.service
        logger.info(f"[*] Starting investigation {incident_id} for service '{target_service}'")

        evidence_list: List[ToolEvidence] = []
        hypotheses_evaluated: List[Dict[str, Any]] = []

        # ── Step 1: Health Probes ───────────────────────────────────
        health_evidence = self.health_tool.check_service_health(target_service)
        evidence_list.append(health_evidence)

        all_health = self.health_tool.check_all_services()
        unhealthy_services = [
            svc for svc, ev in all_health.items()
            if "unreachable" in ev.summary.lower() or "degraded" in ev.summary.lower() or "error" in ev.summary.lower()
        ]

        # ── Step 2: Metrics Analysis ────────────────────────────────
        if self.metrics_tool:
            err_metrics = self.metrics_tool.get_service_error_rate(target_service)
            evidence_list.append(err_metrics)

            latency_metrics = self.metrics_tool.get_service_p95_latency(target_service)
            evidence_list.append(latency_metrics)

        # ── Step 3: Logs Analysis ───────────────────────────────────
        if self.logs_tool:
            logs_evidence = self.logs_tool.search_service_errors(target_service, limit=10)
            evidence_list.append(logs_evidence)

        # ── Step 4: Deployment & Change Inspection ──────────────────
        if self.git_tool:
            git_evidence = self.git_tool.get_recent_commits(limit=3)
            evidence_list.append(git_evidence)

        # ── Step 5: Hypotheses Evaluation & Synthesis ───────────────
        probable_root_cause = "Unknown anomaly"
        confidence_score = 0.50
        summary = ""
        recommendations: List[RemediationRecommendation] = []

        # Check Hypothesis A: Database Failure / Connection Starvation
        raw_health = health_evidence.raw_result.get("health", {})
        db_check = raw_health.get("checks", {}).get("database", {})
        db_status = db_check.get("status", "") if isinstance(db_check, dict) else str(db_check)

        if db_status == "disconnected" or "database" in alert.description.lower() or "disconnected" in health_evidence.summary.lower():
            hypotheses_evaluated.append({
                "hypothesis": "Database Connectivity Exhaustion",
                "matched": True,
                "confidence": 0.95,
                "reason": "Service /health reported database status disconnected or connection pool failure.",
            })
            probable_root_cause = "Database connection pool exhaustion or simulated database failure."
            confidence_score = 0.95
            summary = f"Service '{target_service}' cannot connect to PostgreSQL datastore."
            recommendations.append(
                RemediationRecommendation(
                    action_type="clear_fault",
                    target_service=target_service,
                    risk_level="LOW",
                    description="Clear active database fault simulation or verify PostgreSQL network connectivity.",
                    parameters={"fault_type": "database_failure"},
                    requires_human_approval=False,
                )
            )

        # Check Hypothesis B: Artificial Latency / Downstream Bottleneck
        elif "latency" in alert.description.lower() or alert.trigger_type.value == "latency_spike":
            hypotheses_evaluated.append({
                "hypothesis": "Severe Endpoint Latency Degradation",
                "matched": True,
                "confidence": 0.90,
                "reason": "Alert and telemetry identify latency exceeding SLA threshold.",
            })
            probable_root_cause = "Artificial latency or CPU/io thread starvation on request handler."
            confidence_score = 0.90
            summary = f"Service '{target_service}' is experiencing significant latency delays."
            recommendations.append(
                RemediationRecommendation(
                    action_type="clear_fault",
                    target_service=target_service,
                    risk_level="LOW",
                    description="Clear injected latency fault or scale service replicas.",
                    parameters={"fault_type": "latency"},
                    requires_human_approval=False,
                )
            )

        # Check Hypothesis C: Error Spike / 5xx Fault
        elif "500" in alert.description or "error_spike" in alert.description.lower() or alert.trigger_type.value == "error_spike":
            hypotheses_evaluated.append({
                "hypothesis": "High 5xx Application Error Rate",
                "matched": True,
                "confidence": 0.92,
                "reason": "Error spike observed on HTTP endpoints accompanied by 5xx responses.",
            })
            probable_root_cause = "Elevated 5xx application error rate injected via fault middleware."
            confidence_score = 0.92
            summary = f"Service '{target_service}' is failing incoming requests with 5xx internal server errors."
            recommendations.append(
                RemediationRecommendation(
                    action_type="clear_fault",
                    target_service=target_service,
                    risk_level="LOW",
                    description="Clear error spike fault scenario or roll back latest revision.",
                    parameters={"fault_type": "error_spike"},
                    requires_human_approval=False,
                )
            )

        # Check Hypothesis D: Complete Service Outage / Process Down
        elif "unreachable" in health_evidence.summary.lower() or target_service in unhealthy_services:
            hypotheses_evaluated.append({
                "hypothesis": "Service Outage / Crash",
                "matched": True,
                "confidence": 0.96,
                "reason": f"Service '{target_service}' failed liveness probe and connection refused.",
            })
            probable_root_cause = f"Process failure or container crash on service '{target_service}'."
            confidence_score = 0.96
            summary = f"Service '{target_service}' is completely unreachable."
            recommendations.append(
                RemediationRecommendation(
                    action_type="restart_service",
                    target_service=target_service,
                    risk_level="HIGH",
                    description=f"Restart container 'platform-{target_service}' to recover process.",
                    parameters={"container": f"platform-{target_service}"},
                    requires_human_approval=True,
                )
            )

        # Default fallback
        else:
            hypotheses_evaluated.append({
                "hypothesis": "Generic Degradation",
                "matched": True,
                "confidence": 0.60,
                "reason": "Alert was triggered but evidence indicates mixed telemetry.",
            })
            probable_root_cause = f"Transient failure or network anomaly on {target_service}."
            confidence_score = 0.60
            summary = f"Alert '{alert.alert_id}' triggered on {target_service}."

        duration = time.time() - start_time

        return RCAReport(
            incident_id=incident_id,
            timestamp=datetime.now(timezone.utc),
            affected_service=target_service,
            affected_endpoint=alert.endpoint,
            summary=summary,
            probable_root_cause=probable_root_cause,
            confidence_score=confidence_score,
            evidence_gathered=evidence_list,
            hypotheses_evaluated=hypotheses_evaluated,
            remediation_recommendations=recommendations,
            investigation_duration_seconds=round(duration, 3),
        )
