import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

from common import apply_agent_identity_placeholders, load_agent_identity  # noqa: E402
from verify_no_hardcoded_runtime import find_hardcoded_literals  # noqa: E402


class TestRuntimeIdentity(unittest.TestCase):
    def test_agent_identity_has_required_fields(self):
        identity = load_agent_identity()
        self.assertEqual({"agent_role", "provider", "model_version", "runtime_label"}, set(identity.keys()))

    def test_placeholders_are_replaced_from_config(self):
        rendered = apply_agent_identity_placeholders(
            "[AGENTE_ROL_IA] | [PROVEEDOR_IA] | [MODELO_VERSION_IA] | [RUNTIME_IA]"
        )
        self.assertNotIn("[AGENTE_ROL_IA]", rendered)
        self.assertIn("OpenAI", rendered)

    def test_scanned_paths_have_no_hardcoded_runtime_literals(self):
        self.assertEqual([], find_hardcoded_literals())


if __name__ == "__main__":
    unittest.main()
