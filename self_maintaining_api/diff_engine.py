"""
OpenAPI Schema Diff Engine.

Analyzes semantic deltas between OpenAPI 3.x contract definitions,
classifying modifications into BREAKING and NON_BREAKING categories.
"""

import logging
from typing import Any, Dict, List, Optional

from self_maintaining_api.schemas import (
    ChangeType,
    CompatibilityLevel,
    SchemaChange,
    SchemaDiffResult,
)

logger = logging.getLogger("schema-diff-engine")


class SchemaDiffEngine:
    """
    Computes semantic diffs between two OpenAPI specification dictionaries.
    """

    def compare_specs(
        self,
        old_spec: Dict[str, Any],
        new_spec: Dict[str, Any],
        service_name: str = "service",
    ) -> SchemaDiffResult:
        changes: List[SchemaChange] = []

        old_version = old_spec.get("info", {}).get("version", "1.0.0")
        new_version = new_spec.get("info", {}).get("version", "2.0.0")

        # 1. Compare Paths & HTTP Methods
        old_paths = old_spec.get("paths", {})
        new_paths = new_spec.get("paths", {})

        # Endpoints removed (BREAKING)
        for path, path_item in old_paths.items():
            if path not in new_paths:
                changes.append(
                    SchemaChange(
                        change_type=ChangeType.ENDPOINT_REMOVED,
                        compatibility=CompatibilityLevel.BREAKING,
                        path=path,
                        old_value=list(path_item.keys()),
                        new_value=None,
                        description=f"Endpoint '{path}' was removed from the API specification.",
                    )
                )
            else:
                # Compare methods
                for method, op in path_item.items():
                    if method.startswith("x-") or method == "parameters":
                        continue
                    if method not in new_paths[path]:
                        changes.append(
                            SchemaChange(
                                change_type=ChangeType.ENDPOINT_REMOVED,
                                compatibility=CompatibilityLevel.BREAKING,
                                path=f"{method.upper()} {path}",
                                old_value=method.upper(),
                                new_value=None,
                                description=f"HTTP method '{method.upper()}' on '{path}' was removed.",
                            )
                        )

        # Endpoints added (NON_BREAKING)
        for path, path_item in new_paths.items():
            if path not in old_paths:
                changes.append(
                    SchemaChange(
                        change_type=ChangeType.ENDPOINT_ADDED,
                        compatibility=CompatibilityLevel.NON_BREAKING,
                        path=path,
                        old_value=None,
                        new_value=list(path_item.keys()),
                        description=f"New endpoint '{path}' added to the API specification.",
                    )
                )

        # 2. Compare Components / Schemas (Data Models)
        old_schemas = old_spec.get("components", {}).get("schemas", {})
        new_schemas = new_spec.get("components", {}).get("schemas", {})

        for schema_name, old_s in old_schemas.items():
            if schema_name not in new_schemas:
                changes.append(
                    SchemaChange(
                        change_type=ChangeType.FIELD_REMOVED,
                        compatibility=CompatibilityLevel.BREAKING,
                        path=f"components.schemas.{schema_name}",
                        old_value=schema_name,
                        new_value=None,
                        description=f"Model schema '{schema_name}' was removed completely.",
                    )
                )
                continue

            new_s = new_schemas[schema_name]
            schema_changes = self._compare_single_schema(schema_name, old_s, new_s)
            changes.extend(schema_changes)

        has_breaking = any(c.compatibility == CompatibilityLevel.BREAKING for c in changes)

        return SchemaDiffResult(
            service_name=service_name,
            old_version=old_version,
            new_version=new_version,
            has_breaking_changes=has_breaking,
            changes=changes,
        )

    def _compare_single_schema(
        self,
        schema_name: str,
        old_s: Dict[str, Any],
        new_s: Dict[str, Any],
    ) -> List[SchemaChange]:
        changes: List[SchemaChange] = []

        old_props = old_s.get("properties", {})
        new_props = new_s.get("properties", {})
        old_required = set(old_s.get("required", []))
        new_required = set(new_s.get("required", []))

        # Check removed properties (BREAKING)
        for prop_name, prop_val in old_props.items():
            if prop_name not in new_props:
                changes.append(
                    SchemaChange(
                        change_type=ChangeType.FIELD_REMOVED,
                        compatibility=CompatibilityLevel.BREAKING,
                        path=f"{schema_name}.{prop_name}",
                        old_value=prop_val.get("type", "unknown"),
                        new_value=None,
                        description=f"Property '{prop_name}' was removed from model '{schema_name}'.",
                    )
                )
            else:
                # Property type change (BREAKING if incompatible)
                old_type = prop_val.get("type")
                new_type = new_props[prop_name].get("type")
                if old_type and new_type and old_type != new_type:
                    changes.append(
                        SchemaChange(
                            change_type=ChangeType.FIELD_TYPE_CHANGED,
                            compatibility=CompatibilityLevel.BREAKING,
                            path=f"{schema_name}.{prop_name}",
                            old_value=old_type,
                            new_value=new_type,
                            description=f"Property '{prop_name}' in '{schema_name}' changed type from '{old_type}' to '{new_type}'.",
                        )
                    )

        # Check added properties
        for prop_name, prop_val in new_props.items():
            if prop_name not in old_props:
                is_req = prop_name in new_required
                compat = CompatibilityLevel.BREAKING if is_req else CompatibilityLevel.NON_BREAKING
                ctype = ChangeType.REQUIRED_FIELD_ADDED if is_req else ChangeType.FIELD_ADDED
                desc = (
                    f"New REQUIRED property '{prop_name}' was added to '{schema_name}' (breaking for clients)."
                    if is_req
                    else f"New optional property '{prop_name}' was added to '{schema_name}'."
                )
                changes.append(
                    SchemaChange(
                        change_type=ctype,
                        compatibility=compat,
                        path=f"{schema_name}.{prop_name}",
                        old_value=None,
                        new_value=prop_val.get("type", "unknown"),
                        description=desc,
                    )
                )

        return changes
