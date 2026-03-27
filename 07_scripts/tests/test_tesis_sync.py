import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from tesis import classify_patches_by_step, classify_sync_paths, parse_porcelain_paths  # noqa: E402


class TestTesisSync(unittest.TestCase):
    def test_parse_porcelain_paths_handles_rename(self):
        porcelain = " M 00_sistema_tesis/canon/events.jsonl\nR  old.md -> new.md\n?? 06_dashboard/wiki/a.md\n"
        paths = parse_porcelain_paths(porcelain)
        self.assertEqual(
            paths,
            [
                "00_sistema_tesis/canon/events.jsonl",
                "new.md",
                "06_dashboard/wiki/a.md",
            ],
        )

    def test_classify_paths_keeps_primary_projection_in_operational_bundle(self):
        paths = [
            "00_sistema_tesis/canon/events.jsonl",
            "00_sistema_tesis/bitacora/log_conversaciones_ia.md",
            "06_dashboard/wiki/index.md",
            "06_dashboard/generado/wiki_manifest.json",
            "06_dashboard/publico/index.md",
            "00_sistema_tesis/config/token_usage_snapshot.json",
            "README.md",
        ]
        operational, secondary = classify_sync_paths(
            paths,
            ["00_sistema_tesis/bitacora/log_conversaciones_ia.md"],
        )
        self.assertEqual(
            operational,
            [
                "00_sistema_tesis/canon/events.jsonl",
                "00_sistema_tesis/bitacora/log_conversaciones_ia.md",
            ],
        )
        self.assertEqual(
            secondary,
            [
                "06_dashboard/wiki/index.md",
                "06_dashboard/generado/wiki_manifest.json",
                "06_dashboard/publico/index.md",
                "00_sistema_tesis/config/token_usage_snapshot.json",
                "README.md",
            ],
        )

    def test_classify_patches_by_step_groups_paths_and_fallbacks_to_latest(self):
        patches = {
            "00_sistema_tesis/decisiones/2026-03-26_DEC-0017_operacion_humana_dual_y_superficies_privada_publica.md": """
diff --git a/a b/b
+++ b/00_sistema_tesis/decisiones/2026-03-26_DEC-0017_operacion_humana_dual_y_superficies_privada_publica.md
@@ -1 +1 @@
+  - **Soporte:** [VAL-STEP-470]
""",
            "07_scripts/canon.py": """
diff --git a/a b/b
+++ b/07_scripts/canon.py
@@ -1 +1 @@
+def append_conversation_source():
""",
            "00_sistema_tesis/bitacora/log_conversaciones_ia.md": """
diff --git a/a b/b
+++ b/00_sistema_tesis/bitacora/log_conversaciones_ia.md
@@ -1 +1 @@
+## [VAL-STEP-500]
""",
            "06_dashboard/publico/index.md": """
diff --git a/a b/b
+++ b/06_dashboard/publico/index.md
@@ -1 +1 @@
+bundle
""",
        }
        bundles, derived, unassigned = classify_patches_by_step(
            patches,
            ["00_sistema_tesis/bitacora/log_conversaciones_ia.md"],
            {"VAL-STEP-470", "VAL-STEP-500"},
        )
        self.assertEqual(unassigned, [])
        self.assertEqual([bundle["step_id"] for bundle in bundles], ["VAL-STEP-470", "VAL-STEP-500"])
        self.assertIn("07_scripts/canon.py", bundles[1]["auto_assigned_paths"])
        self.assertEqual(derived, ["06_dashboard/publico/index.md"])


if __name__ == "__main__":
    unittest.main()
