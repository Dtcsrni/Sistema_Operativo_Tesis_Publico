from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(ROOT / "07_scripts" / "ops"))

import test_impact_gate as gate  # noqa: E402


class TestTestImpactGate(unittest.TestCase):
    def test_agent_ops_change_selects_focused_commands(self) -> None:
        report = gate.build_report(paths=["07_scripts/ops/agent_ops_core_gate.py"])
        ids = {item["id"] for item in report["selected_commands"]}
        self.assertIn("agent_ops_core_gate_unit", ids)
        self.assertIn("agent_ops_core_gate_dry", ids)
        self.assertEqual(report["integration_commands_require_justification"], [])

    def test_openclaw_change_marks_integration_justification(self) -> None:
        report = gate.build_report(paths=["runtime/openclaw/openclaw_local/engine.py"])
        ids = {item["id"] for item in report["selected_commands"]}
        self.assertIn("openclaw_focused", ids)
        self.assertIn("openclaw_focused", report["integration_commands_require_justification"])
        self.assertEqual(report["status"], "degraded")

    def test_direct_test_file_runs_itself(self) -> None:
        report = gate.build_report(paths=["07_scripts/tests/test_agent_ops_core_gate.py"])
        commands = {item["id"]: item for item in report["selected_commands"]}
        self.assertIn("unittest:07_scripts.tests.test_agent_ops_core_gate", commands)

    def test_history_match_reports_previous_ok_same_impact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            history = Path(tmp) / "history.jsonl"
            report = gate.build_report(paths=["07_scripts/ops/agent_ops_core_gate.py"], history_path=history)
            gate.append_history(history, report, "ok")
            second = gate.build_report(paths=["07_scripts/ops/agent_ops_core_gate.py"], history_path=history)
        self.assertEqual(second["redundancy_hint"], "previous_ok_same_impact")
        self.assertEqual(second["history_match"]["result_status"], "ok")

    def test_mcp_contract_shape_not_available_by_default(self) -> None:
        report = gate.build_report(paths=["07_scripts/ops/test_impact_gate.py"])
        ids = {item["id"] for item in report["selected_commands"]}
        self.assertIn("test_impact_gate_unit", ids)
        self.assertIn("test_impact_gate_dry", ids)

    def test_ignores_own_history_from_impact(self) -> None:
        report = gate.build_report(paths=["00_sistema_tesis/bitacora/audit_history/test_impact_history.jsonl"])
        self.assertEqual(report["changed_paths"], [])
        ids = {item["id"] for item in report["selected_commands"]}
        self.assertEqual(ids, {"agent_ops_core_gate_dry"})


if __name__ == "__main__":
    unittest.main()
