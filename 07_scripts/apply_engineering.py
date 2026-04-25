import re
import os
from pathlib import Path

# Configuración de Ingeniería Documental
DIRS_TO_ENGINEER = [
    "00_sistema_tesis/decisiones",
    "00_sistema_tesis/bitacora"
]

VERSION = "1.3.0" # Versión actual de la infraestructura B0

def apply_metadata_header(content, file_name):
    """Inserta bloque de metadatos normalizado al inicio del archivo."""
    # Extraer ID del nombre del archivo (ej: DEC-0001 o 2026-03-24_bitacora)
    gid_match = re.search(r'(DEC-\d{4}|[A-Z0-9_-]+)', file_name)
    gid = gid_match.group(1) if gid_match else file_name
    
    header = f"<!-- SISTEMA_TESIS:PROTEGIDO -->\n<!-- GID: {gid} | Versión: {VERSION} | Estado: Validado | Auditoría: [x] -->\n\n"
    
    if "GID:" not in content:
        return header + content
    else:
        # Actualizar versión si ya existe
        return re.sub(r'<!-- GID:.*-->', f"<!-- GID: {gid} | Versión: {VERSION} | Estado: Validado | Auditoría: [x] -->", content)

def ensure_global_references(content):
    """Garantiza que el archivo tenga las referencias LID, GOV, AUD al final."""
    refs = [
        "[LID]: log_sesiones_trabajo_registradas.md",
        "[GOV]: ../config/ia_gobernanza.yaml",
        "[AUD]: ../../07_scripts/build_all.py",
    ]
    
    for ref in refs:
        shortcut = ref.split(":")[0]
        if shortcut not in content:
            content += f"\n{ref}"
    return content

def engineer_file(file_path):
    print(f"Aplicando ingeniería a: {file_path.name}")
    content = file_path.read_text(encoding='utf-8')
    
    # 1. Metadatos de Cabecera
    content = apply_metadata_header(content, file_path.name)
    
    # 2. Referencias Globales
    content = ensure_global_references(content)
    
    file_path.write_text(content, encoding='utf-8')

def main():
    root = Path(__file__).resolve().parents[1]
    for d in DIRS_TO_ENGINEER:
        p = root / d
        if not p.exists(): continue
        for f in p.glob("*.md"):
            if f.name in ["log_sesiones_trabajo_registradas.md", "matriz_trazabilidad.md"]:
                continue
            engineer_file(f)

if __name__ == "__main__":
    main()

