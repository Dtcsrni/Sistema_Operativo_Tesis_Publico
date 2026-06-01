#!/usr/bin/env python3
"""
smoke_test_openclaw.py -- Valida la "consciencia" y personalidad del Asistente.
"""

import os
import sys
from pathlib import Path

# Añadir el path para importar módulos de openclaw_local
repo_root = Path(__file__).resolve().parents[2]
sys.path.append(str(repo_root))

from runtime.openclaw.openclaw_local.persona import build_system_block
from runtime.openclaw.openclaw_local.toltecayotl_knowledge import search_knowledge

def test_persona():
    print("[TEST] Verificando Perfil Científico...")
    block = build_system_block("research", "high")
    if "asistente científico" in block.lower() and "Erick" in block:
        print("[OK] Identidad y Tono correctos.")
    else:
        print("[FAIL] La identidad no refleja el asistente científico.")
        return False
    return True

def test_knowledge_access():
    print("[TEST] Verificando Acceso a CONTEXT.md (via Toltecayotl)...")
    # Este test asume que ya se corrió ingest_meta_docs.py
    results = search_knowledge(repo_root, "LoRa P2P MQTT")
    if results["results"]:
        print(f"[OK] Se encontraron {len(results['results'])} fragmentos de conocimiento.")
        # Verificar si algún fragmento viene de CONTEXT.md
        if any("CONTEXT.md" in str(r.get("source_path")) for r in results["results"]):
            print("[OK] El sistema reconoce el glosario canónico.")
        else:
            print("[WARN] No se detectó CONTEXT.md en los resultados. ¿Se ejecutó la ingesta?")
    else:
        print("[FAIL] No se encontró conocimiento base.")
        return False
    return True

def main():
    print("=== SMOKE TEST: OPENCLAW SCIENTIFIC ASSISTANT ===\n")
    
    steps = [test_persona, test_knowledge_access]
    success = True
    for step in steps:
        if not step():
            success = False
            break
            
    if success:
        print("\n[SUCCESS] El Asistente Científico está listo para operar.")
    else:
        print("\n[FAIL] Se detectaron problemas en la integración.")
        sys.exit(1)

if __name__ == "__main__":
    main()
