from __future__ import annotations

from pathlib import Path

from common import ROOT, load_agent_identity, load_yaml_json


SCAN_DIRECTORIES = [
    "07_scripts",
    "00_sistema_tesis/plantillas",
    ".github",
]
SCAN_SUFFIXES = {".py", ".md", ".yaml", ".yml", ".json"}
LEGACY_LITERALS = {
    "Google (DeepMind)",
    "Gemini 1.5 Pro / Advanced Agentic Coding v1.0",
    "Antigravity (Assistant)",
}
IGNORE_PATHS = {
    "07_scripts/verify_no_hardcoded_runtime.py",
}
IGNORE_PREFIXES = (
    "07_scripts/tests/",
)


def forbidden_literals() -> set[str]:
    identity = load_agent_identity()
    tesista = load_yaml_json("00_sistema_tesis/config/tesista.json")
    values = {
        identity["agent_role"],
        identity["provider"],
        identity["model_version"],
        identity["runtime_label"],
        tesista["tesista"]["nombre_completo"],
    }
    return {value for value in values if value} | LEGACY_LITERALS


def find_hardcoded_literals(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    literals = forbidden_literals()

    for relative_dir in SCAN_DIRECTORIES:
        base_dir = root / relative_dir
        if not base_dir.exists():
            continue
        for path in base_dir.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in SCAN_SUFFIXES:
                continue
            rel_path = path.relative_to(root).as_posix()
            if rel_path in IGNORE_PATHS:
                continue
            if any(rel_path.startswith(prefix) for prefix in IGNORE_PREFIXES):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for literal in sorted(literals):
                if literal and literal in text:
                    errors.append(f"Literal hardcodeado detectado en {rel_path}: {literal}")
    return errors


def main() -> int:
    errors = find_hardcoded_literals()
    if errors:
        print("AUDITORÍA NO-HARDCODE: FALLÓ")
        for error in errors:
            print(f"- {error}")
        return 1

    print("AUDITORÍA NO-HARDCODE: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
