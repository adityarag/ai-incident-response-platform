"""
Schemas and Data Contracts for Evaluation and Benchmarking Framework.
"""

from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field


class ScenarioResult(BaseModel):
    """Execution and timing metrics for a single evaluated incident scenario."""
    scenario_id: str
    scenario_name: str
    target_service: str
    mttd_seconds: float = Field(..., description="Mean Time To Detect (seconds)")
    mtti_seconds: float = Field(..., description="Mean Time To Investigate / Produce RCA (seconds)")
    mttr_seconds: float = Field(..., description="Mean Time To Remediate & Verify Recovery (seconds)")
    total_time_seconds: float = Field(..., description="Total elapsed time from injection to recovery (seconds)")
    probable_root_cause: str
    confidence_score: float
    recovered: bool = True
    autonomous: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BenchmarkSummary(BaseModel):
    """Aggregated quantitative performance benchmarks across all test scenarios."""
    total_scenarios: int
    mean_mttd_seconds: float
    mean_mtti_seconds: float
    mean_mttr_seconds: float
    mean_total_seconds: float
    success_rate_percent: float
    autonomous_rate_percent: float
    average_confidence: float
    scenarios: List[ScenarioResult] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
