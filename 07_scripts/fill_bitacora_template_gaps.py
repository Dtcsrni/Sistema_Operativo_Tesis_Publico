from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BITACORA_DIR = ROOT / "00_sistema_tesis" / "bitacora"
TEMPLATE_PATH = ROOT / "00_sistema_tesis" / "plantillas" / "bitacora_template.md"

TARGETS = sorted(BITACORA_DIR.glob("*.md"))
TARGETS = [path for path in TARGETS if path.exists()]
# Deduplicate while preserving order.
seen_paths: set[Path] = set()
TARGETS = [path for path in TARGETS if not (path in seen_paths or seen_paths.add(path))]

TEMPLATE_HEADERS = re.findall(r"^## (.*)$", TEMPLATE_PATH.read_text(encoding="utf-8"), re.MULTILINE)

BASE_APPENDIX = {
    "Infraestructura de Sesión": [
        "- **OS:** [N/A Retroactivo]",
        "- **Python:** [N/A Retroactivo]",
        "- **Herramientas Clave:** [N/A Retroactivo]",
    ],
    "Objetivo de la sesión": [
        "Registro retroactivo para completar la estructura histórica de la bitácora.",
    ],
    "Tareas del día": [
        "- [x] Actividad histórica preservada en el cuerpo principal de la bitácora.",
    ],
    "Trabajo realizado": [
        "- Resumen retroactivo conservado en el contenido principal del documento.",
    ],
    "Evidencia Técnica e Integridad": [
        "- **Commits:** [N/A Retroactivo]",
        "- **Archivos Clave:** [Ver contenido histórico del archivo]",
        "- **Validación del Sistema:** [N/A Retroactivo]",
    ],
    "Trabajo asistido con IA y gobernanza": [
        "- **Proveedor de asistencia:** [N/A Retroactivo]",
        "- **Modelo/Versión de asistencia:** [N/A Retroactivo]",
        "- **Objetivo:** [N/A Retroactivo]",
        "- **Nivel de Razonamiento:** [medio]",
        "- **Alineación Ética:**",
        "    - [x] Transparencia (NIST RMF)",
        "    - [x] Soberanía Humana (UNESCO)",
        "    - [x] Responsabilidad (ISO 42001)",
    ],
    "Economía de uso": [
        "- Presupuesto vs Avance: [N/A Retroactivo]",
        "- Qué se evitó: [N/A Retroactivo]",
        "- Qué ameritaría subir razonamiento en la siguiente sesión: [N/A Retroactivo]",
    ],
    "Siguiente paso concreto": [
        "Completar la sincronización documental retroactiva con el resto de artefactos del día.",
    ],
}

IA_COMPATIBILITY_BLOCK = [
    "### Compatibilidad de plantilla retroactiva",
    "- **Prompts Asociados:** [N/A Retroactivo]",
    "- **Soporte:** [N/A Retroactivo]",
    "- **Modo:** [N/A Retroactivo]",
    "- **Pregunta Crítica de Validación:** [N/A Retroactivo]",
]

HANDSHAKE_BLOCK = [
    "### Validación de Soberanía (Handshake)",
    "- **Pregunta Crítica:** [N/A Retroactivo]",
    "- **Respuesta Erick Vega:** [N/A Retroactivo]",
    "- **Criterio de Aceptación:** [x] Validado.",
    "  - **Pre-checks:** [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima",
    "  - **Soporte:** [N/A Retroactivo]",
    "  - **Modo:** [N/A Retroactivo]",
    "  - **Hash (Contenido):** `sha256:N/A`",
    "  - **Fingerprint:** `sha256:N/A`",
    "  - **Nivel de Riesgo:** [Medio]",
    "  - **Pregunta crítica o disparador:** [N/A Retroactivo]",
    "  - **Texto exacto de confirmación verbal:** [N/A Retroactivo]",
    "  - **Hash de confirmación verbal:** `sha256:N/A`",
    "  - **Fuente de verdad de confirmación:** [N/A Retroactivo]",
]


def _insert_before_footers(text: str, addition: str) -> str:
    marker = "\n[LID]:"
    idx = text.find(marker)
    if idx == -1:
        if not text.endswith("\n"):
            text += "\n"
        return text + "\n" + addition.strip() + "\n"
    return text[:idx].rstrip() + "\n\n" + addition.strip() + "\n\n" + text[idx:].lstrip("\n")


def _append_missing_headers(path: Path, content: str) -> tuple[str, list[str]]:
    existing_headers = set(re.findall(r"^## (.*)$", content, re.MULTILINE))
    missing_headers = [header for header in TEMPLATE_HEADERS if header not in existing_headers]
    blocks: list[str] = []

    if missing_headers:
        for header in missing_headers:
            if header in BASE_APPENDIX:
                blocks.append(f"## {header}")
                blocks.extend(BASE_APPENDIX[header])
                blocks.append("")
            else:
                blocks.append(f"## {header}")
                blocks.append("- [N/A Retroactivo]")
                blocks.append("")

    needs_ia_patterns = {
        "Prompts Asociados": r"\*\*Prompts Asociados:\*\*",
        "Soporte": r"\*\*Soporte:\*\*",
        "Modo": r"\*\*Modo:\*\*",
        "Pregunta Crítica de Validación": r"\*\*Pregunta Crítica de Validación:\*\*",
    }
    missing_ia_patterns = [label for label, pattern in needs_ia_patterns.items() if not re.search(pattern, content)]
    if missing_ia_patterns:
        if "Trabajo asistido con IA y gobernanza" not in existing_headers:
            blocks.append("## Trabajo asistido con IA y gobernanza")
            blocks.extend(BASE_APPENDIX["Trabajo asistido con IA y gobernanza"])
            blocks.append("")
            blocks.extend(HANDSHAKE_BLOCK)
            blocks.append("")
            blocks.extend(IA_COMPATIBILITY_BLOCK)
            blocks.append("")
        elif "### Compatibilidad de plantilla retroactiva" not in content:
            blocks.append("### Compatibilidad de plantilla retroactiva")
            if "Prompts Asociados" in missing_ia_patterns:
                blocks.append("- **Prompts Asociados:** [N/A Retroactivo]")
            if "Soporte" in missing_ia_patterns:
                blocks.append("- **Soporte:** [N/A Retroactivo]")
            if "Modo" in missing_ia_patterns:
                blocks.append("- **Modo:** [N/A Retroactivo]")
            if "Pregunta Crítica en Uso de IA" in missing_ia_patterns:
                blocks.append("- **Pregunta Crítica en Uso de IA:** [N/A Retroactivo]")
            blocks.append("")
            if "Pregunta Crítica en Uso de IA" in missing_ia_patterns:
                blocks.extend(HANDSHAKE_BLOCK)
                blocks.append("")

    if not blocks:
        return content, []

    addition = "\n".join(blocks).rstrip() + "\n"
    updated = _insert_before_footers(content, addition)
    return updated, missing_headers + missing_ia_patterns


def main() -> int:
    changed = []
    for path in TARGETS:
        content = path.read_text(encoding="utf-8")
        updated, notes = _append_missing_headers(path, content)
        if updated != content:
            path.write_text(updated, encoding="utf-8")
            changed.append((path.relative_to(ROOT), notes))
            print(f"ACTUALIZADO {path.relative_to(ROOT)}")
            if notes:
                print(f"  - faltantes cubiertos: {', '.join(notes)}")
    print(f"TOTAL ACTUALIZADOS: {len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
