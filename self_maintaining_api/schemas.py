"""
Data Contracts and Schemas for Self-Maintaining API Engine.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    ENDPOINT_ADDED = "endpoint_added"
    ENDPOINT_REMOVED = "endpoint_removed"
    FIELD_ADDED = "field_added"
    FIELD_REMOVED = "field_removed"
    FIELD_RENAMED = "field_renamed"
    FIELD_TYPE_CHANGED = "field_type_changed"
    REQUIRED_FIELD_ADDED = "required_field_added"
    ENUM_VALUE_REMOVED = "enum_value_removed"


class CompatibilityLevel(str, Enum):
    BREAKING = "BREAKING"
    NON_BREAKING = "NON_BREAKING"


class SchemaChange(BaseModel):
    """Represents a discrete semantic schema delta between API versions."""
    change_type: ChangeType
    compatibility: CompatibilityLevel
    path: str
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    description: str


class SchemaDiffResult(BaseModel):
    """Aggregated contract diff report across OpenAPI specifications."""
    service_name: str
    old_version: str = "1.0.0"
    new_version: str = "2.0.0"
    has_breaking_changes: bool = False
    changes: List[SchemaChange] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def breaking_changes(self) -> List[SchemaChange]:
        return [c for c in self.changes if c.compatibility == CompatibilityLevel.BREAKING]

    @property
    def non_breaking_changes(self) -> List[SchemaChange]:
        return [c for c in self.changes if c.compatibility == CompatibilityLevel.NON_BREAKING]


class ImpactedReference(BaseModel):
    """Specific line and symbol in consumer codebase affected by a schema change."""
    file_path: str
    line_number: int
    line_content: str
    matched_symbol: str
    impact_reason: str


class ImpactReport(BaseModel):
    """Repository-wide consumer impact analysis result."""
    service_name: str
    total_impacted_files: int = 0
    impacted_references: List[ImpactedReference] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CandidatePatch(BaseModel):
    """Proposed source code transformation resolving a schema incompatibility."""
    file_path: str
    original_content: str
    patched_content: str
    diff_unified: str
    explanation: str


class PullRequestDraft(BaseModel):
    """Structured Pull Request payload ready for GitHub submission and review."""
    pr_id: str
    title: str
    branch_name: str
    target_branch: str = "master"
    body_markdown: str
    patches: List[CandidatePatch] = Field(default_factory=list)
    tests_passed: bool = False
    test_summary: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
