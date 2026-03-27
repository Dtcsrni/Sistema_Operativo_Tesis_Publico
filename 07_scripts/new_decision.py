import sys
from pathlib import Path
from datetime import datetime

from common import apply_agent_identity_placeholders
from guardrails import safe_write

def main():
    root = Path(__file__).parent.parent
    decisiones_dir = root / "00_sistema_tesis" / "decisiones"
    template_path = root / "00_sistema_tesis" / "plantillas" / "decision_template.md"
    
    if not template_path.exists():
        print(f"[ERROR] No se encontró la plantilla en {template_path}")
        sys.exit(1)

    existing = list(decisiones_dir.glob("*.md"))
    next_id = len(existing) + 1
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Permitir título desde argumentos
    titulo = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "nueva_decision"
    titulo_slug = titulo.lower().replace(" ", "_")
    
    filename = f"{today}_DEC-{next_id:04d}_{titulo_slug}.md"
    target_path = decisiones_dir / filename
    
    if target_path.exists():
         print(f"[ERROR] Ya existe {filename}")
         sys.exit(1)
         
    content = apply_agent_identity_placeholders(template_path.read_text(encoding='utf-8'))
    content = content.replace("DEC-XXXX", f"DEC-{next_id:04d}")
    content = content.replace("Título corto de la decisión", titulo)
    content = content.replace("AAAA-MM-DD", today)
    
    if not safe_write(target_path, content, force=True):
        sys.exit(1)
    print(f"[OK] Decisión creada: {target_path}")

if __name__ == "__main__":
    main()
