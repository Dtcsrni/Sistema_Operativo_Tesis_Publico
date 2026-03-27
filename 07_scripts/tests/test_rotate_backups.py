import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from rotate_backups import classify_risk, plan_rotation, read_backups  # noqa: E402


def base_policy() -> dict:
    return {
        "backup_rotation": {
            "enabled": True,
            "retention_days": {"critico": 180, "alto": 90, "operativo": 30},
            "limits": {"max_files": 500, "max_total_size_mb": 1024, "min_protected_days": 7},
            "risk_patterns": {
                "critico": ["00_sistema_tesis_decisiones_"],
                "alto": ["00_sistema_tesis_bitacora_"],
                "operativo": [],
            },
        }
    }


class TestRotateBackups(unittest.TestCase):
    def test_classify_risk(self):
        policy = base_policy()
        self.assertEqual(classify_risk("00_sistema_tesis_decisiones_x", policy), "critico")
        self.assertEqual(classify_risk("00_sistema_tesis_bitacora_x", policy), "alto")
        self.assertEqual(classify_risk("07_scripts_build_all.py", policy), "operativo")

    def test_plan_rotation_deletes_expired_non_protected(self):
        with tempfile.TemporaryDirectory() as tmp:
            backup_dir = Path(tmp)
            old = datetime.now() - timedelta(days=45)
            fresh = datetime.now() - timedelta(days=2)
            old_name = f"07_scripts_build_all.py.{old.strftime('%Y%m%d_%H%M%S')}.bak"
            fresh_name = f"07_scripts_build_all.py.{fresh.strftime('%Y%m%d_%H%M%S')}.bak"
            (backup_dir / old_name).write_text("x", encoding="utf-8")
            (backup_dir / fresh_name).write_text("x", encoding="utf-8")

            import rotate_backups as mod

            prev = mod.BACKUP_DIR
            mod.BACKUP_DIR = backup_dir
            try:
                entries = read_backups(base_policy())
                to_delete, summary = plan_rotation(entries, base_policy())
                deleted = {item.path.name for item in to_delete}
                self.assertIn(old_name, deleted)
                self.assertNotIn(fresh_name, deleted)
                self.assertEqual(summary["to_delete_count"], 1)
            finally:
                mod.BACKUP_DIR = prev


if __name__ == "__main__":
    unittest.main()
