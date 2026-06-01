import unittest
from pathlib import Path
from runtime.openclaw.openclaw_local.doc_converter import DocConverter

class TestDocIngestion(unittest.TestCase):
    def setUp(self):
        self.converter = DocConverter()

    def test_converter_initialization(self):
        """ Verifica que los motores se inicialicen segÃºn disponibilidad. """
        # Al menos uno deberÃ­a estar disponible si se instalaron
        self.assertTrue(self.converter._markitdown is not None or self.converter._docling is not None)
        print(f"Docling disponible: {self.converter._docling is not None}")
        print(f"MarkItDown disponible: {self.converter._markitdown is not None}")

    def test_markdown_cleaning(self):
        """ Verifica la limpieza de ruido en el Markdown. """
        raw_text = "Texto con muchos saltos\n\n\n\ny espacios al final   \n"
        cleaned = self.converter._clean_markdown(raw_text)
        self.assertEqual(cleaned, "Texto con muchos saltos\n\ny espacios al final")

    def test_supported_types(self):
        """ Verifica que el ingestor acepte los nuevos tipos de archivo. """
        from runtime.openclaw.openclaw_local.toltecayotl_ingestor import SUPPORTED_SOURCE_TYPES
        new_types = {"docx", "xlsx", "pptx", "html", "csv"}
        for t in new_types:
            self.assertIn(t, SUPPORTED_SOURCE_TYPES)

if __name__ == "__main__":
    unittest.main()
