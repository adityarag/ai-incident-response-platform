"""
Automated Tests for Phase 7: Self-Maintaining API Engine.
"""

import os
import tempfile
import pytest

from self_maintaining_api.diff_engine import SchemaDiffEngine
from self_maintaining_api.impact_analyzer import ImpactAnalyzer
from self_maintaining_api.patcher import PatchSynthesizer
from self_maintaining_api.pr_generator import PullRequestGenerator
from self_maintaining_api.schemas import (
    ChangeType,
    CompatibilityLevel,
    SchemaDiffResult,
)


@pytest.fixture
def sample_specs():
    spec_v1 = {
        "openapi": "3.0.0",
        "info": {"title": "Payment Service", "version": "1.0.0"},
        "paths": {
            "/payments/process": {
                "post": {
                    "summary": "Process payment",
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/PaymentRequest"}
                            }
                        }
                    },
                }
            },
            "/payments/{payment_id}": {
                "get": {"summary": "Get payment by ID"}
            },
        },
        "components": {
            "schemas": {
                "PaymentRequest": {
                    "type": "object",
                    "required": ["order_id", "amount"],
                    "properties": {
                        "order_id": {"type": "string"},
                        "amount": {"type": "number"},
                        "currency": {"type": "string"},
                    },
                }
            }
        },
    }

    # Spec v2 introduces:
    # 1. Renamed/removed endpoint: /payments/{payment_id} removed
    # 2. In PaymentRequest: "amount" changed type from number to integer (breaking)
    # 3. In PaymentRequest: "payment_method" added as REQUIRED (breaking)
    # 4. In PaymentRequest: "note" added as optional (non-breaking)
    spec_v2 = {
        "openapi": "3.0.0",
        "info": {"title": "Payment Service", "version": "2.0.0"},
        "paths": {
            "/payments/process": {
                "post": {
                    "summary": "Process payment",
                }
            },
            "/payments/v2/transactions/{id}": {
                "get": {"summary": "Get payment transaction"}
            },
        },
        "components": {
            "schemas": {
                "PaymentRequest": {
                    "type": "object",
                    "required": ["order_id", "amount", "payment_method"],
                    "properties": {
                        "order_id": {"type": "string"},
                        "amount": {"type": "integer"},
                        "payment_method": {"type": "string"},
                        "note": {"type": "string"},
                    },
                }
            }
        },
    }

    return spec_v1, spec_v2


class TestSchemaDiffEngine:
    def test_detect_non_breaking_changes(self):
        diff_engine = SchemaDiffEngine()
        spec_v1 = {
            "info": {"version": "1.0.0"},
            "paths": {"/health": {"get": {}}},
            "components": {
                "schemas": {
                    "Item": {
                        "type": "object",
                        "properties": {"name": {"type": "string"}},
                    }
                }
            },
        }
        spec_v2 = {
            "info": {"version": "1.1.0"},
            "paths": {
                "/health": {"get": {}},
                "/metrics": {"get": {}},  # added endpoint (non-breaking)
            },
            "components": {
                "schemas": {
                    "Item": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},  # optional added (non-breaking)
                        },
                    }
                }
            },
        }

        diff = diff_engine.compare_specs(spec_v1, spec_v2, service_name="item-service")
        assert not diff.has_breaking_changes
        assert len(diff.breaking_changes) == 0
        assert len(diff.non_breaking_changes) == 2

    def test_detect_breaking_changes(self, sample_specs):
        v1, v2 = sample_specs
        diff_engine = SchemaDiffEngine()
        diff = diff_engine.compare_specs(v1, v2, service_name="payment-service")

        assert diff.has_breaking_changes
        assert len(diff.breaking_changes) >= 3

        # Endpoint removed
        removed_endpoints = [c for c in diff.changes if c.change_type == ChangeType.ENDPOINT_REMOVED]
        assert len(removed_endpoints) == 1
        assert "/payments/{payment_id}" in removed_endpoints[0].path

        # Field type changed (amount: number -> integer)
        type_changes = [c for c in diff.changes if c.change_type == ChangeType.FIELD_TYPE_CHANGED]
        assert len(type_changes) == 1
        assert "amount" in type_changes[0].path

        # Required field added (payment_method)
        req_changes = [c for c in diff.changes if c.change_type == ChangeType.REQUIRED_FIELD_ADDED]
        assert len(req_changes) == 1
        assert "payment_method" in req_changes[0].path


class TestImpactAnalyzer:
    def test_analyze_repository_finds_usages(self, sample_specs):
        v1, v2 = sample_specs
        diff_engine = SchemaDiffEngine()
        diff = diff_engine.compare_specs(v1, v2, service_name="payment-service")

        with tempfile.TemporaryDirectory() as tmpdir:
            client_file = os.path.join(tmpdir, "client.py")
            with open(client_file, "w") as f:
                f.write(
                    'import requests\n'
                    'def pay():\n'
                    '    url = "/payments/{payment_id}"\n'
                    '    data = {"order_id": "123", "amount": 99.5}\n'
                    '    return requests.post("/payments/process", json=data)\n'
                )

            analyzer = ImpactAnalyzer()
            report = analyzer.analyze_repository(diff, search_dir=tmpdir)

            assert report.total_impacted_files == 1
            assert len(report.impacted_references) >= 2
            matched_syms = [r.matched_symbol for r in report.impacted_references]
            assert "amount" in matched_syms or "/payments/{payment_id}" in matched_syms


class TestPatchSynthesizer:
    def test_generate_and_apply_patch(self):
        synthesizer = PatchSynthesizer()
        code = 'data = {"old_payment_key": 500, "user": "alice"}\n'
        
        with tempfile.NamedTemporaryFile("w+", delete=False, suffix=".py") as tmp:
            tmp.write(code)
            tmp_path = tmp.name

        try:
            patch = synthesizer.generate_patch(
                file_path=tmp_path,
                original_content=code,
                replacements={"old_payment_key": "new_transaction_key"},
            )
            assert patch is not None
            assert "new_transaction_key" in patch.patched_content
            assert "old_payment_key" in patch.diff_unified
            assert "--- a/" in patch.diff_unified

            # Apply
            applied = synthesizer.apply_patch_to_file(patch)
            assert applied
            with open(tmp_path, "r") as f:
                assert "new_transaction_key" in f.read()

            # Rollback
            rolled_back = synthesizer.rollback_patch(patch)
            assert rolled_back
            with open(tmp_path, "r") as f:
                assert "old_payment_key" in f.read()

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)


class TestPullRequestGenerator:
    def test_pr_draft_formatting(self, sample_specs):
        v1, v2 = sample_specs
        diff_engine = SchemaDiffEngine()
        diff = diff_engine.compare_specs(v1, v2, service_name="payment-service")

        analyzer = ImpactAnalyzer()
        with tempfile.TemporaryDirectory() as tmpdir:
            impact = analyzer.analyze_repository(diff, search_dir=tmpdir)

        synthesizer = PatchSynthesizer()
        patch = synthesizer.generate_patch(
            file_path="services/order-service/client.py",
            original_content='req = {"amount": 50.0}\n',
            replacements={"50.0": "50"},
            explanation="Cast amount to integer per v2 schema",
        )

        pr_gen = PullRequestGenerator()
        draft = pr_gen.generate_draft(
            diff_result=diff,
            impact_report=impact,
            patches=[patch] if patch else [],
            tests_passed=True,
            test_summary="5 integration tests passed.",
        )

        assert "payment-service" in draft.title
        assert "auto-api-maintenance/" in draft.branch_name
        assert "## 2. Upstream Schema Changes" in draft.body_markdown
        assert "## 4. Test Verification Status" in draft.body_markdown
        assert "✅ YES" in draft.body_markdown
