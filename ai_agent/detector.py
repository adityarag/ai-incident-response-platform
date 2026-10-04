"""
Incident Detector.

Monitors services, probes endpoints, evaluates telemetry against SLAs,
and triggers investigations when anomalies or failures occur.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from ai_agent.schemas import IncidentAlert, IncidentTriggerType
from ai_agent.tools.health_tool import HealthTool

logger = logging.getLogger("incident-detector")


class IncidentDetector:
    def __init__(self, health_tool: Optional[HealthTool] = None):
        self.health_tool = health_tool or HealthTool()

    def check_for_incidents(self) -> List[IncidentAlert]:
        """
        Polls registered services and returns a list of detected IncidentAlerts.
        """
        alerts: List[IncidentAlert] = []
        health_results = self.health_tool.check_all_services()

        for svc_name, evidence in health_results.items():
            raw = evidence.raw_result
            # 1. Unreachable / down
            if "health_error" in raw:
                alerts.append(
                    IncidentAlert(
                        alert_id=f"ALT-{uuid.uuid4().hex[:6].upper()}",
                        service=svc_name,
                        trigger_type=IncidentTriggerType.PROBE_FAILURE,
                        description=f"Service '{svc_name}' health check failed: {raw.get('health_error')}",
                    )
                )
                continue

            health_data = raw.get("health", {})
            status = health_data.get("status")

            # 2. Database disconnected / degraded
            db_status = health_data.get("checks", {}).get("database", {}).get("status")
            if db_status == "disconnected":
                alerts.append(
                    IncidentAlert(
                        alert_id=f"ALT-{uuid.uuid4().hex[:6].upper()}",
                        service=svc_name,
                        trigger_type=IncidentTriggerType.DATABASE_DISCONNECTED,
                        description=f"Service '{svc_name}' reports database disconnected.",
                    )
                )
            elif status in ("degraded", "unhealthy"):
                alerts.append(
                    IncidentAlert(
                        alert_id=f"ALT-{uuid.uuid4().hex[:6].upper()}",
                        service=svc_name,
                        trigger_type=IncidentTriggerType.PROBE_FAILURE,
                        description=f"Service '{svc_name}' reports {status} health state.",
                    )
                )

        return alerts
