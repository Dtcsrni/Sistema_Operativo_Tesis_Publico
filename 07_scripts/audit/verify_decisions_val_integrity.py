from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))      # subdirectory siblings

from common import ROOT

DECISIONS_DIR = ROOT / "00_sistema_tesis" / "decisiones"
LEDGER_PATH = ROOT / "00_sistema_tesis" / "bitacora" / "log_sesiones_trabajo_registradas.md"
MATRIX_PATH = ROOT / "00_sistema_tesis" / "bitacora" / "matriz_trazabilidad.md"
EVENTS_PATH = ROOT / "00_sistema_tesis" / "canon" / "events.jsonl"

FILENAME_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})_DEC-(?P<id>\d{4})_.+\.md$",
    re.IGNORECASE,
)
GID_RE = re.compile(
    r"^<!--\s*GID:\s*DEC-(?P<id>\d{4})\s*\|\s*(?P<date>\d{4}-\d{2}-\d{2})\s*\|\s*v(?P<version>[0-9]+(?:\.[0-9]+)?)\s*\|\s*(?P<status>[^>]+?)\s*-->$",
    re.IGNORECASE,
)
HEADING_DEC_RE = re.compile(r"^#\s*DEC-(?P<id>\d{4})\b", re.IGNORECASE)
GENERIC_DEC_REF_RE = re.compile(r"\[DEC-(\d{4})\]")
VAL_STEP_RE = re.compile(r"VAL-STEP-(\d+)")
ENFORCE_HEADERS_FROM = "2026-04-01"


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _collect_decision_ids() -> tuple[dict[str, Path], list[str]]:
    errors: list[str] = []
    seen: dict[str, Path] = {}

    for path in sorted(DECISIONS_DIR.glob("*.md")):
        name_match = FILENAME_RE.match(path.name)
        if not name_match:
            continue

        date_id = name_match.group("date")
        file_id = name_match.group("id")
        text = _read_text(path)
        lines = text.splitlines()

        if file_id in seen:
            errors.append(
                f"DEC-{file_id}: colisión de ID entre {seen[file_id].relative_to(ROOT)} y {path.relative_to(ROOT)}"
            )
        else:
            seen[file_id] = path

        if not lines:
            errors.append(f"{path.relative_to(ROOT)}: archivo vacío")
            continue

        strict_headers = date_id >= ENFORCE_HEADERS_FROM

        first_line = lines[0].strip()
        if strict_headers and first_line != "<!-- SISTEMA_TESIS:PROTEGIDO -->":
            errors.append(
                f"{path.relative_to(ROOT)}: primera línea debe ser '<!-- SISTEMA_TESIS:PROTEGIDO -->'"
            )

        gid_line = lines[1].strip() if len(lines) > 1 else ""
        gid_match = GID_RE.match(gid_line)
        if strict_headers and not gid_match:
            errors.append(
                f"{path.relative_to(ROOT)}: falta GID válido en segunda línea"
            )
        if gid_match:
            gid_id = gid_match.group("id")
            gid_date = gid_match.group("date")
            if gid_id != file_id:
                errors.append(
                    f"{path.relative_to(ROOT)}: ID en GID (DEC-{gid_id}) no coincide con filename (DEC-{file_id})"
                )
            if gid_date != date_id:
                errors.append(
                    f"{path.relative_to(ROOT)}: fecha en GID ({gid_date}) no coincide con filename ({date_id})"
                )

        heading_id = None
        for line in lines:
            heading_match = HEADING_DEC_RE.match(line.strip())
            if heading_match:
                heading_id = heading_match.group("id")
                break
        if heading_id and heading_id != file_id:
            errors.append(
                f"{path.relative_to(ROOT)}: heading DEC-{heading_id} no coincide con filename DEC-{file_id}"
            )

    return seen, errors


def _collect_ledger_val_steps() -> tuple[set[str], list[str]]:
    errors: list[str] = []
    text = _read_text(LEDGER_PATH)
    found = re.findall(r"##\s*\[(VAL-STEP-\d+)\]", text)
    duplicates = {step for step in found if found.count(step) > 1}
    for step in sorted(duplicates):
        errors.append(f"ledger: VAL duplicado {step}")
    return set(found), errors


def _collect_matrix_refs() -> tuple[set[str], set[str], list[str]]:
    errors: list[str] = []
    text = _read_text(MATRIX_PATH)
    matrix_steps = set(re.findall(r"\[(VAL-STEP-\d+)\]", text))
    matrix_decs = {f"DEC-{dec_id}" for dec_id in GENERIC_DEC_REF_RE.findall(text)}

    return matrix_steps, matrix_decs, errors


def _collect_canon_val_steps() -> tuple[set[str], list[str]]:
    errors: list[str] = []
    if not EVENTS_PATH.exists():
        errors.append("canon/events.jsonl: no existe")
        return set(), errors
    text = _read_text(EVENTS_PATH)
    canon_steps = {f"VAL-STEP-{n}" for n in VAL_STEP_RE.findall(text)}
    return canon_steps, errors


def verify_decisions_val_integrity() -> list[str]:
    errors: list[str] = []

    decision_ids, decision_errors = _collect_decision_ids()
    errors.extend(decision_errors)

    ledger_steps, ledger_errors = _collect_ledger_val_steps()
    errors.extend(ledger_errors)

    matrix_steps, matrix_decs, matrix_errors = _collect_matrix_refs()
    errors.extend(matrix_errors)

    canon_steps, canon_errors = _collect_canon_val_steps()
    errors.extend(canon_errors)

    valid_dec_refs = {f"DEC-{num}" for num in decision_ids.keys()}
    for dec_ref in sorted(matrix_decs):
        if dec_ref not in valid_dec_refs and dec_ref != "DEC-0014":
            errors.append(f"matriz_trazabilidad.md: referencia DEC inexistente {dec_ref}")

    missing_in_ledger = sorted(matrix_steps - ledger_steps)
    for step in missing_in_ledger:
        errors.append(f"matriz_trazabilidad.md: {step} no existe en ledger")

    missing_in_matrix = sorted(ledger_steps - matrix_steps)
    for step in missing_in_matrix:
        errors.append(f"ledger: {step} no existe en matriz")

    missing_in_canon = sorted(ledger_steps - canon_steps)
    for step in missing_in_canon:
        errors.append(f"ledger: {step} no existe en canon/events.jsonl")

    return errors


def main() -> int:
    errors = verify_decisions_val_integrity()
    if errors:
        print("DECISIONES_VAL_INTEGRITY: FAIL")
        for err in errors:
            print(f"- {err}")
        return 1
    print("DECISIONES_VAL_INTEGRITY: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
