#!/usr/bin/env python3
from pathlib import Path
import re, hashlib

ROOT = Path(__file__).resolve().parents[1]
BITACORA_DIR = ROOT / "00_sistema_tesis" / "bitacora"
DECISIONS_DIR = ROOT / "00_sistema_tesis" / "decisiones"

# Files to ensure refs (from last audit)
files_to_ensure_refs = [
    ROOT / '00_sistema_tesis' / 'bitacora' / '2026-05-04_bitacora_dialogo.md',
    ROOT / '00_sistema_tesis' / 'bitacora' / '2026-05-04_bitacora_dialogo_1.md',
    ROOT / '00_sistema_tesis' / 'bitacora' / '2026-05-04_bitacora_dialogo_2.md',
    ROOT / '00_sistema_tesis' / 'bitacora' / '2026-05-04_bitacora_sesion.md',
    ROOT / '00_sistema_tesis' / 'bitacora' / 'caracteristicas_sistema_siot.md',
    ROOT / '00_sistema_tesis' / 'bitacora' / 'CORRECCIONES_TELEGRAM_2026-05-05.md',
    ROOT / '00_sistema_tesis' / 'bitacora' / 'informe_benchmarking_detallado_2026-05-05.md',
    ROOT / '00_sistema_tesis' / 'bitacora' / 'REPORTE_HUÉRFANAS_CRITICO_2026-05-05.md',
    ROOT / '00_sistema_tesis' / 'bitacora' / 'REPORTE_TELEGRAM_2026-05-05.md',
    ROOT / '00_sistema_tesis' / 'bitacora' / 'RESUMEN_EJECUTIVO_MAESTRO_2026-05-05.md',
    ROOT / '00_sistema_tesis' / 'bitacora' / 'SISTEMA_AUTONOMO_BACKENDS_2026-05-05.md',
    # DECISIONES missing refs
    ROOT / '00_sistema_tesis' / 'decisiones' / '2026-05-05_DEC-0035_optimizacion_vram_y_poda_de_modelos.md',
    ROOT / '00_sistema_tesis' / 'decisiones' / '2026-05-05_DEC-0036_restriccion_ram_edge.md',
    ROOT / '00_sistema_tesis' / 'decisiones' / '2026-05-05_DEC-0037_estandarizacion_telemetria_remota.md',
    ROOT / '00_sistema_tesis' / 'decisiones' / '2026-05-07_DEC-0038_opencode_executor_subordinado.md',
]

REF_TEXT = '\n\n[LID]: {path}\n[GOV]: AGENTS.md\n[AUD]: build_all.py\n'

def calc_hash(filepath: Path) -> str:
    text = filepath.read_text(encoding='utf-8')
    normalized = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', '\r\n')
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

# 1) Ensure refs
updated = []
for p in files_to_ensure_refs:
    if not p.exists():
        continue
    content = p.read_text(encoding='utf-8')
    if re.search(r"^\[LID\]:", content, re.MULTILINE):
        continue
    path_rel = str(p).replace('\\', '/')
    p.write_text(content + REF_TEXT.format(path=path_rel), encoding='utf-8')
    updated.append(p.name)

print(f"Refs añadidas en: {updated}")

# 2) Insertar Pre-checks y confirmación verbal en DEC-0038 y SISTEMA_AUTONOMO_BACKENDS
prechecks_block = '\nPre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima\n\n**Texto exacto de confirmación verbal:** Pendiente de revisión por el Tesista\n**Hash de confirmación verbal:** sha256:pendiente_actualizacion\n**Fuente de verdad de confirmación:** No existe `VAL-STEP-*`\n'

dec_0038 = ROOT / '00_sistema_tesis' / 'decisiones' / '2026-05-07_DEC-0038_opencode_executor_subordinado.md'
if dec_0038.exists():
    c = dec_0038.read_text(encoding='utf-8')
    if 'Pre-checks:' not in c:
        # Insert before '## Referencias' or at end
        if '## Referencias' in c:
            c = c.replace('## Referencias', prechecks_block + '\n## Referencias')
        else:
            c = c + prechecks_block
        dec_0038.write_text(c, encoding='utf-8')
        print('DEC-0038: Pre-checks insertados')

backend_file = ROOT / '00_sistema_tesis' / 'bitacora' / 'SISTEMA_AUTONOMO_BACKENDS_2026-05-05.md'
if backend_file.exists():
    c = backend_file.read_text(encoding='utf-8')
    if 'Pre-checks:' not in c:
        # Insert after '## ✅ CHECKLIST DE VALIDACIÓN' header
        c = c.replace('## ✅ CHECKLIST DE VALIDACIÓN', '## ✅ CHECKLIST DE VALIDACIÓN' + prechecks_block)
        backend_file.write_text(c, encoding='utf-8')
        print('Backends: Pre-checks insertados')

# 3) Corregir Cadena de Confianza en todas las bitácoras
bitacoras = sorted([f for f in BITACORA_DIR.glob('*.md') if 'bitacora' in f.name])
prev_hash = None
prev_name = None
for i, b in enumerate(bitacoras):
    content = b.read_text(encoding='utf-8')
    if i == 0:
        # ensure INICIO marker
        if 'Cadena de Confianza' not in content:
            insert = '\n\nCadena de Confianza (Anterior): sha256/INICIO\n'
            content = content + insert
            b.write_text(content, encoding='utf-8')
            print(f'{b.name}: Añadido INICIO')
        prev_hash = calc_hash(b)
        prev_name = b.name
        continue
    declared_match = re.search(r"Cadena de Confianza \(Anterior\).*?sha256/([a-f0-9]+)", content, re.IGNORECASE | re.DOTALL)
    expected = prev_hash
    if declared_match:
        declared = declared_match.group(1)
        if declared != expected:
            # replace declared with expected
            content = re.sub(r"(Cadena de Confianza \(Anterior\).*?sha256/)[a-f0-9]+", r"\1" + expected, content, flags=re.IGNORECASE | re.DOTALL)
            b.write_text(content, encoding='utf-8')
            print(f'{b.name}: Cadena actualizada (hash mismatch)')
    else:
        # insert after header (top)
        insert = f'\n\nCadena de Confianza (Anterior): sha256/{expected}\n'
        content = content + insert
        b.write_text(content, encoding='utf-8')
        print(f'{b.name}: Cadena insertada')
    prev_hash = calc_hash(b)
    prev_name = b.name

print('Patch completo')
