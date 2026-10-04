"""
Unit and Integration Tests for AI Investigation Agent and RCA Tools.
"""

import pytest
from unittest.mock import MagicMock

from ai_agent.schemas import (
    IncidentAlert,
    IncidentTriggerType,
    RCAReport,
    ToolEvidence,
)
from ai_agent.investigator import AIInvestigator
from ai_agent.detector import IncidentDetector
from ai_agent.tools import GitTool, HealthTool, LogsTool, MetricsTool


class TestAITools:
    def test_git_tool(self):
        tool = GitTool(repo_path=".")
        evidence = tool.get_recent_commits(limit=3)
        assert evidence.tool_name == "git_tool"
        assert len(evidence.raw_result) >= 1
        assert "Retrieved" in evidence.summary

    def test_health_tool_with_mocks(self):
        mock_tool = HealthTool()
        # Mock internal check
        mock_tool.check_service_health = MagicMock(return_value=ToolEvidence(
            tool_name="health_tool",
            query_used="http://localhost:8002/health",
            raw_result={"health": {"status": "degraded", "checks": {"database": {"status": "disconnected"}}}},
            summary="Service 'payment-service' reported status 'degraded'. Database status: 'disconnected'.",
        ))

        ev = mock_tool.check_service_health("payment-service")
        assert ev.tool_name == "health_tool"
        assert "disconnected" in ev.summary

    def test_metrics_tool_with_mocks(self):
        mock_metrics = MetricsTool()
        mock_metrics.query_prometheus = MagicMock(return_value=ToolEvidence(
            tool_name="metrics_tool",
            query_used="sum(rate(http_requests_total...))",
            raw_result=[{"metric": {}, "value": [1234567, "15.5"]}],
            summary="Query returned 1 metrics series.",
        ))

        ev = mock_metrics.get_service_error_rate("order-service")
        assert ev.tool_name == "metrics_tool"
        assert len(ev.raw_result) == 1

    def test_logs_tool_with_mocks(self):
        mock_logs = LogsTool()
        mock_logs.query_loki = MagicMock(return_value=ToolEvidence(
            tool_name="logs_tool",
            query_used='{service=~".*order-service.*"} |= "ERROR"',
            raw_result=[{"stream": {}, "values": [["12345", "Simulated error on /orders"]]}],
            summary="Log query retrieved 1 log lines.",
        ))

        ev = mock_logs.search_service_errors("order-service")
        assert ev.tool_name == "logs_tool"
        assert "1 log lines" in ev.summary


class TestAIInvestigator:
    def test_investigate_database_failure(self):
        # Mock health tool indicating database disconnect
        mock_health = HealthTool()
        mock_health.check_service_health = MagicMock(return_value=ToolEvidence(
            tool_name="health_tool",
            query_used="http://localhost:8002/health",
            raw_result={"health": {"status": "degraded", "checks": {"database": {"status": "disconnected"}}}},
            summary="Service 'payment-service' reported status 'degraded'. Database status: 'disconnected'.",
        ))
        mock_health.check_all_services = MagicMock(return_value={
            "payment-service": mock_health.check_service_health("payment-service"),
            "order-service": ToolEvidence(tool_name="health_tool", query_used="", raw_result={"health": {"status": "healthy"}}, summary="healthy"),
            "api-gateway": ToolEvidence(tool_name="health_tool", query_used="", raw_result={"health": {"status": "healthy"}}, summary="healthy"),
        })

        mock_metrics = MetricsTool()
        mock_metrics.get_service_error_rate = MagicMock(return_value=ToolEvidence(tool_name="metrics_tool", query_used="", raw_result=[], summary="ok"))
        mock_metrics.get_service_p95_latency = MagicMock(return_value=ToolEvidence(tool_name="metrics_tool", query_used="", raw_result=[], summary="ok"))

        mock_logs = LogsTool()
        mock_logs.search_service_errors = MagicMock(return_value=ToolEvidence(tool_name="logs_tool", query_used="", raw_result=[], summary="none"))

        investigator = AIInvestigator(
            health_tool=mock_health,
            metrics_tool=mock_metrics,
            logs_tool=mock_logs,
        )

        alert = IncidentAlert(
            alert_id="ALT-DB-1",
            service="payment-service",
            trigger_type=IncidentTriggerType.DATABASE_DISCONNECTED,
            description="Service payment-service reports database disconnected.",
        )

        rca: RCAReport = investigator.investigate(alert)

        assert rca.incident_id.startswith("INC-")
        assert rca.affected_service == "payment-service"
        assert rca.confidence_score >= 0.90
        assert "Database" in rca.probable_root_cause
        assert len(rca.remediation_recommendations) >= 1
        assert rca.remediation_recommendations[0].action_type == "clear_fault"

    def test_investigate_latency_spike(self):
        mock_health = HealthTool()
        mock_health.check_service_health = MagicMock(return_value=ToolEvidence(
            tool_name="health_tool",
            query_used="",
            raw_result={"health": {"status": "healthy", "checks": {"database": {"status": "connected"}}}},
            summary="Service 'order-service' healthy.",
        ))
        mock_health.check_all_services = MagicMock(return_value={})

        mock_metrics = MetricsTool()
        mock_metrics.get_service_error_rate = MagicMock(return_value=ToolEvidence(tool_name="metrics_tool", query_used="", raw_result=[], summary="ok"))
        mock_metrics.get_service_p95_latency = MagicMock(return_value=ToolEvidence(tool_name="metrics_tool", query_used="", raw_result=[], summary="ok"))

        mock_logs = LogsTool()
        mock_logs.search_service_errors = MagicMock(return_value=ToolEvidence(tool_name="logs_tool", query_used="", raw_result=[], summary="none"))

        investigator = AIInvestigator(
            health_tool=mock_health,
            metrics_tool=mock_metrics,
            logs_tool=mock_logs,
        )

        alert = IncidentAlert(
            alert_id="ALT-LAT-1",
            service="order-service",
            trigger_type=IncidentTriggerType.LATENCY_SPIKE,
            description="P95 latency exceeded 2.0s SLA threshold on /orders",
            endpoint="/orders",
        )

        rca = investigator.investigate(alert)
        assert rca.affected_service == "order-service"
        assert "latency" in rca.probable_root_cause.lower()
        assert rca.confidence_score >= 0.85

    def test_incident_detector_finds_unhealthy_service(self):
        mock_health = HealthTool()
        mock_health.check_all_services = MagicMock(return_value={
            "payment-service": ToolEvidence(
                tool_name="health_tool",
                query_used="",
                raw_result={"health": {"status": "degraded", "checks": {"database": {"status": "disconnected"}}}},
                summary="degraded",
            ),
            "order-service": ToolEvidence(
                tool_name="health_tool",
                query_used="",
                raw_result={"health": {"status": "healthy"}},
                summary="healthy",
            ),
        })

        detector = IncidentDetector(health_tool=mock_health)
        alerts = detector.check_for_incidents()

        assert len(alerts) == 1
        assert alerts[0].service == "payment-service"
        assert alerts[0].trigger_type == IncidentTriggerType.DATABASE_DISCONNECTED
