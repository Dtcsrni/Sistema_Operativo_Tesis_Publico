from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))  # subdirectory siblings

from common import ROOT


ALLOWED_SCRIPTS = {
    "07_scripts/ops/publication.py",
    "07_scripts/tesis.py",
    "07_scripts/audit/secret_scanner.py",  # Ignorado por exclusiones listadas como string
    "07_scripts/audit/audit_public_paths.py", # Este propio archivo
    "07_scripts/ops/observability_snapshot.py", # A veces lo lee/escribe en variables locales pero ya corregimos el output principal
    "07_scripts/build_runner/registry.py", # Lo lista como watch file
    "07_scripts/audit/validate_links.py", # Lo lee
    "07_scripts/common.py",
    "07_scripts/audit/guardrails.py",
    "07_scripts/audit/validate_public_text.py",
    "07_scripts/audit/validate_structure.py",
    "07_scripts/ops/build_dashboard.py",
    "07_scripts/ops/build_readme_portada.py",
    "07_scripts/ops/build_wiki.py",
    "07_scripts/ops/sync_public_repo.py",
}

FORBIDDEN_PATTERN = "06_dashboard/publico"


def check_public_paths() -> list[str]:
    scripts_dir = ROOT / "07_scripts"
    errors = []

    for py_file in scripts_dir.rglob("*.py"):
        rel_path = py_file.relative_to(ROOT).as_posix()
        
        # Ignorar archivos permitidos explícitamente y archivos temporales de tests
        if rel_path in ALLOWED_SCRIPTS or "test_" in rel_path:
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            if FORBIDDEN_PATTERN in content:
                # Verificamos si realmente lo está usando para escribir o si es solo lectura,
                # pero por diseño, NADIE debería saber que existe `06_dashboard/publico` excepto publication.py
                lines = content.splitlines()
                for i, line in enumerate(lines, 1):
                    if FORBIDDEN_PATTERN in line and not line.strip().startswith("#"):
                        errors.append(f"{rel_path}:{i}: Uso prohibido de ruta pública directa '{FORBIDDEN_PATTERN}'. Use '06_dashboard/generado' y 'publicacion.yaml' en su lugar.")
        except Exception:
            pass

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Audita el bypass de rutas de publicacion.")
    parser.parse_args()

    print("[PROCESS] Analizando código estático en busca de bypass de rutas públicas...")
    errors = check_public_paths()

    if errors:
        print("[CRITICAL ERROR] Se han detectado referencias directas a '06_dashboard/publico':", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print("\nPOR DISEÑO, solo publication.py puede escribir en la ruta pública.", file=sys.stderr)
        return 1
    
    print("[OK] No se detectó bypass de rutas públicas en el código.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
