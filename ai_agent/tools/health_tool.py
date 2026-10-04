"""
Health Probe Tool for AI Agent.

Queries /health and /ready endpoints of registered microservices.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any

from ai_agent.schemas import ToolEvidence

DEFAULT_SERVICE_URLS = {
    "api-gateway": "http://localhost:8000",
    "order-service": "http://localhost:8001",
    "payment-service": "http://localhost:8002",
}


class HealthTool:
    def __init__(self, service_urls: Dict[str, str] = None):
        self.service_urls = service_urls or DEFAULT_SERVICE_URLS

    def check_service_health(self, service_name: str) -> ToolEvidence:
        """Inspects /health and /ready for a given service."""
        base_url = self.service_urls.get(service_name)
        if not base_url:
            return ToolEvidence(
                tool_name="health_tool",
                query_used=f"health_check({service_name})",
                raw_result={"error": f"Unknown service: {service_name}"},
                summary=f"Service '{service_name}' is not in known services registry.",
            )

        health_url = f"{base_url.rstrip('/')}/health"
        result: Dict[str, Any] = {}
        summary = ""

        try:
            req = urllib.request.Request(health_url)
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result["health"] = data
                status = data.get("status", "unknown")
                db_status = data.get("checks", {}).get("database", {}).get("status", "unknown")
                summary = f"Service '{service_name}' reported status '{status}'. Database status: '{db_status}'."
        except urllib.error.HTTPError as exc:
            result["health_error"] = f"HTTP {exc.code}"
            summary = f"Service '{service_name}' returned HTTP error {exc.code} on /health."
        except Exception as exc:
            result["health_error"] = str(exc)
            summary = f"Service '{service_name}' is UNREACHABLE at {health_url}: {exc}."

        return ToolEvidence(
            tool_name="health_tool",
            query_used=health_url,
            raw_result=result,
            summary=summary,
        )

    def check_all_services(self) -> Dict[str, ToolEvidence]:
        """Checks health across all registered services."""
        return {svc: self.check_service_health(svc) for svc in self.service_urls}
