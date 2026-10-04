"""
Git Change & Deployment Inspection Tool for AI Agent.

Inspects recent commits in the repository to determine whether recent deployments
or schema changes triggered an incident.
"""

import subprocess
from typing import List, Dict, Any

from ai_agent.schemas import ToolEvidence


class GitTool:
    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path

    def get_recent_commits(self, limit: int = 5) -> ToolEvidence:
        """Retrieves the most recent git commits to correlate with incident timestamps."""
        try:
            cmd = ["git", "log", f"-n{limit}", "--oneline", "--decorate"]
            result = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            commits = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
            summary = f"Retrieved {len(commits)} recent commit(s). Latest: '{commits[0] if commits else 'None'}'."
            return ToolEvidence(
                tool_name="git_tool",
                query_used=f"git log -n {limit}",
                raw_result=commits,
                summary=summary,
            )
        except Exception as exc:
            return ToolEvidence(
                tool_name="git_tool",
                query_used=f"git log -n {limit}",
                raw_result={"error": str(exc)},
                summary=f"Git inspection failed: {exc}",
            )
