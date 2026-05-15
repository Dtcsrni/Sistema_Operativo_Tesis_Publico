from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PENDIENTES_DIR = ROOT / "00_sistema_tesis" / "pendientes"

PRD_REQUIRED_FRONTMATTER = {"title", "date", "category", "status", "reporter"}
SPEC_REQUIRED_FRONTMATTER = {"title", "date", "category", "status", "owner", "decisions", "step_id"}
ALLOWED_STATUSES = {
    "needs-triage",
    "needs-info",
    "ready-for-agent",
    "ready-for-human",
    "implementation-ready",
    "wontfix",
    "open",
    "closed",
}
PRD_REQUIRED_SECTIONS = (
    "Problem Statement",
    "Solution",
    "User Stories",
    "Implementation Decisions",
    "Testing Decisions",
    "Out of Scope",
)
SPEC_REQUIRED_SECTIONS = (
    "Objetivo",
    "Alcance",
    "Rutas Afectadas",
    "Gates Publicos",
    "Pruebas y Aceptacion",
    "Rollback",
    "Cierre de Trazabilidad",
    "FRE",
    "ESE",
)


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    payload: dict[str, str] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        payload[key.strip()] = value.strip().strip('"')
    return payload, body


def spec_kind(path: Path, frontmatter: dict[str, str], body: str) -> str:
    title = frontmatter.get("title", "")
    if path.name.startswith("PRD-") or title.startswith("PRD:") or re.search(r"^# PRD:", body, re.MULTILINE):
        return "prd"
    if path.name.startswith("SPEC-") or title.startswith("SPEC:") or re.search(r"^# SPEC:", body, re.MULTILINE):
        return "spec"
    return ""


def is_sdd_spec(path: Path, frontmatter: dict[str, str], body: str) -> bool:
    return bool(spec_kind(path, frontmatter, body))


def validate_sdd_spec(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    frontmatter, body = parse_frontmatter(text)
    errors: list[str] = []

    kind = spec_kind(path, frontmatter, body)
    required_frontmatter = SPEC_REQUIRED_FRONTMATTER if kind == "spec" else PRD_REQUIRED_FRONTMATTER
    required_sections = SPEC_REQUIRED_SECTIONS if kind == "spec" else PRD_REQUIRED_SECTIONS

    missing = sorted(required_frontmatter - set(frontmatter))
    if missing:
        errors.append(f"frontmatter incompleto: {', '.join(missing)}")

    status = frontmatter.get("status", "")
    if status and status not in ALLOWED_STATUSES:
        errors.append(f"status invalido: {status}")

    for section in required_sections:
        if f"## {section}" not in body:
            errors.append(f"falta seccion SDD: {section}")

    if kind == "spec" and "step_id: \"PENDIENTE\"" not in text and "step_id: PENDIENTE" not in text:
        errors.append("spec debe dejar step_id como PENDIENTE hasta validacion humana explicita")

    if re.search(r"(?im)^\s*-\s*\[x\]", body):
        errors.append("una spec SDD no debe marcar tareas como completadas; requiere validacion humana externa")

    if "VAL-STEP-" in body and status in {"needs-triage", "needs-info"}:
        errors.append("spec sin triage no debe declarar cierre o validacion VAL-STEP como propia")

    return errors


def validate_specs(root: Path = ROOT) -> dict[str, Any]:
    pendientes = root / "00_sistema_tesis" / "pendientes"
    checked: list[str] = []
    errors: list[str] = []
    for path in sorted(pendientes.glob("*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        frontmatter, body = parse_frontmatter(text)
        if not is_sdd_spec(path, frontmatter, body):
            continue
        checked.append(str(path.relative_to(root)))
        for error in validate_sdd_spec(path):
            errors.append(f"{path.relative_to(root)}: {error}")
    return {"checked": checked, "errors": errors}


def main() -> int:
    parser = argparse.ArgumentParser(description="Valida specs SDD en el tracker local de pendientes.")
    parser.add_argument("--json", action="store_true", help="Imprime JSON estructurado.")
    args = parser.parse_args()
    result = validate_specs(ROOT)
    if args.json:
        import json

        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif result["errors"]:
        print("VALIDACION SDD: FAIL")
        for error in result["errors"]:
            print(f"- {error}")
    else:
        print(f"VALIDACION SDD: OK ({len(result['checked'])} spec(s))")
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
