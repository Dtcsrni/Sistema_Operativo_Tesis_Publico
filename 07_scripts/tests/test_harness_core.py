from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
import sys

sys.path.insert(0, str(ROOT / "07_scripts"))

from harness import core  # noqa: E402


class HarnessCoreTests(unittest.TestCase):
    def test_manifest_is_provider_agnostic_and_covers_siot(self) -> None:
        payload = core.manifest()
        self.assertTrue(payload["provider_agnostic"])
        self.assertEqual(payload["scope"], "whole_siot")
        for subsystem in ("canon", "openclaw", "mission_control", "toltecayotl", "publicacion", "ci_cd", "git"):
            self.assertIn(subsystem, payload["subsystems"])

    def test_sanitize_path_redacts_private_prefixes(self) -> None:
        self.assertEqual(core.sanitize_path("00_sistema_tesis/evidencia_privada/x.md"), "[redacted]")
        self.assertEqual(core.sanitize_path("docs/02_arquitectura/x.md"), "docs/02_arquitectura/x.md")

    def test_score_writes_private_and_public_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile_dir = root / "00_sistema_tesis" / "bitacora" / "audit_history"
            profile_dir.mkdir(parents=True)
            (profile_dir / "build_all_profile_latest.json").write_text(
                '{"summary":{"failed":0,"total":4},"slow_stages":[]}',
                encoding="utf-8",
            )
            for rel in (
                "07_scripts/ops/run_tests_smart.py",
                "07_scripts/build_all.py",
                "00_sistema_tesis/bitacora/matriz_trazabilidad.md",
                "00_sistema_tesis/config/security_report.json",
            ):
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("ok", encoding="utf-8")

            with patch.object(core, "ROOT", root), patch.object(core, "PRIVATE_READINESS", root / "00_sistema_tesis/config/harness_readiness.json"), patch.object(core, "PUBLIC_READINESS", root / "06_dashboard/generado/harness_readiness_public.json"), patch.object(core, "PRIVATE_RUNS", root / "00_sistema_tesis/bitacora/audit_history/harness_runs.jsonl"):
                payload = core.score()
                self.assertEqual(payload["status"], "ok")
                self.assertTrue((root / "00_sistema_tesis/config/harness_readiness.json").exists())
                self.assertTrue((root / "06_dashboard/generado/harness_readiness_public.json").exists())


if __name__ == "__main__":
    unittest.main()
