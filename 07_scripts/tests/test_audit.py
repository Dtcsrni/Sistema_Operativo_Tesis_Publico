import unittest
import json
import hashlib
from pathlib import Path

class TestAuditSystem(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]
        self.sign_offs_path = self.root / "00_sistema_tesis" / "config" / "sign_offs.json"
        self.journal_path = self.root / "00_sistema_tesis" / "ia_journal.json"

    def test_sign_offs_exist(self):
        self.assertTrue(self.sign_offs_path.exists(), "El archivo sign_offs.json debería existir")

    def test_journal_is_valid_json(self):
        self.assertTrue(self.journal_path.exists())
        with open(self.journal_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            self.assertIn("journal", data)

    def test_sha256_consistency(self):
        # Verificar que si hay firmas, el formato es correcto
        with open(self.sign_offs_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for entry in data.get("sign_offs", []):
                self.assertIn("archivo", entry)
                self.assertIn("hash_verificado", entry)
                self.assertEqual(len(entry["hash_verificado"]), 64, "El hash SHA256 debe tener 64 caracteres")

if __name__ == "__main__":
    unittest.main()
