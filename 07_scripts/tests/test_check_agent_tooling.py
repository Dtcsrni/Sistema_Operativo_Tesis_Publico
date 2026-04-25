from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

import check_agent_tooling  # noqa: E402


class TestCheckAgentTooling(unittest.TestCase):
    def test_build_report_prioritizes_caveman_before_serena(self) -> None:
        fake_serena = {
            "effective_access": {"serena-local": {"available_and_recommended": True, "health_status": "ok", "workspace_enabled": True}},
            "recommendations": ["Serena recomendada"],
        }
        with patch.object(check_agent_tooling, "check_caveman", return_value={"available": True, "status": "ok", "command": "/usr/local/bin/caveman"}), patch.object(
            check_agent_tooling, "build_serena_report", return_value=fake_serena
        ):
            report = check_agent_tooling.build_report(ROOT)

        self.assertEqual(report["policy"]["workflow"], "caveman -> serena-local -> filesystem")
        self.assertEqual(report["policy"]["priority_order"][0], "caveman")
        self.assertEqual(report["policy"]["priority_order"][1], "serena-local")
        self.assertTrue(report["caveman"]["available"])

    def test_build_report_falls_back_when_serena_is_not_ready(self) -> None:
        fake_serena = {
            "effective_access": {"serena-local": {"available_and_recommended": False, "health_status": "unavailable", "workspace_enabled": False}},
            "recommendations": [],
        }
        with patch.object(check_agent_tooling, "check_caveman", return_value={"available": True, "status": "ok", "command": "/usr/local/bin/caveman"}), patch.object(
            check_agent_tooling, "build_serena_report", return_value=fake_serena
        ):
            report = check_agent_tooling.build_report(ROOT)

        self.assertEqual(report["policy"]["workflow"], "caveman -> filesystem -> restore serena")


if __name__ == "__main__":
    unittest.main()
