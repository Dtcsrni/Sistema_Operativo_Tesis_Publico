import os
import re
import sys
from pathlib import Path

# Patrones comunes de secretos (alto impacto y baja tasa de falsos positivos).
PATTERNS = {
    "GitHub PAT (Classic)": r"\bghp_[A-Za-z0-9]{36}\b",
    "GitHub PAT (Fine-grained)": r"\bgithub_pat_[A-Za-z0-9_]{82}\b",
    "GitHub OAuth token": r"\bgho_[A-Za-z0-9]{36}\b",
    "GitHub App token": r"\bghu_[A-Za-z0-9]{36}\b",
    "LLM API key (sk-)": r"\bsk-[A-Za-z0-9]{20,}\b",
    "Google API key": r"\bAIza[0-9A-Za-z\-_]{35}\b",
    "AWS Access Key ID": r"\bAKIA[0-9A-Z]{16}\b",
    "Slack token": r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
    "JWT token": r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]{10,}\.[A-Za-z0-9._-]{10,}\b",
    "Private key block": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
}

EXCLUDE_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", "runtime/models", "runtime/drivers"}
EXCLUDE_FILES = {
    ".env.example",
    "common.py",
    "sign_off.py",
}  # Archivos que suelen mencionar variables/patrones en contexto documental.
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pyc",
    ".exe",
    ".zip",
    ".tar",
    ".gz",
    ".pdf",
    ".rkllm",
    ".so",
    ".sqlite",
    ".db",
    ".whl",
    ".pkl",
    ".map",
}
SAFE_LINE_MARKERS = (
    "example",
    "ejemplo",
    "placeholder",
    "dummy",
    "sample",
    "test_",
    "fake",
    "redacted",
    "<token>",
    "<secret>",
)

def should_ignore_line(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in SAFE_LINE_MARKERS)


def scan():
    root = Path(__file__).resolve().parents[1]
    found_secrets = []

    for path in root.rglob("*"):
        path_posix = path.as_posix()
        if any(exc in path.parts or exc in path_posix for exc in EXCLUDE_DIRS):
            continue
        if path.name in EXCLUDE_FILES or not path.is_file():
            continue
        
        # Saltar archivos binarios y empaquetados.
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue

        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            for name, pattern in PATTERNS.items():
                for match in re.finditer(pattern, content):
                    line_number = content.count("\n", 0, match.start()) + 1
                    line_text = content.splitlines()[line_number - 1] if content.splitlines() else ""
                    if should_ignore_line(line_text):
                        continue
                    found_secrets.append(
                        f"{name} encontrado en: {path.relative_to(root)} (linea {line_number})"
                    )
                    break
        except Exception as e:
            print(f"[WARN] No se pudo escanear {path}: {e}")

    return found_secrets

def main():
    print("[PROCESS] Escaneando secretos en el repositorio...")
    secrets = scan()
    if secrets:
        print("\n[CRITICAL ERROR] Se encontraron potenciales secretos en el código:")
        for s in secrets:
            print(f"  - {s}")
        print("\nPOR SEGURIDAD, EL BUILD SE HA DETENIDO. Limpie los secretos y use variables de entorno (.env)")
        sys.exit(1)
    else:
        print("[OK] No se detectaron secretos evidentes.")

if __name__ == "__main__":
    main()
