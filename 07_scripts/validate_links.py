from __future__ import annotations

import argparse
import posixpath
import re
from html.parser import HTMLParser
from pathlib import Path

from common import ROOT


MARKDOWN_LINK_PATTERN = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")
HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)$")
PLACEHOLDER_PATTERN = re.compile(
    r"\[(?:bitacora_privada|reportes_privados|ruta_local_redactada|identidad_agente_privada|canon_privado|matriz_privada|ledger_privado|indice_fuentes_privado)[^\]]*\]"
)
PRIVATE_TARGET_PATTERNS = (
    "00_sistema_tesis/bitacora/",
    "00_sistema_tesis/reportes_semanales/",
    "00_sistema_tesis/canon/",
)
SKIP_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:", "javascript:")
ABSOLUTE_DRIVE_PATTERN = re.compile(r"^/?[A-Za-z]:/")
SCAN_TARGETS = [
    "README.md",
    "README_INICIO.md",
    "06_dashboard/wiki",
    "06_dashboard/generado",
    "06_dashboard/publico",
]


class LinkHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[tuple[str, int]] = []
        self.ids: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        if "id" in attrs_dict and attrs_dict["id"]:
            self.ids.add(attrs_dict["id"])
        if tag.lower() == "a" and attrs_dict.get("href"):
            self.hrefs.append((attrs_dict["href"] or "", self.getpos()[0]))


def iter_scan_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in SCAN_TARGETS:
        path = root / rel
        if path.is_file():
            files.append(path)
            continue
        if path.is_dir():
            files.extend(sorted(item for item in path.rglob("*") if item.is_file() and item.suffix.lower() in {".md", ".html"}))
    return files


def is_relative_href(href: str) -> bool:
    return bool(href) and not href.startswith("#") and not href.startswith(SKIP_SCHEMES)


def normalize_target(base_file: Path, href: str, root: Path) -> tuple[Path | None, str | None]:
    target, separator, anchor = href.partition("#")
    if not target:
        return base_file, anchor if separator else None
    if ABSOLUTE_DRIVE_PATTERN.match(target):
        normalized = target[1:] if target.startswith("/") else target
        absolute = Path(normalized)
        if absolute.exists():
            return absolute, anchor if separator else None
        normalized_posix = normalized.replace("\\", "/")
        parts = [part for part in Path(normalized_posix).parts if part not in {"/", ""}]
        for index in range(len(parts)):
            candidate = root.joinpath(*parts[index:])
            if candidate.exists():
                return candidate, anchor if separator else None
        return absolute, anchor if separator else None
    base_rel = base_file.relative_to(root).as_posix()
    normalized = posixpath.normpath(posixpath.join(Path(base_rel).parent.as_posix(), target))
    resolved = root / Path(normalized)
    return resolved, anchor if separator else None


def markdown_anchors(text: str) -> set[str]:
    anchors: set[str] = set()
    for raw_line in text.splitlines():
        match = HEADING_PATTERN.match(raw_line.strip())
        if not match:
            continue
        title = match.group(2).strip().lower()
        title = re.sub(r"[`*_~]", "", title)
        title = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
        title = re.sub(r"\s+", "-", title).strip("-")
        if title:
            anchors.add(title)
    return anchors


def html_anchors(text: str) -> tuple[list[tuple[str, int]], set[str]]:
    parser = LinkHTMLParser()
    parser.feed(text)
    return parser.hrefs, parser.ids


def extract_markdown_links(text: str) -> list[tuple[str, int]]:
    links: list[tuple[str, int]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for match in MARKDOWN_LINK_PATTERN.finditer(line):
            links.append((match.group(2).strip(), lineno))
    return links


def collect_document_anchors(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".md":
        return markdown_anchors(text)
    _, ids = html_anchors(text)
    return ids


def validate_links(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    scan_files = iter_scan_files(root)
    anchor_cache: dict[Path, set[str]] = {}

    for path in scan_files:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8")
        markdown_links = extract_markdown_links(text) if path.suffix.lower() == ".md" else []
        html_links, _ = html_anchors(text) if path.suffix.lower() == ".html" else ([], set())
        all_links = markdown_links + html_links

        if rel.startswith("06_dashboard/publico/"):
            for href, lineno in all_links:
                if "[" in href and "]" in href:
                    errors.append(f"{rel}:{lineno} mantiene un href con placeholder redactado: {href}")
                if PLACEHOLDER_PATTERN.search(href):
                    errors.append(f"{rel}:{lineno} mantiene un href con placeholder redactado: {href}")
                if any(token in href for token in PRIVATE_TARGET_PATTERNS):
                    errors.append(f"{rel}:{lineno} mantiene un href hacia superficie privada: {href}")

        for href, lineno in all_links:
            if not href or href.startswith(SKIP_SCHEMES):
                continue
            target_path, anchor = normalize_target(path, href, root)
            if href.startswith("#"):
                target_path = path
                anchor = href[1:]
            if target_path is None:
                continue
            if not target_path.exists():
                errors.append(f"{rel}:{lineno} apunta a un destino inexistente: {href}")
                continue
            if anchor:
                cache_key = target_path.resolve()
                if cache_key not in anchor_cache:
                    anchor_cache[cache_key] = collect_document_anchors(target_path)
                if anchor not in anchor_cache[cache_key]:
                    try:
                        target_rel = target_path.relative_to(root).as_posix()
                    except ValueError:
                        target_rel = target_path.as_posix()
                    errors.append(f"{rel}:{lineno} apunta a ancla inexistente `{anchor}` en {target_rel}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida enlaces relativos y anclas en superficies derivadas.")
    parser.add_argument("--root", default=str(ROOT), help="Raíz del repositorio a validar")
    args = parser.parse_args()
    errors = validate_links(Path(args.root))
    if errors:
        print("VALIDACION ENLACES: ERROR")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VALIDACION ENLACES: OK")
    print("Markdown/HTML, targets relativos y anclas consistentes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
