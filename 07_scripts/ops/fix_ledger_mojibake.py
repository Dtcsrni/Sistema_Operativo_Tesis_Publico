import os
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
FILES_TO_FIX = [
    "00_sistema_tesis/canon/events.jsonl",
    "00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md",
    "00_sistema_tesis/bitacora/indice_fuentes_conversacion.md",
]

def fix_mojibake(text):
    # Common mojibake patterns for UTF-8 interpreted as Latin-1
    replacements = {
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã±": "ñ",
        "Ã": "Á", # Careful with this one, might be prefix
        "Ã‰": "É",
        "Ã": "Í",
        "Ã“": "Ó",
        "Ãš": "Ú",
        "Ã‘": "Ñ",
        "Â¿": "¿",
        "Â¡": "¡",
    }
    
    # Try a more systemic approach first: encode as latin-1 and decode as utf-8
    # This works if the text was correctly saved as UTF-8 but the *content* itself 
    # was already corrupted (double encoded).
    try:
        # We target specific sequences that look like mojibake
        # If we do the whole file, we might break actual UTF-8 that is NOT corrupted.
        fixed = text
        for corrupted, correct in replacements.items():
            fixed = fixed.replace(corrupted, correct)
        return fixed
    except Exception as e:
        print(f"Error during systemic fix: {e}")
        return text

def process_file(rel_path):
    path = ROOT / rel_path
    if not path.exists():
        print(f"Skipping {rel_path}: Not found")
        return

    print(f"Processing {rel_path}...")
    content = path.read_text(encoding="utf-8")
    fixed_content = fix_mojibake(content)
    
    if content != fixed_content:
        # Create backup
        backup_path = path.with_suffix(path.suffix + ".bak")
        path.write_text(content, encoding="utf-8") # Ensure we have current as backup
        os.replace(path, backup_path)
        
        path.write_text(fixed_content, encoding="utf-8")
        print(f"Fixed {rel_path}. Backup created at {backup_path.name}")
    else:
        print(f"No changes needed for {rel_path}")

def fix_transcripts():
    transcripts_dir = ROOT / "00_sistema_tesis/evidencia_privada/conversaciones_codex"
    for transcript in transcripts_dir.rglob("transcripcion.md"):
        rel_path = transcript.relative_to(ROOT)
        process_file(str(rel_path))

if __name__ == "__main__":
    for rel_path in FILES_TO_FIX:
        process_file(rel_path)
    fix_transcripts()
    print("Done.")
