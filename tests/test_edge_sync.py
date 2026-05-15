import unittest
import os
import shutil
from pathlib import Path
from runtime.edge_sync.sync_manager import SyncManager

class TestSyncManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("test_buffer")
        self.test_dir.mkdir(exist_ok=True)
        os.environ["BUFFER_DIR"] = str(self.test_dir)
        self.sync = SyncManager()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_get_pending_files(self):
        # Crear archivo de prueba
        test_file = self.test_dir / "test.jsonl"
        test_file.write_text('{"test": 1}')
        
        files = self.sync.get_pending_files()
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "test.jsonl")

    def test_sync_fail_no_hub(self):
        test_file = self.test_dir / "test.jsonl"
        test_file.write_text('{"test": 1}')
        
        # Debe fallar pero no crashear
        result = self.sync.sync_file(test_file)
        self.assertFalse(result)
        self.assertTrue(test_file.exists()) # Sigue ahí porque falló

if __name__ == "__main__":
    unittest.main()
