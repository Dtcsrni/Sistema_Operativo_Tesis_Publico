import sys
import re
import subprocess
from pathlib import Path
from datetime import datetime

# Importar utilitarios de common si es posible
try:
    from common import ROOT, load_yaml_json
    from canon import projection_paths
except ImportError:
    ROOT = Path(__file__).resolve().parents[1]
    def projection_paths(events=None):  # type: ignore
        return []

def get_git_signature(file_path):
    """Verifica si el archivo tiene una firma GPG válida en el último commit."""
    try:
        # %G? devuelve 'G' para buena, 'B' para mala, 'U' para desconocida, 'N' para ninguna
        result = subprocess.check_output(
            ["git", "log", "-1", "--format=%G?", str(file_path)],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        return result == 'G'
    except Exception:
        return False

def check_structure_integrity():
    """Ejecuta el validador de estructura y retorna True si pasa."""
    try:
        result = subprocess.run(
            [sys.executable, "07_scripts/validate_structure.py"],
            cwd=ROOT,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def check_md_format():
    """Ejecuta el validador de formato MD y retorna True si pasa."""
    try:
        result = subprocess.run(
            [sys.executable, "07_scripts/validate_md_format.py"],
            cwd=ROOT,
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception:
        return False

def sync_file(file_path):
    """Escanea y actualiza las casillas de verificación según evidencia real."""
    content = file_path.read_text(encoding='utf-8')
    lines = content.splitlines()
    new_lines = []
    changed = False

    # Evidencia persistente para la sesión (caché de validaciones globales)
    integrity_ok = None
    format_ok = None

    for line in lines:
        new_line = line
        
        # 1. Firma GPG
        if "Firma digital GPG" in line and "[ ]" in line:
            if get_git_signature(file_path):
                new_line = line.replace("[ ]", "[x]")
                changed = True
        
        # 2. Integridad de Estructura
        if "Validación de integridad estructural" in line and "[ ]" in line:
            if integrity_ok is None: integrity_ok = check_structure_integrity()
            if integrity_ok:
                new_line = line.replace("[ ]", "[x]")
                changed = True
        
        # 3. Consistencia de Auditoría
        if "Consistencia en auditorías automáticas" in line and "[ ]" in line:
            if format_ok is None: format_ok = check_md_format()
            if format_ok:
                new_line = line.replace("[ ]", "[x]")
                changed = True

        # 4. Validación Operativa (Presencia de carpetas/archivos clave)
        if "Validación operativa de la infraestructura" in line and "[ ]" in line:
            # Condición simple: existen las rutas canónicas básicas
            if (ROOT / "00_sistema_tesis").exists() and (ROOT / "01_planeacion").exists():
                new_line = line.replace("[ ]", "[x]")
                changed = True

        new_lines.append(new_line)

    if changed:
        file_path.write_text("\n".join(new_lines), encoding='utf-8')
        return True
    return False

def main():
    dec_dir = ROOT / "00_sistema_tesis" / "decisiones"
    log_dir = ROOT / "00_sistema_tesis" / "bitacora"
    projected = set(projection_paths())
    
    count = 0
    
    print("Sincronizando evidencia técnica...")
    
    for dec in dec_dir.glob("*.md"):
        if sync_file(dec):
            print(f"[SYNC] {dec.name} actualizado con evidencia real.")
            count += 1
            
    for log in log_dir.glob("*.md"):
        rel_path = str(log.relative_to(ROOT)).replace("\\", "/")
        if rel_path in projected:
            continue
        if sync_file(log):
            print(f"[SYNC] {log.name} actualizado con evidencia real.")
            count += 1
            
    print(f"Sincronización finalizada. Archivos actualizados: {count}")

if __name__ == "__main__":
    main()
