#!/usr/bin/env python3
"""
Test e2e: llamadas a modelos local-first.
Uso: python diag_provider_fallback.py [--mode local-only]

Modos:
  local-only   -> Solo Ollama/local (SIN COSTES) - RECOMENDADO

Ejemplo:
  python diag_provider_fallback.py --mode local-only
    -> Usa Ollama local sin costes
"""
import sys
import argparse
from pathlib import Path

# Agregar runtime al path
sys.path.insert(0, str(Path(__file__).parent.parent / "runtime" / "providers"))

from __init__ import create_local_only


def test_local_only():
    """Prueba SOLO modelos locales (SIN COSTES)."""
    print("\n[TEST] Modo LOCAL-ONLY (sin costes)")
    print("[INFO] Usando Ollama/RKLLM - NINGÚN COSTE EN GCP\n")
    try:
        result = create_local_only(base_url="http://localhost:11434")
        prov = result["provider"]
        provider_name = result["name"]
        
        prompt = "Dame un saludo corto en español."
        resp = prov.send(prompt)
        
        print(f"[OK] Provider usado: {provider_name} (costo=$0)")
        print(f"  Respuesta: {resp['text'][:200]}")
        return True
    except Exception as e:
        print(f"[FAIL] Local-only falló: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test de providers con fallback - Control de Costes")
    parser.add_argument("--mode", choices=["local-only"], default="local-only",
                        help="Qué modo probar")
    args = parser.parse_args()
    
    if args.mode == "local-only":
        success = test_local_only()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
