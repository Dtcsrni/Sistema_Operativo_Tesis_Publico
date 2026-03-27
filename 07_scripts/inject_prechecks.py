import os
import re
from pathlib import Path

# Configuración
DIRS_TO_PROCESS = [
    "00_sistema_tesis/decisiones",
    "00_sistema_tesis/bitacora"
]

PRE_CHECKLIST_BLOCK = """  - [ ] **Pre-requisitos Técnicos:**
    - [ ] Integridad SHA-256 verificada.
    - [ ] Alineación con estándares (NIST/UNESCO) confirmada.
    - [ ] Auditoría de inconsistencias (`build_all.py`) exitosa."""
PRECHECK_LINE = "Pre-checks: [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima"

def process_file(file_path):
    content = Path(file_path).read_text(encoding='utf-8')
    
    # 1. LIMPIEZA NUCLEAR: Eliminar bloques y referencias previas
    lines = content.splitlines()
    clean_lines = []
    skip_keywords = [
        "**Pre-requisitos Técnicos**", 
        "Integridad SHA-256 verificada", 
        "Alineación con estándares", 
        "Auditoría de inconsistencias", 
        "Pre-checks: [Integridad]", 
        "[LID]:", "[GOV]:", "[AUD]:"
    ]
    
    for line in lines:
        if not any(kw in line for kw in skip_keywords):
            clean_lines.append(line)
    
    # Eliminar líneas vacías al final que pudieran acumularse
    while clean_lines and not clean_lines[-1].strip():
        clean_lines.pop()
    
    # 2. INYECCIÓN CONTROLADA
    final_lines = []
    for line in clean_lines:
        final_lines.append(line)
        match = re.match(r'^([-*]\s+\[([\sxX])\])', line.strip())
        if match:
            base_match = re.match(r'^(\s*)', line)
            indent = base_match.group(1) if base_match else ""
            status = match.group(2).lower()
            
            sub_indent = indent + "  "
            final_lines.append(f"{sub_indent}- [{status}] {PRECHECK_LINE}")
            
    # 3. Definiciones de Referencia al Final
    base_url = "file:///v:/Sistema_Operativo_Tesis_Posgrado"
    final_lines.extend([
        "",
        f"[LID]: {base_url}/00_sistema_tesis/bitacora/log_conversaciones_ia.md",
        f"[GOV]: {base_url}/00_sistema_tesis/config/ia_gobernanza.yaml",
        f"[AUD]: {base_url}/07_scripts/build_all.py"
    ])
    
    new_content = "\n".join(final_lines) + "\n"
    # Normalizar saltos de línea (un solo salto triple-max)
    new_content = re.sub(r'\n{4,}', '\n\n\n', new_content)
    
    if new_content != content:
        Path(file_path).write_text(new_content, encoding='utf-8')
        return True
    return False

def main():
    root = Path.cwd()
    count = 0
    for d in DIRS_TO_PROCESS:
        p = root / d
        if not p.exists(): continue
        for f in p.glob("*.md"):
            if f.name in ["log_conversaciones_ia.md", "matriz_trazabilidad.md"]:
                continue
            if process_file(f):
                print(f"Inyectado pre-checklist en: {f.name}")
                count += 1
    print(f"Total archivos actualizados: {count}")

if __name__ == "__main__":
    main()
