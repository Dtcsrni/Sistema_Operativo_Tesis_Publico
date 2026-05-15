import re
import json
import hashlib

class RelevanceFilter:
    """
    Motor de filtrado de relevancia y anonimización para el Sistema Operativo de Tesis.
    Garantiza la privacidad (OSINT-Safe) y extrae nexos académicos.
    """
    
    def __init__(self):
        # Patrones para OSINT y datos sensibles
        self.sensitive_patterns = [
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IPv4
            r'\b[A-F0-9]{2}(?::[A-F0-9]{2}){5}\b',  # MAC Address
            r'\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b',  # Email
            r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Credit Cards (ejemplo)
            r'C:\\Users\\[a-zA-Z0-9_]+\\',  # Paths de usuario Windows
            r'/home/[a-zA-Z0-9_]+/',        # Paths de usuario Linux
        ]
        
    def anonymize(self, text: str) -> str:
        """Aplica reglas de anonimización al texto."""
        anonymized = text
        for pattern in self.sensitive_patterns:
            anonymized = re.sub(pattern, "[REDACTED]", anonymized, flags=re.IGNORECASE)
        return anonymized

    def extract_academic_nexuses(self, text: str) -> list[str]:
        """
        Extrae conceptos clave que parecen relevantes para la tesis.
        En una implementación real, esto usaría un LLM local.
        Aquí usamos un filtro heurístico básico.
        """
        # Palabras clave de interés para la tesis (ejemplo)
        keywords = ["epistémico", "distribuida", "npu", "soberanía", "trazabilidad", "agéntico", "ontología"]
        nexuses = []
        
        sentences = re.split(r'[.!?\n]', text)
        for sentence in sentences:
            sentence = sentence.strip()
            if any(kw in sentence.lower() for kw in keywords) and len(sentence) > 20:
                nexuses.append(sentence)
                
        return list(set(nexuses)) # Unificar

    def process_session_log(self, raw_log: str) -> dict:
        """Procesa un log completo y devuelve un objeto sanitizado y relevante."""
        clean_text = self.anonymize(raw_log)
        nexuses = self.extract_academic_nexuses(clean_text)
        
        return {
            "sanitized_summary": clean_text[:500] + "..." if len(clean_text) > 500 else clean_text,
            "academic_nexuses": nexuses,
            "integrity_hash": hashlib.sha256(clean_text.encode()).hexdigest()
        }

if __name__ == "__main__":
    # Test rápido
    f = RelevanceFilter()
    sample = "El sistema de trazabilidad epistémica en la IP 192.168.1.50 es robusto. El usuario evega está trabajando en NPU."
    result = f.process_session_log(sample)
    print(json.dumps(result, indent=2, ensure_ascii=False))
