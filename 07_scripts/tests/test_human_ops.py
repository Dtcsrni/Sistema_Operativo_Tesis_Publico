import argparse
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from build_dashboard import main as build_dashboard_main  # noqa: E402
from build_readme_portada import main as build_readme_main  # noqa: E402
from build_wiki import build_wiki  # noqa: E402
from canon import materialize_events  # noqa: E402
from publication import load_publication_config, publication_bundle_status, sanitize_text  # noqa: E402
from tesis import cmd_doctor, cmd_next, cmd_publish, cmd_source_status, cmd_status  # noqa: E402


class TestHumanOperationalLayer(unittest.TestCase):
    def test_sanitize_text_redacts_private_markers(self):
        config = load_publication_config()
        text = "file:///V:/Sistema_Operativo_Tesis_Posgrado/README.md VAL-STEP-470 EVT-0001 sha256:abcdef12 00_sistema_tesis/canon/events.jsonl 00_sistema_tesis/evidencia_privada/conversaciones_codex/demo/transcripcion.md 00_sistema_tesis/bitacora 00_sistema_tesis/reportes_semanales 00_sistema_tesis/config/agent_identity.json"
        sanitized = sanitize_text(text, config)
        self.assertNotIn("file:///", sanitized)
        self.assertNotIn("VAL-STEP-470", sanitized)
        self.assertNotIn("EVT-0001", sanitized)
        self.assertNotIn("sha256:abcdef12", sanitized)
        self.assertNotIn("00_sistema_tesis/evidencia_privada/conversaciones_codex", sanitized)
        self.assertNotIn("00_sistema_tesis/config/agent_identity.json", sanitized)
        self.assertIn("00_sistema_tesis/canon/events.jsonl", sanitized)
        self.assertIn("00_sistema_tesis/bitacora", sanitized)
        self.assertIn("00_sistema_tesis/reportes_semanales", sanitized)
        self.assertIn("[validacion_humana_interna]", sanitized)

    def test_sanitize_text_tolerates_missing_agent_identity(self):
        config = load_publication_config()
        text = "Texto sin identidad privada requerida."
        with patch("publication.load_agent_identity", side_effect=FileNotFoundError("agent_identity.json")):
            sanitized = sanitize_text(text, config)
        self.assertEqual(sanitized, text)

    def test_status_mentions_guided_commands(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cmd_status(argparse.Namespace())
        output = buffer.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("doctor", output)
        self.assertIn("next", output)

    def test_next_reports_pending_work(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cmd_next(argparse.Namespace())
        output = buffer.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("Tareas sugeridas", output)
        self.assertIn("Riesgos prioritarios", output)

    def test_publish_build_and_check(self):
        build_wiki()
        build_readme_main()
        build_dashboard_main()
        build_code = cmd_publish(argparse.Namespace(build=True, check=False))
        check_code = cmd_publish(argparse.Namespace(build=False, check=True))
        self.assertEqual(build_code, 0)
        self.assertEqual(check_code, 0)

    def test_doctor_check_passes_when_artifacts_are_in_sync(self):
        build_wiki()
        build_readme_main()
        build_dashboard_main()
        materialize_events(check=False)
        publication_bundle_status(build=True)
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cmd_doctor(argparse.Namespace(check=True))
        output = buffer.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("DOCTOR:", output)
        self.assertIn("Source evidence repo status", output)

    def test_source_status_check_passes_on_current_repo(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = cmd_source_status(argparse.Namespace(check=True, repo_only=True))
        output = buffer.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("SOURCE: STATUS", output)

    def test_dashboard_contains_sticky_quick_review_rail(self):
        build_dashboard_main()
        html = (ROOT / "06_dashboard" / "generado" / "index.html").read_text(encoding="utf-8")
        self.assertIn('id="que-revisar-siempre"', html)
        self.assertIn("panel-sticky", html)
        self.assertIn("review-link-card", html)
        self.assertIn('id="review-dock"', html)
        self.assertIn("data-review-toggle", html)


if __name__ == "__main__":
    unittest.main()
