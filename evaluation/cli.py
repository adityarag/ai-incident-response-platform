"""
Command Line Interface for Benchmark Runner and Evaluation Framework.

Usage:
    python -m evaluation.cli run-benchmarks
    python -m evaluation.cli compare
"""

import argparse
import logging
import sys

from evaluation.metrics import MetricsFormatter
from evaluation.runner import BenchmarkRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("evaluation-cli")


def cmd_run_benchmarks(args):
    print("=" * 65)
    print("  RUNNING SYSTEM EVALUATION & BENCHMARK SUITE")
    print("=" * 65)
    runner = BenchmarkRunner()
    summary = runner.run_all_scenarios()
    report_md = MetricsFormatter.format_markdown_report(summary)
    print(report_md)
    return 0


def cmd_compare(args):
    runner = BenchmarkRunner()
    summary = runner.run_all_scenarios()
    print("=" * 65)
    print("  COMPARATIVE EVALUATION SUMMARY")
    print("=" * 65)
    print(f"Autonomous Healing Rate:  {summary.autonomous_rate_percent:.1f}%")
    print(f"Overall Recovery Rate:     {summary.success_rate_percent:.1f}%")
    print(f"Average RCA Confidence:    {summary.average_confidence*100:.1f}%")
    print(f"Mean Total Recovery Time:  {summary.mean_total_seconds:.3f}s (vs. ~45-90 mins manual)")
    print("=" * 65)
    return 0


def main():
    parser = argparse.ArgumentParser(
        prog="evaluation",
        description="Empirical Benchmarking & Evaluation Framework CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("run-benchmarks", help="Execute all 5 benchmark scenarios and print report")
    subparsers.add_parser("compare", help="Display comparative metrics summary")

    args = parser.parse_args()

    if args.command == "run-benchmarks":
        sys.exit(cmd_run_benchmarks(args))
    elif args.command == "compare":
        sys.exit(cmd_compare(args))


if __name__ == "__main__":
    main()
