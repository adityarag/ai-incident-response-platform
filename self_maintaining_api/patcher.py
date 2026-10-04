"""
Automated Patch Synthesizer.

Generates candidate source-code patches to adapt downstream consumer services
to breaking upstream schema changes, formatting reviewable unified diffs.
"""

import difflib
import logging
import re
from typing import Dict, List, Optional

from self_maintaining_api.schemas import CandidatePatch, ImpactReport

logger = logging.getLogger("patch-synthesizer")


class PatchSynthesizer:
    """
    Synthesizes source code patches for consumer microservices.
    """

    def generate_patch(
        self,
        file_path: str,
        original_content: str,
        replacements: Dict[str, str],
        explanation: str = "Automated API contract adaptation",
    ) -> Optional[CandidatePatch]:
        """
        Generates a CandidatePatch applying symbol replacements to original_content.
        """
        patched_content = original_content
        changes_made = False

        for old_sym, new_sym in replacements.items():
            pattern = rf"\b{re.escape(old_sym)}\b"
            if re.search(pattern, patched_content):
                patched_content = re.sub(pattern, new_sym, patched_content)
                changes_made = True

        if not changes_made:
            return None

        # Generate unified diff
        orig_lines = original_content.splitlines(keepends=True)
        patched_lines = patched_content.splitlines(keepends=True)
        diff_lines = list(
            difflib.unified_diff(
                orig_lines,
                patched_lines,
                fromfile=f"a/{file_path}",
                tofile=f"b/{file_path}",
                lineterm="",
            )
        )
        diff_unified = "\n".join(diff_lines)

        return CandidatePatch(
            file_path=file_path,
            original_content=original_content,
            patched_content=patched_content,
            diff_unified=diff_unified,
            explanation=explanation,
        )

    def apply_patch_to_file(self, patch: CandidatePatch) -> bool:
        """Writes the patched content to the target file."""
        try:
            with open(patch.file_path, "w", encoding="utf-8") as f:
                f.write(patch.patched_content)
            logger.info(f"[+] Applied patch to {patch.file_path}")
            return True
        except Exception as err:
            logger.error(f"[-] Failed to apply patch to {patch.file_path}: {err}")
            return False

    def rollback_patch(self, patch: CandidatePatch) -> bool:
        """Restores original content to the target file."""
        try:
            with open(patch.file_path, "w", encoding="utf-8") as f:
                f.write(patch.original_content)
            logger.info(f"[+] Rolled back patch for {patch.file_path}")
            return True
        except Exception as err:
            logger.error(f"[-] Failed to rollback patch for {patch.file_path}: {err}")
            return False
