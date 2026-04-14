import re
import sys
from pathlib import Path

def verify_file_hierarchy(file_path):
    content = Path(file_path).read_text(encoding='utf-8')
    lines = content.splitlines()
    errors = []
    
    parent_line_num = -1
    parent_checked = False
    parent_indent = -1
    
    for i, line in enumerate(lines):
        # Detectar un checklist item (Padre)
        match = re.match(r'^(\s*)[-*]\s+\[([\sxX])\]\s+(.*)', line)
        if match:
            indent = len(match.group(1))
            status = match.group(2).lower()
            text = match.group(3)
            
            # Si el indent es igual o menor al padre anterior, el anterior ya terminó su bloque
            if parent_line_num != -1 and indent <= parent_indent:
                parent_line_num = -1
            
            # Si encontramos un [x] que tiene hijos, lo marcamos como padre actual para vigilar sus hijos
            if status == 'x':
                parent_line_num = i + 1
                parent_checked = True
                parent_indent = indent
                parent_text = text
            else:
                # Si es un [ ], y tenemos un padre [x] activo con mayor indentación, esto es un error
                if parent_line_num != -1 and indent > parent_indent:
                    errors.append(f"Línea {i+1}: Sub-tarea '{text.strip()}' pendiente para padre completado '{parent_text.strip()}'")
        
        # Si la línea no es un checklist pero tiene menos indentación que el padre, el padre terminó
        elif parent_line_num != -1 and line.strip() and not line.startswith((' ', '\t')):
            parent_line_num = -1

    return errors

def main():
    root = Path(__file__).resolve().parents[1]
    dirs = ["00_sistema_tesis/decisiones", "00_sistema_tesis/bitacora"]
    
    all_errors = []
    for d in dirs:
        p = root / d
        if not p.exists(): continue
        for f in p.glob("*.md"):
            if f.name in ["log_sesiones_trabajo_registradas.md", "matriz_trazabilidad.md"]:
                continue
            file_errors = verify_file_hierarchy(f)
            if file_errors:
                all_errors.append((f.name, file_errors))
                
    if all_errors:
        print("AUDITORÍA DE JERARQUÍA: FALLIDA")
        for fname, errors in all_errors:
            print(f"\n [!] Archivo: {fname}")
            for err in errors:
                print(f"     - {err}")
        sys.exit(1)
    else:
        print("AUDITORÍA DE JERARQUÍA: EXITOSA (Dependencias Verificadas)")

if __name__ == "__main__":
    main()

