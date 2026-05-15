#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEC_DIR = ROOT / '00_sistema_tesis' / 'decisiones'

FNAME_RE = re.compile(r'(?P<date>\d{4}-\d{2}-\d{2})_DEC-(?P<id>\d{4})_(?P<rest>.+)\.md', re.IGNORECASE)

# collect existing ids
existing = {}
for p in sorted(DEC_DIR.glob('*.md')):
    m = FNAME_RE.match(p.name)
    if not m:
        continue
    existing[m.group('id')] = p

# target files (from audit)
targets = [
    '2026-05-08_DEC-0040_protocolo_evaluacion_pre-ingestion.md',
    '2026-05-08_DEC-0041_motor_de_evaluacion_de_calidad_epistemica.md',
    '2026-05-08_DEC-0042_politicas_de_estandarizacion_y_calidad_agnostica.md',
    '2026-05-13_DEC-0042_integracion_jira_control_misiones.md',
]

for name in targets:
    p = DEC_DIR / name
    if not p.exists():
        print(f"NO EXISTE: {name}")
        continue
    text = p.read_text(encoding='utf-8')
    lines = text.splitlines()
    # ensure header
    if not lines or lines[0].strip() != '<!-- SISTEMA_TESIS:PROTEGIDO -->':
        lines.insert(0, '<!-- SISTEMA_TESIS:PROTEGIDO -->')
        print(f'Insertado header protegido en {name}')
    # ensure GID line
    m = FNAME_RE.match(p.name)
    if m:
        date = m.group('date')
        fid = m.group('id')
        gid_line = f'<!-- GID: DEC-{fid} | {date} | v1 | draft -->'
        if len(lines) > 1 and re.match(r'^<!--\s*GID:', lines[1]):
            lines[1] = gid_line
            print(f'Actualizado GID en {name}')
        else:
            lines.insert(1, gid_line)
            print(f'Insertado GID en {name}')
    # write back
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')

# Resolve collisions: find duplicate ids
ids = {}
for p in sorted(DEC_DIR.glob('*.md')):
    m = FNAME_RE.match(p.name)
    if not m:
        continue
    fid = int(m.group('id'))
    if fid in ids:
        # rename this file to next available id
        new_id = fid + 1
        while f"{new_id:04d}" in ids:
            new_id += 1
        new_name = p.name.replace(f'DEC-{fid:04d}', f'DEC-{new_id:04d}')
        new_path = p.with_name(new_name)
        p.rename(new_path)
        print(f'Renombrado {p.name} -> {new_name} para evitar colisión')
        ids[new_id] = new_path
    else:
        ids[fid] = p

print('Fix decisiones completado')
