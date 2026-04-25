import sys
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from check_agent_context_tools import compute_exit_code  # noqa: E402


class TestCheckAgentContextTools(unittest.TestCase):
    def test_exit_code_ready(self):
        code = compute_exit_code(
            {"available": True},
            {"effective_access": {"serena-local": {"available_and_recommended": True}}},
        )
        self.assertEqual(code, 0)

    def test_exit_code_serena_not_ready(self):
        code = compute_exit_code(
            {"available": True},
            {"effective_access": {"serena-local": {"available_and_recommended": False}}},
        )
        self.assertEqual(code, 2)

    def test_exit_code_caveman_not_ready(self):
        code = compute_exit_code(
            {"available": False},
            {"effective_access": {"serena-local": {"available_and_recommended": True}}},
        )
        self.assertEqual(code, 3)

    @mock.patch("check_agent_context_tools._run_shell")
    def test_caveman_report_marks_available(self, mocked_run):
        from check_agent_context_tools import caveman_report

        mocked_run.side_effect = [(0, "/root/.local/bin/caveman"), (0, "Codex CLI")]
        payload = caveman_report()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["path"], "/root/.local/bin/caveman")


if __name__ == "__main__":
    unittest.main()
