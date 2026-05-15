#!/usr/bin/env python3
"""
Test e2e: Llamadas a modelos con fallback automático.
Uso: python test_provider_fallback.py [--mode local-only|hybrid|gemini]

Modos:
  local-only   -> Solo Ollama/local (SIN COSTES) - RECOMENDADO
  hybrid       -> Ollama primero, Gemini si falla (opcional coste)
  gemini       -> Solo Gemini (GENERA COSTES)

Ejemplo:
  python test_provider_fallback.py --mode local-only
    -> Usa Ollama local sin costes
"""
import sys
import argparse
from pathlib import Path

# Agregar runtime al path
sys.path.insert(0, str(Path(__file__).parent.parent / "runtime" / "providers"))

from __init__ import get_provider, create_with_fallback, create_local_only


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


def test_hybrid():
    """Prueba fallback: ollama (sin coste) → gemini (con coste si falla)."""
    print("\n[TEST] Modo HYBRID: Ollama → Gemini")
    print("[WARN] Si Ollama falla, usará Gemini (GENERA COSTES)\n")
    try:
        result = create_with_fallback(
            primary="ollama",
            fallback="gemini",
            base_url="http://localhost:11434",
            project="project-d72bb17e-5918-431c-ba5"
        )
        prov = result["provider"]
        provider_name = result["name"]
        fallback_used = result["fallback"]
        
        cost_notice = " (COSTE)" if fallback_used else " (sin coste)"
        prompt = "Dame un saludo corto."
        resp = prov.send(prompt)
        
        print(f"[OK] Provider usado: {provider_name}{cost_notice}")
        print(f"  Respuesta: {resp['text'][:200]}")
        return True
    except Exception as e:
        print(f"[FAIL] Hybrid falló: {e}")
        return False


def test_gemini_only():
    """Prueba SOLO Gemini (GENERA COSTES)."""
    print("\n[TEST] Modo GEMINI DIRECTO")
    print("[ALERT] MODO DE COSTE: cada token generado cuesta dinero\n")
    try:
        prov = get_provider("gemini", project="project-d72bb17e-5918-431c-ba5")
        prompt = "Dame un saludo corto."
        resp = prov.send(prompt)
        
        print(f"[OK] Respuesta de Gemini (COSTE APLICADO):")
        print(f"  {resp['text'][:200]}")
        return True
    except Exception as e:
        print(f"[FAIL] Gemini falló: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Test de providers con fallback - Control de Costes")
    parser.add_argument("--mode", choices=["local-only", "hybrid", "gemini"], default="local-only",
                        help="Qué modo probar")
    args = parser.parse_args()
    
    if args.mode == "local-only":
        success = test_local_only()
    elif args.mode == "hybrid":
        success = test_hybrid()
    elif args.mode == "gemini":
        success = test_gemini_only()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
