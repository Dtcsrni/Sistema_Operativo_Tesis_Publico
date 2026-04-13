import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from common import preferred_python_executable  # noqa: E402
from governance_gate import (  # noqa: E402
    auto_resolve_step_id,
    checks_for_stage,
    detect_projection_policy_errors,
    extract_step_ids_from_diff,
    get_protected_files,
    public_sync_check_dir,
    render_markdown,
    step_ids_exist_in_ledger,
    validate_step_id,
    write_attestation,
)


class TestGovernanceGate(unittest.TestCase):
    def test_detects_protected_files_by_policy(self):
        files = [
            "README.md",
            "00_sistema_tesis/canon/events.jsonl",
            "00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md",
        ]
        protected = get_protected_files(files)
        self.assertIn("00_sistema_tesis/canon/events.jsonl", protected)
        self.assertIn(
            "00_sistema_tesis/decisiones/2026-03-24_DEC-0014_protocolo_de_colaboración_humano-agente.md",
            protected,
        )
        self.assertNotIn("README.md", protected)

    def test_requires_step_id_when_protected_files_change(self):
        errors = validate_step_id("pre-commit", "", ["00_sistema_tesis/canon/events.jsonl"], [])
        self.assertTrue(errors)
        self.assertIn("Step ID", errors[0])

    def test_accepts_existing_step_id_present_in_ledger(self):
        errors = validate_step_id("pre-commit", "VAL-STEP-278", ["00_sistema_tesis/canon/events.jsonl"], [])
        self.assertEqual(errors, [])

    def test_accepts_multiple_ledger_step_ids_during_pre_push(self):
        errors = validate_step_id(
            "pre-push",
            "",
            ["00_sistema_tesis/canon/events.jsonl"],
            ["VAL-STEP-410", "VAL-STEP-420", "VAL-STEP-430"],
        )
        self.assertEqual(errors, [])

    def test_still_requires_explicit_step_id_for_multiple_ids_in_pre_commit(self):
        errors = validate_step_id(
            "pre-commit",
            "",
            ["00_sistema_tesis/canon/events.jsonl"],
            ["VAL-STEP-410", "VAL-STEP-420"],
        )
        self.assertTrue(errors)
        self.assertIn("multiples Step IDs", errors[0])

    def test_auto_resolve_step_id_picks_latest_detected_for_protected_commit(self):
        resolved, auto_selected = auto_resolve_step_id(
            "",
            ["VAL-STEP-470", "VAL-STEP-490", "VAL-STEP-500"],
            ["00_sistema_tesis/canon/events.jsonl"],
        )
        self.assertEqual(resolved, "VAL-STEP-500")
        self.assertTrue(auto_selected)

    def test_auto_resolve_step_id_respects_explicit_value(self):
        resolved, auto_selected = auto_resolve_step_id(
            "VAL-STEP-490",
            ["VAL-STEP-470", "VAL-STEP-500"],
            ["00_sistema_tesis/canon/events.jsonl"],
        )
        self.assertEqual(resolved, "VAL-STEP-490")
        self.assertFalse(auto_selected)

    def test_step_ids_exist_in_ledger_for_known_values(self):
        self.assertTrue(step_ids_exist_in_ledger(["VAL-STEP-410", "VAL-STEP-420"]))

    def test_extract_step_ids_prefers_structural_header_over_chain_reference(self):
        diff_text = """diff --git a/00_sistema_tesis/canon/events.jsonl b/00_sistema_tesis/canon/events.jsonl
+++ b/00_sistema_tesis/canon/events.jsonl
@@ -1,0 +1 @@
+{"actor":{"display_name":"OpenAI","id":"OpenAI","model_version":"GPT-5","provider":"OpenAI","type":"ai"},"affected_files":["00_sistema_tesis/canon/events.jsonl"],"content_hash":"x","event_id":"VAL-STEP-430","event_type":"human_validation","human_validation":{"required":true,"status":"validated","step_id":"VAL-STEP-430","validated_at":"2026-03-26"},"links":{"reference":"[DEC-0014]"},"occurred_at":"2026-03-26 00:00:00","payload":{"content_text":"hola"},"prev_event_hash":"y","risk_level":"ALTO","session_id":"codex"}"""
        step_ids = extract_step_ids_from_diff(
            diff_text,
            ["00_sistema_tesis/canon/events.jsonl"],
        )
        self.assertEqual(step_ids, ["VAL-STEP-430"])

    def test_extract_step_ids_from_matrix_row_ignores_anchor_duplicates(self):
        diff_text = """diff --git a/00_sistema_tesis/bitacora/matriz_trazabilidad.md b/00_sistema_tesis/bitacora/matriz_trazabilidad.md
+++ b/00_sistema_tesis/bitacora/matriz_trazabilidad.md
@@ -1,0 +1 @@
+| 2026-03-26 | [VAL-STEP-430] | [DEC-0014] | Cierre | ALTO | Responsabilidad (ISO 42001) | [x] Validado | [Log](log_conversaciones_ia.md#val-step-430) |
"""
        step_ids = extract_step_ids_from_diff(
            diff_text,
            ["00_sistema_tesis/bitacora/matriz_trazabilidad.md"],
        )
        self.assertEqual(step_ids, ["VAL-STEP-430"])

    def test_rejects_projection_edits_without_canon_change(self):
        errors = detect_projection_policy_errors(["00_sistema_tesis/bitacora/log_conversaciones_ia.md"])
        self.assertTrue(errors)
        self.assertIn("proyecciones", errors[0].lower())

    def test_session_bitacora_is_not_treated_as_primary_projection(self):
        errors = detect_projection_policy_errors(["00_sistema_tesis/bitacora/2026-03-26_bitacora_sesion.md"])
        self.assertEqual(errors, [])

    def test_markdown_reflects_attestation_fields(self):
        attestation = {
            "generated_at": "2026-03-26 12:00:00",
            "stage": "pre-commit",
            "status": "ok",
            "agent": "test-agent",
            "step_id": "VAL-STEP-278",
            "changed_files": ["README.md"],
            "protected_files_touched": ["00_sistema_tesis/bitacora/log_conversaciones_ia.md"],
            "checks_run": ["Validacion de soberania", "Validar estructura"],
            "checks_failed": [],
            "recommendations": ["Mantener el gate como unica puerta de enforcement para hooks, CI y wrappers."],
            "git_ref": "main",
            "git_commit": "deadbeef",
        }
        markdown = render_markdown(attestation)
        self.assertIn("VAL-STEP-278", markdown)
        self.assertIn("pre-commit", markdown)
        self.assertIn("Validar estructura", markdown)

    def test_write_attestation_creates_json_and_markdown(self):
        output_dir = ROOT / ".pytest_cache" / "governance_gate_test"
        attestation = {
            "generated_at": "2026-03-26 12:00:00",
            "stage": "manual",
            "status": "ok",
            "agent": "test-agent",
            "step_id": "",
            "changed_files": [],
            "protected_files_touched": [],
            "checks_run": ["Validacion de soberania"],
            "checks_failed": [],
            "recommendations": ["ok"],
            "git_ref": "main",
            "git_commit": "deadbeef",
            "hashes": {},
            "check_details": [],
        }
        json_path, md_path = write_attestation(attestation, output_dir)
        self.assertTrue(json_path.exists())
        self.assertTrue(md_path.exists())

    def test_ci_checks_use_repo_preferred_python(self):
        checks = checks_for_stage("ci")
        test_check = next(item for item in checks if item[0] == "Pruebas")
        self.assertEqual(test_check[1][0], preferred_python_executable())
        self.assertEqual(test_check[1][1:], ["-m", "pytest", "-q", "-s"])

    def test_ci_checks_include_public_downstream_verification(self):
        checks = checks_for_stage("ci")
        sync_check = next(item for item in checks if item[0] == "Verificar downstream público sanitizado")
        self.assertIn("07_scripts/sync_public_repo.py", sync_check[1][1:])
        self.assertIn("--check", sync_check[1])
        self.assertIn(public_sync_check_dir().replace("\\", "/"), [item.replace("\\", "/") for item in sync_check[1]])

    def test_ci_checks_can_skip_gpg_when_environment_requests_it(self):
        with patch.dict("os.environ", {"SISTEMA_TESIS_SKIP_GPG_CHECK": "1"}, clear=False):
            checks = checks_for_stage("ci")
        labels = [item[0] for item in checks]
        self.assertNotIn("Verificar firma GPG", labels)
        self.assertIn("Pruebas", labels)


if __name__ == "__main__":
    unittest.main()
