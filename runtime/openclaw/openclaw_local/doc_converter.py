from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("openclaw.ingestor")

class DocConverter:
    """
    Orquestador de conversión de documentos a Markdown.
    Prioriza la fidelidad estructural para la economía de tokens.
    """

    def __init__(self, use_plugins: bool = True):
        self.use_plugins = use_plugins
        self._markitdown = None
        self._docling = None
        self._init_engines()

    def _init_engines(self):
        # Intentar inicializar Docling (Primario para PDF y fidelidad estructural)
        try:
            from docling.document_converter import DocumentConverter as DoclingConverter
            self._docling = DoclingConverter()
            logger.info("Docling (IBM) inicializado como motor principal.")
        except ImportError:
            # Docling absent — bajar nivel de alarma a info para reducir ruido en producción.
            logger.info("Docling no disponible. La ingesta de documentos complejos usará fallback de menor fidelidad.")

        # Intentar inicializar MarkItDown (Secundario / Formatos Office)
        try:
            from markitdown import MarkItDown
            self._markitdown = MarkItDown()
            logger.info("MarkItDown inicializado como motor secundario.")
        except ImportError:
            logger.debug("MarkItDown no disponible.")

    def convert(self, path: Path) -> tuple[str, dict[str, Any]]:
        """ 
        Convierte un archivo a Markdown estructurado.
        Prioridad: Docling (Fidelidad) > MarkItDown (Versatilidad) > Fallbacks.
        """
        ext = path.suffix.lower()
        
        # 1. Prioridad Máxima: Docling para PDF y documentos complejos
        if self._docling and ext in {".pdf", ".docx", ".pptx", ".html"}:
            try:
                result = self._docling.convert(str(path))
                # Exportar usando el método oficial de Docling v2
                text = result.document.export_to_markdown()
                cleaned = self._clean_markdown(text)
                return cleaned, {"extractor": "docling_primary", "engine": "docling-v2.x"}
            except Exception as e:
                logger.error(f"Fallo en motor primario Docling para {path.name}: {e}")

        # 2. Secundario: MarkItDown para formatos específicos o si Docling falla
        if self._markitdown:
            # MarkItDown es excelente para Excel y CSV donde Docling puede ser overkill
            # También se usa como fallback seguro para otros formatos
            if ext in {".xlsx", ".csv", ".json"} or (ext in {".pdf", ".docx"} and not self._docling):
                try:
                    result = self._markitdown.convert(str(path))
                    text = result.text_content
                    cleaned = self._clean_markdown(text)
                    return cleaned, {"extractor": "markitdown_secondary", "engine": "markitdown-v0.1"}
                except Exception as e:
                    logger.error(f"Error en MarkItDown para {path.name}: {e}")

        # 3. Fallbacks de emergencia (No cumplen política de alta fidelidad, pero evitan bloqueo)
        if ext == ".pdf":
            logger.info(f"Usando fallback pypdf para {path.name}. Advertencia: posible pérdida de fidelidad estructural.")
            return self._fallback_pdf(path)

        # Fallback genérico
        try:
            return path.read_text(encoding="utf-8", errors="replace"), {"extractor": "raw_read"}
        except Exception as e:
            return "", {"extractor": "error", "error": str(e)}

    def _fallback_pdf(self, path: Path) -> tuple[str, dict[str, Any]]:
        """ Extracción básica de PDF usando pypdf. """
        try:
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ""
                pages.append(text)
            
            combined = "\n\n".join(pages)
            return self._clean_markdown(combined), {"extractor": "pypdf_fallback", "pages": len(reader.pages)}
        except Exception as e:
            logger.error(f"Error en fallback PDF para {path.name}: {e}")
            return "", {"extractor": "pdf_failed", "error": str(e)}

    def _clean_markdown(self, text: str) -> str:
        """ 
        Limpia el Markdown extraído para mejorar la economía de tokens.
        - Remueve espacios excesivos.
        - Intenta normalizar saltos de línea.
        - Elimina artefactos comunes de conversión.
        """
        # Normalizar saltos de línea múltiples
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Eliminar espacios en blanco al final de las líneas
        text = "\n".join(line.rstrip() for line in text.splitlines())
        
        # Remover caracteres de control extraños
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        return text.strip()

# Instancia singleton para uso rápido
converter = DocConverter()
