import sys
import re
from pathlib import Path

def get_h2_headers(template_text):
    return re.findall(r'^## (.*)$', template_text, re.MULTILINE)

def validate_file(file_path, required_headers, required_patterns=None):
    content = file_path.read_text(encoding='utf-8')
    found_headers = get_h2_headers(content)
    
    errors = []
    missing_headers = [h for h in required_headers if h not in found_headers]
    if missing_headers:
        errors.append(f"Faltan encabezados H2: {', '.join(missing_headers)}")
    
    if required_patterns:
        for pattern, label in required_patterns.items():
            if not re.search(pattern, content):
                errors.append(f"Falta campo obligatorio: {label}")
                
    return errors

def main():
    root = Path(__file__).parent.parent
    templates_dir = root / "00_sistema_tesis" / "plantillas"
    decisiones_dir = root / "00_sistema_tesis" / "decisiones"
    bitacora_dir = root / "00_sistema_tesis" / "bitacora"
    
    dec_template = templates_dir / "decision_template.md"
    log_template = templates_dir / "bitacora_template.md"
    
    all_errors = []
    
    # Patrones específicos para cumplimiento estricto
    dec_patterns = {
        r"## Criterio de Aceptación Humana": "Sección: Criterio de Aceptación Humana",
        r"## Trazabilidad de IA": "Sección: Trazabilidad de IA",
        r"\*\*Agente/Rol:\*\*": "Campo: Agente/Rol en Trazabilidad de IA",
        r"\*\*Soporte:\*\*": "Campo: Soporte en Criterio de Aceptación Humana",
        r"\*\*Modo:\*\*": "Campo: Modo en Criterio de Aceptación Humana"
    }
    
    log_patterns = {
        r"\*\*Prompts Asociados:\*\*": "Campo: Prompts Asociados en Uso de IA",
        r"\*\*Soporte:\*\*": "Campo: Soporte en Criterio de Aceptación Humana",
        r"\*\*Modo:\*\*": "Campo: Modo en Criterio de Aceptación Humana",
        r"\*\*Pregunta Crítica de Validación:\*\*": "Campo: Pregunta Crítica en Uso de IA"
    }

    if dec_template.exists():
        req_dec_headers = get_h2_headers(dec_template.read_text(encoding='utf-8'))
        for dec_file in decisiones_dir.glob("*.md"):
            errors = validate_file(dec_file, req_dec_headers, dec_patterns)
            if errors:
                all_errors.append(f"[DECISION] {dec_file.name}:\n  - " + "\n  - ".join(errors))
                
    if log_template.exists():
        req_log_headers = get_h2_headers(log_template.read_text(encoding='utf-8'))
        for log_file in bitacora_dir.glob("*.md"):
            errors = validate_file(log_file, req_log_headers, log_patterns)
            if errors:
                all_errors.append(f"[BITACORA] {log_file.name}:\n  - " + "\n  - ".join(errors))

    if all_errors:
        print("AUDITORÍA DE FORMATO ESTRICTO: FALLÓ")
        for err in all_errors:
            print(f"- {err}")
    else:
        print("AUDITORÍA DE FORMATO ESTRICTO: OK")

if __name__ == "__main__":
    main()
