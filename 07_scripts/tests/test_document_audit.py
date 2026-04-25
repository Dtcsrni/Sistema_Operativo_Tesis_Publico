import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from document_audit import audit_document  # noqa: E402


class TestDocumentAudit(unittest.TestCase):
    def test_accepts_rich_prechecks_and_verbal_confirmation_block(self):
        content = """# Demo

- [x] Tarea trazable
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte:** [VAL-STEP-999]
  - **Texto exacto de confirmación verbal:** "si. implementa"
  - **Hash de confirmación verbal:** `sha256:abc`
  - **Fuente de verdad de confirmación:** `00_sistema_tesis/canon/events.jsonl :: VAL-STEP-999 :: human_validation.confirmation_text`

[LID]: log_sesiones_trabajo_registradas.md
[GOV]: ../config/ia_gobernanza.yaml
[AUD]: ../../07_scripts/build_all.py
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "demo.md"
            path.write_text(content, encoding="utf-8")
            self.assertEqual(audit_document(path), [])

    def test_rejects_missing_verbal_confirmation_source_block(self):
        content = """# Demo

- [x] Tarea trazable
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
  - **Soporte:** [VAL-STEP-999]

[LID]: log_sesiones_trabajo_registradas.md
[GOV]: ../config/ia_gobernanza.yaml
[AUD]: ../../07_scripts/build_all.py
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "demo.md"
            path.write_text(content, encoding="utf-8")
            errors = audit_document(path)
            self.assertTrue(any("confirmación verbal verificable" in error for error in errors))

    def test_rejects_file_scheme_reference_definitions(self):
        content = """# Demo

- [x] Tarea trazable
  - [x] Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima

[LID]: file:///tmp/log.md
[GOV]: ../config/ia_gobernanza.yaml
[AUD]: ../../07_scripts/build_all.py
"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "00_sistema_tesis" / "bitacora" / "demo.md"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            errors = audit_document(path)
            self.assertTrue(any("no trazable en GitHub" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

