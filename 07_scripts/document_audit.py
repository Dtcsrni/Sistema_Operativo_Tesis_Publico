import re
import sys
from pathlib import Path


BASE_PRECHECK_MARKERS = ["[Integridad][LID]", "[Ética][GOV]", "[Auditoría][AUD]"]
RICH_PRECHECK_MARKERS = ["Contexto explícito", "Confirmación verificable", "Reproducibilidad mínima"]
REQUIRED_REFS = ["[LID]:", "[GOV]:", "[AUD]:"]
REF_LINK_PATTERN = re.compile(r"^\[(LID|GOV|AUD)\]:\s+(.+?)\s*$")


def _window(lines: list[str], index: int, before: int = 0, after: int = 0) -> list[str]:
    start = max(0, index - before)
    end = min(len(lines), index + after + 1)
    return lines[start:end]


def _has_verbal_confirmation_block(window_lines: list[str]) -> bool:
    required_patterns = [
        "**Texto exacto de confirmación verbal:**",
        "**Hash de confirmación verbal:**",
        "**Fuente de verdad de confirmación:**",
    ]
    return all(any(pattern in line for line in window_lines) for pattern in required_patterns)


def audit_document(file_path):
    content = Path(file_path).read_text(encoding="utf-8")
    lines = content.splitlines()
    errors = []

    for ref in REQUIRED_REFS:
        if ref not in content:
            errors.append(f"Falta definición de referencia global: {ref}")

    ref_targets: dict[str, str] = {}
    for raw_line in lines:
        match = REF_LINK_PATTERN.match(raw_line.strip())
        if not match:
            continue
        ref_targets[match.group(1)] = match.group(2).strip()

    rel_hint = str(Path(file_path)).replace("\\", "/")
    enforce_traceable_refs = "/bitacora/" in rel_hint
    if enforce_traceable_refs:
        for ref_name in ("LID", "GOV", "AUD"):
            target = ref_targets.get(ref_name, "")
            if target.startswith("file:///"):
                errors.append(f"Referencia [{ref_name}] no trazable en GitHub: usa ruta relativa en lugar de file:///")

    for i, line in enumerate(lines):
        stripped = line.strip()
        match = re.search(r"[-*]\s+\[([\sxX])\]", line)
        if match and "Pre-checks:" not in line and "Pre-requisitos Técnicos" not in line:
            if i + 1 < len(lines) and "Pre-checks:" not in lines[i + 1]:
                if not stripped.startswith(("#", "|", ">", "```")):
                    errors.append(f"Línea {i + 1}: Tarea '{stripped}' no tiene bloque de autoauditoría (Pre-checks)")

        if "Pre-checks:" in line:
            missing_markers = [marker for marker in BASE_PRECHECK_MARKERS + RICH_PRECHECK_MARKERS if marker not in line]
            if missing_markers:
                errors.append(
                    f"Línea {i + 1}: Bloque de autoauditoría incompleto o mal formateado. Faltan: {', '.join(missing_markers)}"
                )

        support_match = re.search(r"\*\*Soporte:\*\*.*(VAL-STEP-[A-Za-z0-9_-]+)", line)
        if support_match:
            nearby = _window(lines, i, after=6)
            if not _has_verbal_confirmation_block(nearby):
                errors.append(
                    f"Línea {i + 1}: Soporte {support_match.group(1)} sin bloque explícito de confirmación verbal verificable"
                )

        if "**Texto exacto de confirmación verbal:**" in line:
            verbal_text = line.split(":", maxsplit=1)[1].strip()
            if not verbal_text or verbal_text == "[PENDIENTE]":
                errors.append(f"Línea {i + 1}: El texto exacto de confirmación verbal está vacío")

        if (
            "**Fuente de verdad de confirmación:**" in line
            and "human_validation.confirmation_text" not in line
            and "No existe `VAL-STEP-*`" not in line
        ):
            errors.append(
                f"Línea {i + 1}: La fuente de verdad de confirmación debe apuntar al campo canónico `human_validation.confirmation_text`"
            )

    return errors


def main():
    root = Path(__file__).resolve().parents[1]
    dirs = ["00_sistema_tesis/decisiones", "00_sistema_tesis/bitacora"]

    all_errors = []
    for directory in dirs:
        path = root / directory
        if not path.exists():
            continue
        for file_path in path.glob("*.md"):
            if file_path.name in ["log_conversaciones_ia.md", "matriz_trazabilidad.md"]:
                continue
            file_errors = audit_document(file_path)
            if file_errors:
                all_errors.append((file_path.name, file_errors))

    if all_errors:
        print("AUTOAUDITORÍA DOCUMENTAL: FALLIDA")
        for filename, errors in all_errors:
            print(f"\n [!] Archivo: {filename}")
            for error in errors:
                print(f"     - {error}")
        sys.exit(1)

    print("AUTOAUDITORÍA DOCUMENTAL: ÉXITOSA (Integridad de Trazabilidad Confirmada)")


if __name__ == "__main__":
    main()
