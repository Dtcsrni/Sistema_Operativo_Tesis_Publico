import json
import sys
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

import guardrails  # noqa: E402


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@contextmanager
def patched_root(repo: Path):
    previous_root = guardrails.ROOT
    previous_manifest = guardrails.MANIFEST_PATH
    guardrails.ROOT = repo
    guardrails.MANIFEST_PATH = repo / "00_sistema_tesis" / "config" / "integrity_manifest.json"
    try:
        yield
    finally:
        guardrails.ROOT = previous_root
        guardrails.MANIFEST_PATH = previous_manifest


class TestGuardrailsIncremental(unittest.TestCase):
    def test_update_manifest_for_path_adds_and_updates_protected_entry(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            target = repo / "00_sistema_tesis" / "config" / "agent_identity.json"
            write_json(target, {"agent_identity": {"provider": "OpenAI"}})
            with patched_root(repo):
                guardrails.update_manifest()
                manifest_before = json.loads(guardrails.MANIFEST_PATH.read_text(encoding="utf-8"))
                original_hash = manifest_before["00_sistema_tesis/config/agent_identity.json"]

                write_json(target, {"agent_identity": {"provider": "OpenAI", "model": "GPT-5"}})
                guardrails.update_manifest_for_path(target)
                manifest_after = json.loads(guardrails.MANIFEST_PATH.read_text(encoding="utf-8"))

            self.assertIn("00_sistema_tesis/config/agent_identity.json", manifest_after)
            self.assertNotEqual(original_hash, manifest_after["00_sistema_tesis/config/agent_identity.json"])

    def test_update_manifest_for_path_removes_entry_when_file_leaves_protected_set(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            target = repo / "docs" / "protegido.md"
            write_text(target, "<!-- SISTEMA_TESIS:PROTEGIDO -->\ntexto\n")
            with patched_root(repo):
                guardrails.update_manifest()
                manifest_before = json.loads(guardrails.MANIFEST_PATH.read_text(encoding="utf-8"))
                self.assertIn("docs/protegido.md", manifest_before)

                write_text(target, "texto sin marcador\n")
                guardrails.update_manifest_for_path(target)
                manifest_after = json.loads(guardrails.MANIFEST_PATH.read_text(encoding="utf-8"))

            self.assertNotIn("docs/protegido.md", manifest_after)

    def test_safe_write_uses_incremental_manifest_update(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            target = repo / "00_sistema_tesis" / "config" / "ia_gobernanza.yaml"
            write_text(target, "clave: uno\n")
            with patched_root(repo):
                guardrails.update_manifest()
                with mock.patch.object(guardrails, "update_manifest_for_path") as incremental, mock.patch.object(
                    guardrails, "update_manifest"
                ) as full:
                    result = guardrails.safe_write(target, "clave: dos\n", force=True)

            self.assertTrue(result)
            incremental.assert_called_once()
            full.assert_not_called()


if __name__ == "__main__":
    unittest.main()
