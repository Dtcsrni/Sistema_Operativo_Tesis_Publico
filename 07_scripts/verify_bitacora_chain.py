import hashlib
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BITACORA_DIR = ROOT / "00_sistema_tesis" / "bitacora"

def calc_hash(filepath):
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def verify_chain():
    bitacoras = sorted([f for f in BITACORA_DIR.glob("*.md") if "bitacora" in f.name])
    if not bitacoras:
        print("[!] No se encontraron bitácoras para verificar")
        return True

    errors = []
    prev_hash = None
    prev_name = None

    for b in bitacoras:
        content = b.read_text(encoding="utf-8")
        # Regex flexible para encontrar la cadena anterior sin importar negritas o espacios exactos
        match = re.search(r"Cadena de Confianza \(Anterior\).*?sha256/([a-f0-9]+)", content, re.IGNORECASE)
        
        if not match:
            if "2026-03-23" in b.name: # Primera bitácora puede no tener cadena aún o ser INICIO
                prev_hash = calc_hash(b)
                prev_name = b.name
                continue
            errors.append(f"Falta 'Cadena de Confianza' en: {b.name}")
            continue

        declared_prev_hash = match.group(1)
        
        if prev_hash and declared_prev_hash != "INICIO" and declared_prev_hash != prev_hash:
            errors.append(f"Cadena rota en {b.name}: Declara hash de {prev_name} pero no coincide.")
        
        prev_hash = calc_hash(b)
        prev_name = b.name

    if errors:
        print("[FAIL] Cadena de Bitácoras ROTA:")
        for e in errors:
            print(f" - {e}")
        return False

    print("[OK] Cadena de Bitácoras íntegra")
    return True

if __name__ == "__main__":
    if not verify_chain():
        sys.exit(1)
