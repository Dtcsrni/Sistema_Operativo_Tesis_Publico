import sys
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from check_serena_access import (  # noqa: E402
    attempt_start_http,
    build_effective_access,
    recommended_mode_today,
    recommendations,
)


class TestCheckSerenaAccess(unittest.TestCase):
    def test_recommended_mode_prefers_http_when_workspace_exposes_serena_local(self):
        mode = recommended_mode_today({"serena-local": True, "serena-local-py": False})
        self.assertIn("default_auto_started_workspace_route", mode)

    def test_effective_access_marks_stdio_as_healthy_but_not_exposed(self):
        report = {
            "mcp_workspace_config": {"profiles": {"serena-local": True, "serena-local-py": False}},
            "profiles": {
                "serena-local": {"healthcheck": {"status": "unavailable", "transport": "http"}, "transport": "http"},
                "serena-local-py": {"healthcheck": {"status": "ok", "transport": "stdio"}, "transport": "stdio"},
            },
        }
        effective = build_effective_access(report)
        self.assertFalse(effective["serena-local-py"]["workspace_enabled"])
        self.assertTrue(effective["serena-local-py"]["healthy_but_not_exposed"])
        self.assertFalse(effective["serena-local-py"]["available_and_recommended"])

    def test_recommendations_do_not_suggest_stdio_fallback_when_profile_not_exposed(self):
        report = {
            "mcp_workspace_config": {"profiles": {"serena-local": True, "serena-local-py": False}},
            "profiles": {
                "serena-local": {"healthcheck": {"status": "unavailable", "transport": "http"}},
                "serena-local-py": {"healthcheck": {"status": "ok", "transport": "stdio"}},
            },
            "log": {"exists": True},
            "bridge": {"status": "unavailable"},
        }
        advice = recommendations(report)
        joined = "\n".join(advice)
        self.assertIn("perfil activo recomendado del workspace es `serena-local`", joined)
        self.assertIn("autoarranque esperado", joined)
        self.assertIn("no esta expuesto en `.vscode/mcp.json`", joined)
        self.assertNotIn("fallback cuando el endpoint HTTP no este levantado", joined)

    def test_attempt_start_http_skips_when_profile_not_published(self):
        payload = attempt_start_http(ROOT, {"serena-local": False})
        self.assertFalse(payload["attempted"])
        self.assertEqual(payload["status"], "skipped")

    @mock.patch("check_serena_access._port_open")
    def test_attempt_start_http_detects_listening_port(self, mocked_open):
        mocked_open.return_value = True
        payload = attempt_start_http(ROOT, {"serena-local": True})
        self.assertTrue(payload["attempted"])
        self.assertEqual(payload["status"], "already_listening")


if __name__ == "__main__":
    unittest.main()
