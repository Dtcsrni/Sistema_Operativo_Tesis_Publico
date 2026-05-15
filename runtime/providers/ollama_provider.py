"""
Adaptador mínimo para Ollama (provider local).
Interfaz: OllamaProvider(base_url, model) -> send(prompt) -> {"text": ..., "raw": ...}
"""
from typing import Dict, Any
import requests


class OllamaProvider:
    def __init__(self, base_url: str = "http://ollama-pc:11434", model: str = "deepseek-r1:7b"):
        self.base_url = base_url.rstrip("/")
        self.model = model
    
    def send(self, prompt: str, max_tokens: int = 512, **kwargs) -> Dict[str, Any]:
        """Envía un prompt a Ollama."""
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("response", "")
            return {"text": text, "raw": data}
        except Exception as e:
            return {"text": "", "raw": e}


if __name__ == "__main__":
    prov = OllamaProvider()
    r = prov.send("Saludo corto en español")
    print(r["text"])
