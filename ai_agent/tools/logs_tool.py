"""
Log Inspection Tool for AI Agent.

Queries Loki / local service logs for error traces, stack traces, and correlation IDs.
"""

import json
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from ai_agent.schemas import ToolEvidence


class LogsTool:
    def __init__(self, loki_url: str = "http://localhost:3100"):
        self.loki_url = loki_url

    def query_loki(self, query: str, limit: int = 50) -> ToolEvidence:
        """Executes a LogQL query against Loki API."""
        url = f"{self.loki_url.rstrip('/')}/loki/api/v1/query_range?query={urllib.parse.quote(query)}&limit={limit}"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                streams = data.get("data", {}).get("result", [])
                total_entries = sum(len(s.get("values", [])) for s in streams)
                summary = f"Log query '{query}' retrieved {total_entries} log lines across {len(streams)} streams."
                return ToolEvidence(
                    tool_name="logs_tool",
                    query_used=query,
                    raw_result=streams,
                    summary=summary,
                )
        except Exception as exc:
            return ToolEvidence(
                tool_name="logs_tool",
                query_used=query,
                raw_result={"error": str(exc)},
                summary=f"Loki log query failed at {url}: {exc}",
            )

    def search_service_errors(self, service: str, limit: int = 20) -> ToolEvidence:
        """Searches for recent error logs matching a service name."""
        logql = f'{{service=~".*{service}.*"}} |= "ERROR"'
        return self.query_loki(logql, limit=limit)
