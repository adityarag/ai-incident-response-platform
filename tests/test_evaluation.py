"""
Automated Tests for Phase 10: System Evaluation and Benchmarking Framework.
"""

import pytest
from evaluation.metrics import MetricsFormatter
from evaluation.runner import BenchmarkRunner
from evaluation.schemas import BenchmarkSummary, ScenarioResult


class TestEvaluationFramework:
    def test_metrics_formatter_output(self):
        scenario = ScenarioResult(
            scenario_id="SCENARIO-01",
            scenario_name="Database Connection Starvation",
            target_service="payment-service",
            mttd_seconds=0.10,
            mtti_seconds=0.45,
            mttr_seconds=0.30,
            total_time_seconds=0.85,
            probable_root_cause="Database connection exhaustion",
            confidence_score=0.95,
            recovered=True,
            autonomous=True,
        )

        summary = BenchmarkSummary(
            total_scenarios=1,
            mean_mttd_seconds=0.10,
            mean_mtti_seconds=0.45,
            mean_mttr_seconds=0.30,
            mean_total_seconds=0.85,
            success_rate_percent=100.0,
            autonomous_rate_percent=100.0,
            average_confidence=0.95,
            scenarios=[scenario],
        )

        md = MetricsFormatter.format_markdown_report(summary)
        assert "# Empirical Evaluation & Benchmarking Report" in md
        assert "Mean Time to Detect (MTTD)" in md
        assert "Comparative Benchmark: Manual Ops vs. AI Autonomous Platform" in md
        assert "SCENARIO-01" in md
        assert "99.8% Faster" in md

    def test_benchmark_api_contract_scenario(self):
        runner = BenchmarkRunner()
        result = runner.benchmark_api_contract_evolution()
        assert result.scenario_id == "SCENARIO-05"
        assert result.recovered is True
        assert result.autonomous is True
        assert result.confidence_score == 1.0

    def test_benchmark_runner_full_suite(self):
        runner = BenchmarkRunner()
        summary = runner.run_all_scenarios()

        assert summary.total_scenarios == 5
        assert summary.success_rate_percent == 100.0
        assert summary.autonomous_rate_percent == 80.0  # 4 autonomous, 1 human-in-the-loop
        assert summary.mean_total_seconds > 0.0
        assert len(summary.scenarios) == 5

        # Check individual scenario IDs
        scenario_ids = [s.scenario_id for s in summary.scenarios]
        assert scenario_ids == [
            "SCENARIO-01",
            "SCENARIO-02",
            "SCENARIO-03",
            "SCENARIO-04",
            "SCENARIO-05",
        ]
