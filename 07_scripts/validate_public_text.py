from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import ROOT
from publication import DEFAULT_PUBLICATION_CONFIG, TEXT_SUFFIXES, load_publication_config


PROHIBITED_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("placeholder redactado", re.compile(r"\[[^\]]*_(?:redactad[ao]|privad[ao]|intern[ao])[^\]]*\]")),
    ("Step ID interno", re.compile(r"VAL-STEP-[A-Za-z0-9_-]+")),
    ("hash sha256 visible", re.compile(r"sha256:", re.IGNORECASE)),
    ("frase privada impropia", re.compile(r"\brepositorio privado\b", re.IGNORECASE)),
    ("frase privada impropia", re.compile(r"\btrazabilidad operativa interna\b", re.IGNORECASE)),
)
REQUIRED_LAST_UPDATE_TARGETS = (
    "README_publico.md",
    "index.md",
    "dashboard/index.html",
    "wiki/index.md",
    "wiki_html/index.html",
)
PUBLIC_SURFACE_PREFIXES = (
    "README.md",
    "06_dashboard/wiki/",
    "06_dashboard/generado/",
    "06_dashboard/publico/",
)


def _is_text_relpath(rel_path: str) -> bool:
    return Path(rel_path).suffix.lower() in TEXT_SUFFIXES


def _requires_last_update(rel_path: str) -> bool:
    normalized = rel_path.replace("\\", "/")
    return any(normalized.endswith(target) for target in REQUIRED_LAST_UPDATE_TARGETS)


def _iter_public_surface_payloads(payloads: dict[str, bytes]) -> list[tuple[str, str]]:
    texts: list[tuple[str, str]] = []
    for rel_path, payload in sorted(payloads.items()):
        normalized = rel_path.replace("\\", "/")
        if not any(normalized == prefix or normalized.startswith(prefix) for prefix in PUBLIC_SURFACE_PREFIXES):
            continue
        if not _is_text_relpath(normalized):
            continue
        texts.append((normalized, payload.decode("utf-8", errors="ignore")))
    return texts


def validate_public_text_payloads(payloads: dict[str, bytes]) -> list[str]:
    errors: list[str] = []
    for rel_path, text in _iter_public_surface_payloads(payloads):
        for label, pattern in PROHIBITED_PATTERNS:
            if pattern.search(text):
                errors.append(f"{rel_path}: contiene {label}.")
        if _requires_last_update(rel_path) and "Última actualización:" not in text:
            errors.append(f"{rel_path}: no declara 'Última actualización:' en la superficie pública.")
    return errors


def validate_public_text(root: Path) -> list[str]:
    publication = load_publication_config(DEFAULT_PUBLICATION_CONFIG)
    output_root = root / publication["salida"]["directorio"]
    if not output_root.exists():
        return [f"No existe la superficie pública: {output_root}"]

    payloads: dict[str, bytes] = {}
    for path in sorted(output_root.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(root).as_posix()
        if not _is_text_relpath(rel_path):
            continue
        payloads[rel_path] = path.read_bytes()

    return validate_public_text_payloads(payloads)


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida calidad editorial de la superficie pública generada.")
    parser.add_argument("--root", default=str(ROOT))
    args = parser.parse_args()

    errors = validate_public_text(Path(args.root).resolve())
    if errors:
        print("VALIDATE-PUBLIC-TEXT: FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print("VALIDATE-PUBLIC-TEXT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
