"""
Self-Maintaining API Engine Package.
"""

from self_maintaining_api.diff_engine import SchemaDiffEngine
from self_maintaining_api.impact_analyzer import ImpactAnalyzer
from self_maintaining_api.patcher import PatchSynthesizer
from self_maintaining_api.pr_generator import PullRequestGenerator
from self_maintaining_api.schemas import (
    CandidatePatch,
    ChangeType,
    CompatibilityLevel,
    ImpactReport,
    ImpactedReference,
    PullRequestDraft,
    SchemaChange,
    SchemaDiffResult,
)

__all__ = [
    "CandidatePatch",
    "ChangeType",
    "CompatibilityLevel",
    "ImpactAnalyzer",
    "ImpactReport",
    "ImpactedReference",
    "PatchSynthesizer",
    "PullRequestDraft",
    "PullRequestGenerator",
    "SchemaChange",
    "SchemaDiffEngine",
    "SchemaDiffResult",
]
