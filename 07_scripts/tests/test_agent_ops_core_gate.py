from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(ROOT / "07_scripts" / "ops"))

import agent_ops_core_gate as gate  # noqa: E402


class TestAgentOpsCoreGate(unittest.TestCase):
    def test_standard_result_has_required_public_keys(self) -> None:
        payload = gate.standard_result(status="ok", available=True, recommended=True)
        for key in gate.STANDARD_KEYS:
            self.assertIn(key, payload)
        self.assertEqual(payload["next_action"], "none")

    def test_validate_spec_file_accepts_required_terms_and_pending_step(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spec.md"
            path.write_text(
                "\n".join(
                    [
                        "decisions:",
                        'step_id: "PENDIENTE"',
                        "## Objetivo",
                        "## Alcance",
                        "## Rutas Afectadas",
                        "## Gates Publicos",
                        "## Pruebas y Aceptacion",
                        "## Rollback",
                        "## Cierre de Trazabilidad",
                        "## FRE",
                        "## ESE",
                    ]
                ),
                encoding="utf-8",
            )
            payload = gate.validate_spec_file(path)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["required_step_id"], "PENDIENTE")

    def test_validate_spec_file_blocks_missing_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "spec.md"
            path.write_text("## Objetivo\n", encoding="utf-8")
            payload = gate.validate_spec_file(path)
        self.assertEqual(payload["status"], "blocked")
        self.assertIn("missing_terms", payload["details"])

    def test_external_mcp_contracts_use_required_shape(self) -> None:
        required = {
            "capability_id",
            "backend",
            "auth_required",
            "live_check",
            "fallback",
            "allowed_domains",
            "trace_level",
        }
        self.assertEqual(len(gate.EXTERNAL_MCP_CONTRACTS), 6)
        for contract in gate.EXTERNAL_MCP_CONTRACTS:
            self.assertTrue(required.issubset(contract))
            self.assertFalse(contract.get("available", False))

    def test_traceability_gate_does_not_fabricate_step_id(self) -> None:
        payload = gate.traceability_gate("")
        self.assertEqual(payload["status"], "degraded")
        self.assertEqual(payload["required_step_id"], "PENDIENTE")
        self.assertIn("missing_human_step_id", payload["blocking_reason"])

    def test_no_live_report_is_actionable_without_running_external_checks(self) -> None:
        report = gate.build_report(live=False, max_residue_items=1)
        self.assertIn(report["status"], {"ok", "degraded", "blocked"})
        self.assertIn("spec", report["checks"])
        self.assertIn("context_residue_inventory", report["checks"])
        self.assertIn("test_impact", report["checks"])
        self.assertNotIn("serena_access", report["checks"])


if __name__ == "__main__":
    unittest.main()
