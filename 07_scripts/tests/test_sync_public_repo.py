import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts" / "ops"))

from sync_public_repo import _rewrite_public_operational_files  # noqa: E402


class TestSyncPublicRepo(unittest.TestCase):
    def test_rewrite_public_openclaw_compose_mounts(self):
        text = """services:
  openclaw-sovereign-core:
    volumes:
      -  ruta local no pública
      -  ruta local no pública

volumes:
  siot_canon_data:
    external: true
"""
        rewritten = _rewrite_public_operational_files(text, "docker-compose-openclaw.yml")
        self.assertIn("- ./:/workspace:ro", rewritten)
        self.assertIn("- openclaw_public_home:/home/appuser/.openclaw", rewritten)
        self.assertIn("openclaw_public_home:", rewritten)
        self.assertNotIn("ruta local no pública", rewritten)


if __name__ == "__main__":
    unittest.main()
