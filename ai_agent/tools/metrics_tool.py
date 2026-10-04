"""
Prometheus Metrics Query Tool for AI Agent.

Queries Prometheus HTTP API (/api/v1/query) or service /metrics endpoints directly.
"""

import json
import urllib.parse
import urllib.request
import urllib.error
from typing import Any, Dict, Optional

from ai_agent.schemas import ToolEvidence


class MetricsTool:
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url

    def query_prometheus(self, query: str) -> ToolEvidence:
        """Executes an instant PromQL query against Prometheus."""
        url = f"{self.prometheus_url.rstrip('/')}/api/v1/query?query={urllib.parse.quote(query)}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("data", {}).get("result", [])
                summary = f"Query '{query}' returned {len(results)} metrics series."
                return ToolEvidence(
                    tool_name="metrics_tool",
                    query_used=query,
                    raw_result=results,
                    summary=summary,
                )
        except Exception as exc:
            # Fallback if Prometheus is unreachable
            return ToolEvidence(
                tool_name="metrics_tool",
                query_used=query,
                raw_result={"error": str(exc)},
                summary=f"Failed to query Prometheus at {url}: {exc}",
            )

    def get_service_error_rate(self, service: str) -> ToolEvidence:
        """Computes recent 5xx error rate for a service."""
        q = f'sum(rate(http_requests_total{{service="{service}",status=~"5.."}}[1m])) or vector(0)'
        return self.query_prometheus(q)

    def get_service_p95_latency(self, service: str) -> ToolEvidence:
        """Computes 95th percentile request latency in seconds."""
        q = f'histogram_quantile(0.95, sum by (le) (rate(http_request_duration_seconds_bucket{{service="{service}"}}[1m])))'
        return self.query_prometheus(q)
