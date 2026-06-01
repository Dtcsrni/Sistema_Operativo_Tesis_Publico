import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from audit import verify_decisions_val_integrity as integrity  # noqa: E402


class TestVerifyDecisionsValIntegrity(unittest.TestCase):
    def _write(self, path: Path, content: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def test_integrity_ok_minimal(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            decisions_dir = base / "00_sistema_tesis" / "decisiones"
            ledger = base / "00_sistema_tesis" / "bitacora" / "log_sesiones_trabajo_registradas.md"
            matrix = base / "00_sistema_tesis" / "bitacora" / "matriz_trazabilidad.md"
            events = base / "00_sistema_tesis" / "canon" / "events.jsonl"

            self._write(
                decisions_dir / "2026-05-01_DEC-0099_decision_prueba.md",
                "\n".join(
                    [
                        "<!-- SISTEMA_TESIS:PROTEGIDO -->",
                        "<!-- GID: DEC-0099 | 2026-05-01 | v1.0 | ACEPTADA -->",
                        "",
                        "# DEC-0099 Decision de Prueba",
                    ]
                ),
            )
            self._write(
                ledger,
                "\n".join(
                    [
                        "## [VAL-STEP-999]",
                        "- **Cadena:** [Anterior: INICIO] | [Siguiente: FIN]",
                        "<<<",
                        "contenido",
                        ">>>",
                    ]
                ),
            )
            self._write(
                matrix,
                "| 2026-05-01 | [VAL-STEP-999] | [DEC-0099] | Test | ALTO | Integridad | [x] Validado | [Log](log_sesiones_trabajo_registradas.md#val-step-999) |\n",
            )
            self._write(
                events,
                '{"event_id":"VAL-STEP-999","event_type":"human_validation"}\n',
            )

            old_root = integrity.ROOT
            old_decisions = integrity.DECISIONS_DIR
            old_ledger = integrity.LEDGER_PATH
            old_matrix = integrity.MATRIX_PATH
            old_events = integrity.EVENTS_PATH
            try:
                integrity.ROOT = base
                integrity.DECISIONS_DIR = decisions_dir
                integrity.LEDGER_PATH = ledger
                integrity.MATRIX_PATH = matrix
                integrity.EVENTS_PATH = events
                self.assertEqual(integrity.verify_decisions_val_integrity(), [])
            finally:
                integrity.ROOT = old_root
                integrity.DECISIONS_DIR = old_decisions
                integrity.LEDGER_PATH = old_ledger
                integrity.MATRIX_PATH = old_matrix
                integrity.EVENTS_PATH = old_events

    def test_detects_decision_collision(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            decisions_dir = base / "00_sistema_tesis" / "decisiones"
            ledger = base / "00_sistema_tesis" / "bitacora" / "log_sesiones_trabajo_registradas.md"
            matrix = base / "00_sistema_tesis" / "bitacora" / "matriz_trazabilidad.md"
            events = base / "00_sistema_tesis" / "canon" / "events.jsonl"

            content = "\n".join(
                [
                    "<!-- SISTEMA_TESIS:PROTEGIDO -->",
                    "<!-- GID: DEC-0099 | 2026-05-01 | v1.0 | ACEPTADA -->",
                    "",
                    "# DEC-0099 Decision de Prueba",
                ]
            )
            self._write(decisions_dir / "2026-05-01_DEC-0099_decision_a.md", content)
            self._write(
                decisions_dir / "2026-05-02_DEC-0099_decision_b.md",
                content.replace("2026-05-01", "2026-05-02"),
            )
            self._write(ledger, "## [VAL-STEP-999]\n")
            self._write(matrix, "| [VAL-STEP-999] | [DEC-0099] |\n")
            self._write(events, '{"event_id":"VAL-STEP-999"}\n')

            old_root = integrity.ROOT
            old_decisions = integrity.DECISIONS_DIR
            old_ledger = integrity.LEDGER_PATH
            old_matrix = integrity.MATRIX_PATH
            old_events = integrity.EVENTS_PATH
            try:
                integrity.ROOT = base
                integrity.DECISIONS_DIR = decisions_dir
                integrity.LEDGER_PATH = ledger
                integrity.MATRIX_PATH = matrix
                integrity.EVENTS_PATH = events
                errors = integrity.verify_decisions_val_integrity()
                self.assertTrue(any("colisión de ID" in error for error in errors))
            finally:
                integrity.ROOT = old_root
                integrity.DECISIONS_DIR = old_decisions
                integrity.LEDGER_PATH = old_ledger
                integrity.MATRIX_PATH = old_matrix
                integrity.EVENTS_PATH = old_events

    def test_detects_val_not_in_canon(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp)
            decisions_dir = base / "00_sistema_tesis" / "decisiones"
            ledger = base / "00_sistema_tesis" / "bitacora" / "log_sesiones_trabajo_registradas.md"
            matrix = base / "00_sistema_tesis" / "bitacora" / "matriz_trazabilidad.md"
            events = base / "00_sistema_tesis" / "canon" / "events.jsonl"

            self._write(
                decisions_dir / "2026-05-01_DEC-0099_decision_prueba.md",
                "\n".join(
                    [
                        "<!-- SISTEMA_TESIS:PROTEGIDO -->",
                        "<!-- GID: DEC-0099 | 2026-05-01 | v1.0 | ACEPTADA -->",
                        "",
                        "# DEC-0099 Decision de Prueba",
                    ]
                ),
            )
            self._write(ledger, "## [VAL-STEP-1234]\n")
            self._write(matrix, "| [VAL-STEP-1234] | [DEC-0099] |\n")
            self._write(events, '{"event_id":"EVT-0001"}\n')

            old_root = integrity.ROOT
            old_decisions = integrity.DECISIONS_DIR
            old_ledger = integrity.LEDGER_PATH
            old_matrix = integrity.MATRIX_PATH
            old_events = integrity.EVENTS_PATH
            try:
                integrity.ROOT = base
                integrity.DECISIONS_DIR = decisions_dir
                integrity.LEDGER_PATH = ledger
                integrity.MATRIX_PATH = matrix
                integrity.EVENTS_PATH = events
                errors = integrity.verify_decisions_val_integrity()
                self.assertTrue(any("no existe en canon/events.jsonl" in error for error in errors))
            finally:
                integrity.ROOT = old_root
                integrity.DECISIONS_DIR = old_decisions
                integrity.LEDGER_PATH = old_ledger
                integrity.MATRIX_PATH = old_matrix
                integrity.EVENTS_PATH = old_events


if __name__ == "__main__":
    unittest.main()
