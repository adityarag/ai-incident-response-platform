"""
Repository Impact Analyzer.

Scans downstream microservice codebases to identify files, functions,
and lines directly affected by upstream API schema changes.
"""

import os
import re
import logging
from typing import List, Optional

from self_maintaining_api.schemas import (
    ImpactReport,
    ImpactedReference,
    SchemaDiffResult,
)

logger = logging.getLogger("impact-analyzer")


class ImpactAnalyzer:
    """
    Performs static code analysis across consumer microservices to identify
    dependencies on modified API contracts.
    """

    def analyze_repository(
        self,
        diff_result: SchemaDiffResult,
        search_dir: str,
        exclude_service: Optional[str] = None,
    ) -> ImpactReport:
        impacted_refs: List[ImpactedReference] = []
        breaking_changes = diff_result.breaking_changes

        # Extract symbols and paths to look for
        symbols_to_track = set()
        for c in breaking_changes:
            # e.g., "PaymentCreate.amount" -> "amount"
            if "." in c.path:
                field = c.path.split(".")[-1]
                symbols_to_track.add(field)
            # Endpoint path e.g. "/payments/process"
            if "/" in c.path:
                # clean method prefix if present e.g. "POST /payments/process"
                endpoint = c.path.split(" ")[-1]
                symbols_to_track.add(endpoint)

        logger.info(f"[*] Scanning {search_dir} for {len(symbols_to_track)} impacted symbols: {symbols_to_track}")

        # Walk search_dir looking for Python files
        for root, _, files in os.walk(search_dir):
            # Exclude upstream service's own definition if requested
            if exclude_service and exclude_service in root:
                continue
            # Skip hidden dirs, caches, and venv
            if ".git" in root or "__pycache__" in root or "venv" in root or ".pytest_cache" in root:
                continue

            for file in files:
                if not file.endswith(".py"):
                    continue

                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, search_dir)

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()

                    for idx, line in enumerate(lines, start=1):
                        for sym in symbols_to_track:
                            # Match symbol occurrence (as string literal, identifier, or attr)
                            pattern = rf"\b{re.escape(sym)}\b"
                            if re.search(pattern, line) or (sym.startswith("/") and sym in line):
                                impacted_refs.append(
                                    ImpactedReference(
                                        file_path=rel_path.replace("\\", "/"),
                                        line_number=idx,
                                        line_content=line.strip(),
                                        matched_symbol=sym,
                                        impact_reason=f"Downstream reference to modified schema symbol '{sym}'",
                                    )
                                )
                except Exception as err:
                    logger.warning(f"Error reading {full_path}: {err}")

        unique_files = len(set(ref.file_path for ref in impacted_refs))

        return ImpactReport(
            service_name=diff_result.service_name,
            total_impacted_files=unique_files,
            impacted_references=impacted_refs,
        )
