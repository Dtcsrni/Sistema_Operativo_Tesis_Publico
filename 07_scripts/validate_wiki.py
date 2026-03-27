from __future__ import annotations

import json
from pathlib import Path

from build_wiki import REQUIRED_PAGE_FIELDS, SECTION_IDS
from common import ROOT


def load_repo_json(root: Path, relative_path: str) -> dict:
    path = root / relative_path
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_wiki(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    wiki = load_repo_json(root, "00_sistema_tesis/config/wiki.yaml")
    markdown_dir = root / wiki["salida"]["markdown_dir"]
    html_dir = root / wiki["salida"]["html_dir"]
    manifest_path = root / wiki["salida"]["manifest"]

    expected_sections = [section["id"] for section in wiki["secciones"]]
    missing_required = sorted(SECTION_IDS - set(expected_sections))
    for section_id in missing_required:
        errors.append(f"Falta la sección requerida en wiki.yaml: {section_id}")

    if wiki["politica"]["editable_directamente"] is not False:
        errors.append("wiki.yaml debe indicar que la wiki no es editable directamente")

    if not markdown_dir.exists():
        errors.append(f"No existe la salida Markdown de wiki: {markdown_dir}")
    if not html_dir.exists():
        errors.append(f"No existe la salida HTML de wiki: {html_dir}")
    if not manifest_path.exists():
        errors.append(f"No existe el manifiesto de wiki: {manifest_path}")

    manifest_pages: set[str] = set()
    expected_pages = {"index"} | set(expected_sections)
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest_pages = set(manifest.get("pages", []))
        if manifest_pages != expected_pages:
            errors.append("El manifiesto de wiki no enumera exactamente las páginas esperadas")

    for section in wiki["secciones"]:
        page_id = section["id"]
        markdown_path = markdown_dir / f"{page_id}.md"
        html_path = html_dir / f"{page_id}.html"
        if not markdown_path.exists():
            errors.append(f"Falta la página Markdown declarada: {markdown_path}")
            continue
        if not html_path.exists():
            errors.append(f"Falta la página HTML declarada: {html_path}")

        content = markdown_path.read_text(encoding="utf-8")
        for field in REQUIRED_PAGE_FIELDS:
            if field not in content:
                errors.append(f"La página {markdown_path.name} no contiene el campo requerido: {field}")

        for source in section["fuentes"]:
            if not (root / source).exists():
                errors.append(f"La página {markdown_path.name} referencia una fuente inexistente: {source}")
            if f"`{source}`" not in content:
                errors.append(f"La página {markdown_path.name} no lista explícitamente su fuente canónica: {source}")

        if page_id in {"experimentos", "implementacion", "tesis"}:
            source_dir = root / section["fuentes"][0]
            non_keep_files = [path for path in source_dir.rglob("*") if path.is_file() and path.name != ".gitkeep"]
            if not non_keep_files and "Sin contenido operativo aún" not in content:
                errors.append(f"La página {markdown_path.name} no refleja que su directorio sigue vacío")

    index_path = markdown_dir / "index.md"
    if not index_path.exists():
        errors.append("Falta la página índice de la wiki")

    return errors


def main() -> int:
    errors = validate_wiki()
    if errors:
        print("VALIDACION WIKI: ERROR")
        for error in errors:
            print(f"- {error}")
        return 1

    print("VALIDACION WIKI: OK")
    print("Páginas, fuentes, manifiesto y cobertura vacía consistentes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
