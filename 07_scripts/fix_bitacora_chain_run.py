#!/usr/bin/env python3
from pathlib import Path
import re, hashlib

ROOT = Path(__file__).resolve().parents[1]
BITACORA_DIR = ROOT / "00_sistema_tesis" / "bitacora"

def calc_hash(filepath: Path) -> str:
    text = filepath.read_text(encoding='utf-8')
    normalized = text.replace('\r\n','\n').replace('\r','\n').replace('\n','\r\n')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

bitacoras = sorted([f for f in BITACORA_DIR.glob('*.md') if 'bitacora' in f.name])
prev_hash = None
for i, b in enumerate(bitacoras):
    content = b.read_text(encoding='utf-8')
    if i == 0:
        if 'Cadena de Confianza' not in content:
            content = content + '\n\nCadena de Confianza (Anterior): sha256/INICIO\n'
            b.write_text(content, encoding='utf-8')
            print(f'{b.name}: Añadido INICIO')
        prev_hash = calc_hash(b)
        continue
    expected = prev_hash
    # look for pattern
    m = re.search(r"Cadena de Confianza \(Anterior\).*?sha256/([a-f0-9]+)", content, re.IGNORECASE | re.DOTALL)
    if m:
        declared = m.group(1)
        if declared != expected:
            # replace whole sha segment
            content_new = re.sub(r"(Cadena de Confianza \(Anterior\).*?sha256/)[a-f0-9]+", lambda mo: mo.group(1)+expected, content, flags=re.IGNORECASE | re.DOTALL)
            b.write_text(content_new, encoding='utf-8')
            print(f'{b.name}: Hash actualizado (antes {declared[:8]}..., ahora {expected[:8]}...)')
    else:
        content = content + f"\n\nCadena de Confianza (Anterior): sha256/{expected}\n"
        b.write_text(content, encoding='utf-8')
        print(f'{b.name}: Cadena insertada (sha256/{expected[:8]}...)')
    prev_hash = calc_hash(b)

print('Cadena de bitácoras corregida.')
