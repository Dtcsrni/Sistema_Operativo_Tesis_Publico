from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(ROOT / "07_scripts" / "ops"))

import human_validation_gate as gate  # noqa: E402


class TestHumanValidationGate(unittest.TestCase):
    def test_sha256_text_normalizes_newlines(self) -> None:
        self.assertEqual(gate.sha256_text("a\r\nb\n"), gate.sha256_text("a\nb\n"))

    def test_missing_step_id_blocks_without_canon_mutation(self) -> None:
        report = gate.build_report(paths=[])
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["required_step_id"], "PENDIENTE")
        self.assertEqual(report["details"]["mode"], "dry_run_no_canon_mutation")
        self.assertIn("missing_step_id", report["blocking_reason"])

    def test_invalid_step_id_format_is_reported(self) -> None:
        validation = gate.validate_human_inputs(
            step_id="STEP-1",
            source_event_id="",
            confirmation_text="confirmo",
        )
        self.assertIn("invalid_step_id_format", validation["errors"])
        self.assertTrue(validation["confirmation_text_hash"])

    def test_signoff_status_detects_current_and_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "doc.md"
            target.write_text("uno\n", encoding="utf-8")
            current_hash = gate.sha256_file(target)
            signoffs = root / "sign_offs.json"
            signoffs.write_text(
                json.dumps(
                    {
                        "sign_offs": [
                            {
                                "archivo": "doc.md",
                                "hash_verificado": current_hash,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(gate.signoff_status(["doc.md"], root=root, signoffs_path=signoffs)[0]["state"], "current")
            target.write_text("dos\n", encoding="utf-8")
            self.assertEqual(gate.signoff_status(["doc.md"], root=root, signoffs_path=signoffs)[0]["state"], "drift")

    def test_signoff_missing_path_blocks_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            signoffs = root / "sign_offs.json"
            signoffs.write_text('{"sign_offs":[]}', encoding="utf-8")
            report = gate.build_report(
                step_id="bad",
                paths=["missing.md"],
                root=root,
                signoffs_path=signoffs,
            )
            self.assertIn("signoff_drift_or_missing", report["blocking_reason"])


if __name__ == "__main__":
    unittest.main()
