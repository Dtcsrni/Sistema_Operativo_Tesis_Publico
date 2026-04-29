from __future__ import annotations

import re
import sys
from pathlib import Path

from common import ROOT, load_yaml_json


LEDGER_PATH = ROOT / "00_sistema_tesis" / "bitacora" / "log_sesiones_trabajo_registradas.md"
MATRIX_PATH = ROOT / "00_sistema_tesis" / "bitacora" / "matriz_trazabilidad.md"
DECISIONS_DIR = ROOT / "00_sistema_tesis" / "decisiones"
POLICY_PATH = "00_sistema_tesis/config/traceability_quality_policy.yaml"
BASELINE_PATH = "00_sistema_tesis/config/traceability_quality_baseline.yaml"


def _load_policy() -> dict:
    return load_yaml_json(POLICY_PATH)


def _load_baseline() -> set[str]:
    baseline_file = ROOT / BASELINE_PATH
    if not baseline_file.exists():
        return set()
    payload = load_yaml_json(BASELINE_PATH)
    ignored = payload.get("ignored_findings", [])
    return {str(item).strip() for item in ignored if str(item).strip()}


def _apply_baseline(errors: list[str], ignored: set[str]) -> list[str]:
    if not ignored:
        return errors
    normalized_ignored = {item.replace("\\", "/") for item in ignored}
    kept: list[str] = []
    for error in errors:
        if error in ignored:
            continue
        if error.replace("\\", "/") in normalized_ignored:
            continue
        kept.append(error)
    return kept


def verify_ledger(policy: dict) -> list[str]:
    errors: list[str] = []
    text = LEDGER_PATH.read_text(encoding="utf-8")
    blocks = re.findall(r"## \[(VAL-STEP-\d+)\](.*?)(?=\n## \[VAL-STEP-|\Z)", text, re.DOTALL)
    min_chars = int(policy["ledger"].get("min_content_chars", 24))
    allowed_levels = set(policy["ledger"].get("allowed_audit_levels", []))

    for step_id, block in blocks:
        content_match = re.search(r"<<<\s*(.*?)\s*>>>", block, re.DOTALL)
        if policy["ledger"].get("require_non_empty_content_between_delimiters") and content_match:
            content = content_match.group(1).strip()
            if len(content) < min_chars:
                errors.append(f"{step_id}: contenido entre <<< >>> insuficiente (min {min_chars} chars)")

        level_match = re.search(r"\*\*Audit Level:\*\*\s*`([^`]+)`", block)
        if level_match:
            level = level_match.group(1).strip().upper()
            if allowed_levels and level not in allowed_levels:
                errors.append(f"{step_id}: Audit Level no permitido ({level})")

    return errors


def verify_matrix(policy: dict) -> list[str]:
    errors: list[str] = []
    lines = MATRIX_PATH.read_text(encoding="utf-8").splitlines()
    banned = set(policy["matrix"].get("disallow_generic_descriptions", []))
    for idx, line in enumerate(lines, start=1):
        if "|" not in line or "VAL-STEP-" not in line:
            continue
        for token in banned:
            if token in line:
                errors.append(f"matriz_trazabilidad.md:{idx}: descripcion generica prohibida '{token}'")
    return errors


def verify_decisions(policy: dict) -> list[str]:
    errors: list[str] = []
    if not policy["decisions"].get("proposal_cannot_have_implementation_checked", True):
        return errors
    for path in sorted(DECISIONS_DIR.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        if not re.search(r"Estado:\s*propuesta", content, re.IGNORECASE):
            continue
        if "## Implementación o seguimiento" in content and re.search(r"## Implementación o seguimiento[\s\S]*?- \[x\]", content):
            errors.append(f"{path.relative_to(ROOT)}: estado propuesta con implementacion marcada [x]")
    return errors


def main() -> int:
    strict = "--strict" in sys.argv[1:]
    policy = _load_policy()
    ignored_findings = _load_baseline()
    errors = []
    errors.extend(verify_ledger(policy))
    errors.extend(verify_matrix(policy))
    errors.extend(verify_decisions(policy))
    errors = _apply_baseline(errors, ignored_findings)
    if errors:
        print("TRACEABILITY_QUALITY: FAIL")
        for error in errors:
            print(f"- {error}")
        if strict:
            return 1
        print("TRACEABILITY_QUALITY: WARN (modo no estricto)")
        return 0
    print("TRACEABILITY_QUALITY: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
