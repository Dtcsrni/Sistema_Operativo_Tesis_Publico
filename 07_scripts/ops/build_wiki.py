from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings



from html import escape

import posixpath
import re

from common import (
    ROOT,
    canonical_file_status,
    directory_markdown_status,
    dump_json,
    ensure_directory,
    file_sha256,
    list_markdown_entries,
    load_csv_rows,
    load_yaml_json,
    path_timestamp,
    stable_generated_at,
    write_text_if_changed,
)

SECTION_IDS = {
    "casos_uso",
    "sistema",
    "gobernanza",
    "arquitectura",
    "terminologia",
    "hipotesis",
    "bloques",
    "planeacion",
    "decisiones",
    "bitacora",
    "experimentos",
    "implementacion",
    "tesis",
}

PAGE_ORDER = [
    "casos_uso",
    "sistema",
    "gobernanza",
    "arquitectura",
    "terminologia",
    "planeacion",
    "hipotesis",
    "bloques",
    "decisiones",
    "bitacora",
    "experimentos",
    "implementacion",
    "tesis",
]

PAGE_TITLES = {
    "casos_uso": "Agente y Casos de Uso",
    "sistema": "Sistema",
    "gobernanza": "Gobernanza",
    "arquitectura": "Arquitectura",
    "terminologia": "Terminología",
    "hipotesis": "Hipótesis",
    "bloques": "Bloques",
    "planeacion": "Planeación",
    "decisiones": "Decisiones",
    "bitacora": "Bitácora",
    "experimentos": "Experimentos",
    "implementacion": "Implementación",
    "tesis": "Tesis",
}

PAGE_RELATED = {
    "casos_uso": ["sistema", "gobernanza", "decisiones"],
    "sistema": ["gobernanza", "terminologia", "planeacion"],
    "gobernanza": ["sistema", "arquitectura", "bitacora"],
    "arquitectura": ["sistema", "gobernanza", "decisiones"],
    "terminologia": ["sistema", "gobernanza", "planeacion"],
    "planeacion": ["bloques", "hipotesis", "decisiones"],
    "hipotesis": ["planeacion", "bloques", "experimentos"],
    "bloques": ["planeacion", "hipotesis", "implementacion"],
    "decisiones": ["bitacora", "planeacion", "sistema"],
    "bitacora": ["decisiones", "gobernanza", "planeacion"],
    "experimentos": ["hipotesis", "implementacion", "tesis"],
    "implementacion": ["bloques", "experimentos", "tesis"],
    "tesis": ["experimentos", "implementacion", "decisiones"],
}

PAGE_ICONS = {
    "casos_uso": "smart_toy",
    "sistema": "settings",
    "gobernanza": "gavel",
    "arquitectura": "architecture",
    "terminologia": "book",
    "hipotesis": "lightbulb",
    "bloques": "grid_view",
    "planeacion": "event_note",
    "decisiones": "psychology",
    "bitacora": "history_edu",
    "experimentos": "science",
    "implementacion": "code",
    "tesis": "school",
}

REQUIRED_PAGE_FIELDS = [
    "Tesista",
    "Fecha",
    "Estado",
    "Fuentes",
    "Aviso",
]

WIKI_MARKDOWN_DIR = Path("06_dashboard/wiki")
WIKI_HTML_DIR = Path("06_dashboard/generado/wiki")
PUBLIC_WIKI_MARKDOWN_DIR = Path("06_dashboard/publico/wiki")
PUBLIC_WIKI_HTML_DIR = Path("06_dashboard/publico/wiki_html")

MARKDOWN_LINK_PATTERN = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")
SKIP_LINK_PREFIXES = ("http://", "https://", "mailto:", "tel:", "data:", "javascript:")
NON_REPO_LINK_PREFIXES = ("file:",)

def relative_wiki_link(page_id: str) -> str:
    return f"{page_id}.md"

def _normalize_repo_relpath(base_rel: str, href: str) -> str:
    base_dir = Path(base_rel).parent.as_posix()
    normalized = posixpath.normpath(posixpath.join(base_dir, href))
    return normalized.lstrip("./")

def _relative_link(from_dir: Path, target_rel: str) -> str:
    return Path(posixpath.relpath(target_rel, from_dir.as_posix())).as_posix()

def _rewrite_embedded_markdown_links(text: str, source_rel: str) -> str:
    def replace(match: re.Match[str]) -> str:
        label, href = match.groups()
        href = href.strip()
        if not href or href.startswith("#") or href.startswith(SKIP_LINK_PREFIXES):
            return match.group(0)
        if href.startswith(NON_REPO_LINK_PREFIXES):
            return f"`{label}`"
        target, separator, anchor = href.partition("#")
        normalized = _normalize_repo_relpath(source_rel, target)
        relative = _relative_link(WIKI_MARKDOWN_DIR, normalized)
        suffix = f"#{anchor}" if separator else ""
        return f"[{label}]({relative}{suffix})"

    return MARKDOWN_LINK_PATTERN.sub(replace, text)

def repo_link_from_wiki(target_rel: str) -> str:
    return _relative_link(WIKI_MARKDOWN_DIR, target_rel)

def get_sign_off_badge(rel_path: str, current_hash: str, sign_offs: list[dict]) -> str:
    """Retorna un badge de validación humana si el hash coincide."""
    for record in sign_offs:
        if record["archivo"] == rel_path:
            if record["hash_verificado"] == current_hash:
                return "!!! success \"Validación Humana: VERIFICADA\"\n    Este contenido ha sido supervisado y firmado por el tesista humano. (SHA256: `" + current_hash[:8] + "...`)\n"
            else:
                return "!!! warning \"Validación Humana: DESACTUALIZADA\"\n    El archivo original ha sido modificado después de la última firma humana. Requiere revisión.\n"
    return "!!! danger \"Validación Humana: AUSENTE\"\n    No se ha registrado firma de supervisión para este artefacto en `sign_offs.yaml`.\n"

def render_metadata(*, generated_at: str, status: str, sources: list[str], notice: str) -> list[str]:
    tesista = load_yaml_json("00_sistema_tesis/config/tesista.json")
    nombre = tesista["tesista"]["nombre_completo"]

    return [
        f"- **Tesista:** `{nombre}`",
        f"- **Fecha:** `{generated_at}`",
        f"- **Estado:** `{status.upper()}`",
        f"- **Fuentes:** {', '.join(f'`{item}`' for item in sources)}",
        f"- **Aviso:** {notice}",
        "",
    ]

def render_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return ["No hay filas disponibles.", ""]
    separator = "|" + "|".join(["---"] * len(headers)) + "|"
    lines = ["|" + "|".join(headers) + "|", separator]
    for row in rows:
        sanitized = [str(item).replace("\n", " ").replace("|", "\\|") for item in row]
        lines.append("|" + "|".join(sanitized) + "|")
    lines.append("")
    return lines

def render_markdown_fragment(rel_path: str, *, demote_by: int = 1) -> list[str]:
    target = ROOT / rel_path
    if not target.exists():
        return [f"_Fuente narrativa no disponible: `{rel_path}`_", ""]
    lines: list[str] = []
    for raw_line in target.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(#+)\s+(.*)$", raw_line)
        if match:
            hashes, title = match.groups()
            raw_line = f"{'#' * (len(hashes) + demote_by)} {title}"
        raw_line = raw_line.replace("log_conversaciones_ia.md", "log_sesiones_trabajo_registradas.md")
        if rel_path.endswith("00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md"):
            # Evita que contenido de trazas (por ejemplo <match ...>) rompa el parser HTML de MkDocs.
            raw_line = raw_line.replace("<", "&lt;").replace(">", "&gt;")
        raw_line = _rewrite_embedded_markdown_links(raw_line, rel_path)
        lines.append(raw_line)
    lines.append("")
    return lines

def _indent_markdown_block(lines: list[str], spaces: int = 4) -> list[str]:
    prefix = " " * spaces
    return [f"{prefix}{line}" if line else prefix for line in lines]

def _month_bucket_from_date(date_str: str) -> str:
    if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return date_str[:7]
    return "sin-fecha"

def _is_iso_date(date_str: str) -> bool:
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}$", date_str))

def _month_bucket_sort_key(bucket: str) -> tuple[int, str]:
    if bucket == "sin-fecha":
        return (0, "")
    return (1, bucket)

def _safe_details_title(text: str) -> str:
    return text.replace('"', r'\"').strip()

def _truncate_text(value: str, *, max_chars: int = 220) -> str:
    compact = re.sub(r"\s+", " ", value).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rstrip() + "..."

def _index_decisions_by_id() -> dict[str, str]:
    decisions_dir = ROOT / "00_sistema_tesis/decisiones"
    decision_index: dict[str, str] = {}
    if not decisions_dir.exists():
        return decision_index

    for item in decisions_dir.glob("*.md"):
        match = re.search(r"(DEC-\d{4})", item.name)
        if not match:
            continue
        decision_index[match.group(1)] = f"00_sistema_tesis/decisiones/{item.name}"
    return decision_index

def _render_vinculo_summary(vinculo_text: str, decisions_index: dict[str, str]) -> str:
    normalized = (vinculo_text or "").strip()
    if not normalized:
        return "Sin vínculo"

    dec_match = re.search(r"(DEC-\d{4})", normalized)
    if dec_match:
        dec_id = dec_match.group(1)
        target_rel = decisions_index.get(dec_id)
        if target_rel:
            return f"[{dec_id}]({repo_link_from_wiki(target_rel)})"

    return f"`{normalized}` (referencia operativa interna no enlazable)"

def _parse_ledger_validation_entries(rel_path: str) -> list[dict[str, str]]:
    target = ROOT / rel_path
    if not target.exists():
        return []

    entries: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    in_raw_content = False

    def match_field(line: str, label: str) -> str | None:
        pattern = rf"^- \*\*{re.escape(label)}:\*\*\s*(.+)$"
        match = re.match(pattern, line)
        if not match:
            return None
        return match.group(1).strip()

    for raw_line in target.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if stripped == "<<<":
            in_raw_content = True
            continue
        if stripped.endswith(">>>"):
            in_raw_content = False
            continue
        if in_raw_content:
            continue

        heading_match = re.match(r"^## \[(VAL-STEP-[^\]]+)\]", stripped)
        if heading_match:
            if current:
                entries.append(current)
            current = {
                "step_id": heading_match.group(1),
                "fecha": "",
                "vinculo": "",
                "audit_level": "",
                "pregunta": "",
                "confirmacion": "",
            }
            continue

        if not current:
            continue

        fecha = match_field(stripped, "Fecha")
        if fecha is not None:
            current["fecha"] = fecha
            continue

        vinculo = match_field(stripped, "Vínculo")
        if vinculo is not None:
            current["vinculo"] = vinculo
            continue

        audit_level = match_field(stripped, "Audit Level")
        if audit_level is not None:
            current["audit_level"] = audit_level
            continue

        pregunta = match_field(stripped, "Pregunta Crítica / Disparador")
        if pregunta is not None:
            current["pregunta"] = pregunta
            continue

        confirmacion = match_field(stripped, "Confirmación Verbal (Texto Exacto)")
        if confirmacion is not None:
            current["confirmacion"] = confirmacion

    if current:
        entries.append(current)
    return entries

def _render_ledger_monthly_summary() -> list[str]:
    rel_path = "00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md"
    entries = _parse_ledger_validation_entries(rel_path)
    decisions_index = _index_decisions_by_id()
    if not entries:
        lines = [
            "## Bitácora de sesiones de trabajo registradas",
            "",
            "No se pudo construir el resumen mensual. Consulta el archivo canónico para ver el contenido completo.",
            "",
            f"- **Archivo completo:** [{rel_path}]({repo_link_from_wiki(rel_path)})",
            "",
        ]
        return lines

    grouped: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        bucket = _month_bucket_from_date(entry["fecha"])
        grouped.setdefault(bucket, []).append(entry)

    ordered_buckets = sorted(grouped.keys(), key=_month_bucket_sort_key, reverse=True)
    lines = [
        "## Bitácora de sesiones de trabajo registradas",
        "",
        "### Qué es este bloque",
        "",
        "Este bloque existe para conservar, en superficie pública, la evidencia mínima de validación humana",
        "que sostiene la gobernanza del sistema sin exponer contenido sensible del ledger canónico.",
        "",
        "### Para qué sirve",
        "",
        "- Permite rastrear qué validaciones humanas habilitaron cambios relevantes.",
        "- Conecta decisiones canónicas con sesiones de trabajo de forma auditable.",
        "- Facilita revisión pública sin publicar transcripciones completas ni datos internos.",
        "",
        "### Qué representa",
        "",
        "Representa un resumen sanitizado de validaciones (no una transcripción completa del Libro Mayor).",
        "Cada registro conserva fecha, referencia operativa, nivel de auditoría y síntesis del disparador/confirmación.",
        "",
        "### Enlaces de navegación",
        "",
        f"- **Ledger completo:** [{rel_path}]({repo_link_from_wiki(rel_path)})",
        f"- **Matriz de trazabilidad:** [00_sistema_tesis/bitacora/matriz_trazabilidad.md]({repo_link_from_wiki('00_sistema_tesis/bitacora/matriz_trazabilidad.md')})",
        f"- **Índice de decisiones:** [06_dashboard/wiki/decisiones.md]({repo_link_from_wiki('06_dashboard/wiki/decisiones.md')})",
        "",
        "### Índices maestros",
        "",
        f"- **Total de registros de validación:** `{len(entries)}`",
        "",
    ]

    for bucket in ordered_buckets:
        bucket_title = bucket if bucket != "sin-fecha" else "Sin fecha (registro heredado)"
        month_entries = grouped[bucket]
        lines.append(f'??? "{bucket_title} — {len(month_entries)} validación(es)"')
        lines.append("")
        for index, entry in enumerate(month_entries, start=1):
            fecha = entry["fecha"] if _is_iso_date(entry["fecha"]) else "Sin fecha"
            vinculo = _render_vinculo_summary(entry["vinculo"], decisions_index)
            audit_level = entry["audit_level"] or "N/D"
            pregunta = _truncate_text(entry["pregunta"] or "No especificado.", max_chars=280)
            confirmacion = _truncate_text(entry["confirmacion"] or "No especificado.", max_chars=280)
            step_id = entry["step_id"] or "N/D"

            lines.append(f"    **[{step_id}] Registro {index} del mes**")
            lines.append("")
            lines.append(f"    - **Fecha:** `{fecha}`")
            lines.append(f"    - **Decisión o referencia:** {vinculo}")
            lines.append(f"    - **Nivel de auditoría:** `{audit_level}`")
            lines.append(f"    - **Disparador resumido:** {pregunta}")
            lines.append(f"    - **Confirmación resumida:** {confirmacion}")
            lines.append("")

    return lines

def _extract_markdown_summary(rel_path: str, *, max_lines: int = 4, max_chars: int = 420) -> list[str]:
    target = ROOT / rel_path
    if not target.exists():
        return ["Resumen no disponible (archivo no encontrado)."]

    summary: list[str] = []
    total_chars = 0
    in_front_matter = False
    front_matter_checked = False
    in_code_block = False

    for raw_line in target.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not front_matter_checked and stripped == "---":
            in_front_matter = True
            front_matter_checked = True
            continue
        if in_front_matter:
            if stripped == "---":
                in_front_matter = False
            continue

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        normalized = stripped
        while re.match(r"^[-*+]\s+", normalized):
            normalized = re.sub(r"^[-*+]\s+", "", normalized)
        normalized = re.sub(r"^\d+\.\s+", "", normalized)
        normalized = _rewrite_embedded_markdown_links(normalized, rel_path)
        if normalized.startswith("<!--"):
            continue
        if normalized.startswith("|"):
            continue

        projected = total_chars + len(normalized)
        if projected > max_chars and summary:
            break

        summary.append(normalized)
        total_chars = projected
        if len(summary) >= max_lines:
            break

    if not summary:
        return ["Sin resumen breve disponible; consulta el archivo para ver el contenido completo."]
    return summary

def render_source_links(sources: list[str]) -> list[str]:
    rows: list[list[str]] = []
    for path in sources:
        source = ROOT / path
        kind = "directorio" if source.is_dir() else "archivo"
        rows.append([f"[`{path}`]({repo_link_from_wiki(path)})", kind, "sí" if source.exists() else "no"])
    return render_table(["Fuente canónica", "Tipo", "Existe"], rows)

def render_page_navigation(page_id: str) -> list[str]:
    position = PAGE_ORDER.index(page_id)
    previous_page = PAGE_ORDER[position - 1] if position > 0 else None
    next_page = PAGE_ORDER[position + 1] if position + 1 < len(PAGE_ORDER) else None
    related = PAGE_RELATED.get(page_id, [])
    lines = [
        "## Navegación de esta página",
        "",
        "- [Volver al índice](index.md).",
    ]
    if previous_page:
        lines.append(f"- Página anterior en la ruta base: [{PAGE_TITLES[previous_page]}]({relative_wiki_link(previous_page)}).")
    if next_page:
        lines.append(f"- Página siguiente en la ruta base: [{PAGE_TITLES[next_page]}]({relative_wiki_link(next_page)}).")
    for related_page in related:
        lines.append(f"- Relacionada: [{PAGE_TITLES[related_page]}]({relative_wiki_link(related_page)}).")
    lines.append("")
    return lines

def render_origin_block(page_id: str, sources: list[str]) -> list[str]:
    lines = [
        "## Origen canónico y artefactos relacionados",
        "",
        "### Cómo rastrear esta página hasta su origen canónico",
        "",
        f"1. Esta página derivada: [`06_dashboard/wiki/{page_id}.md`]({page_id}.md).",
        "2. Revisa la lista de fuentes canónicas que alimentan su contenido.",
        "3. Si necesitas la versión visual derivada, consulta el HTML hermano generado.",
        "4. Si necesitas divulgación o evaluación externa, consulta el artefacto público sanitizado equivalente.",
        "5. Si necesitas cambiar el contenido, edita la fuente canónica y reconstruye; no edites esta salida a mano.",
        "",
        "### Fuentes canónicas declaradas",
        "",
    ]
    lines.extend(render_source_links(sources))
    lines.extend(
        [
            "### Artefactos derivados relacionados",
            "",
            f"- Markdown interno: [`06_dashboard/wiki/{page_id}.md`]({page_id}.md)",
            f"- HTML interno: [`06_dashboard/generado/wiki/{page_id}.html`]({_relative_link(WIKI_MARKDOWN_DIR, (WIKI_HTML_DIR / f'{page_id}.html').as_posix())})",
            f"- Markdown público sanitizado: [`06_dashboard/publico/wiki/{page_id}.md`]({_relative_link(WIKI_MARKDOWN_DIR, (PUBLIC_WIKI_MARKDOWN_DIR / f'{page_id}.md').as_posix())})",
            f"- HTML público sanitizado: [`06_dashboard/publico/wiki_html/{page_id}.html`]({_relative_link(WIKI_MARKDOWN_DIR, (PUBLIC_WIKI_HTML_DIR / f'{page_id}.html').as_posix())})",
            "",
        ]
    )
    return lines

def render_index_page(wiki: dict, pages: list[dict], generated_at: str) -> str:
    lines = [
        "# Wiki verificable del sistema operativo de tesis",
        "",
        wiki["proposito"],
        "",
    ]
    lines.extend(
        render_metadata(
            generated_at=generated_at,
            status="ok",
            sources=wiki["fuentes_base"],
            notice=wiki["politica"]["aviso_no_editar"],
        )
    )
    lines.extend(
        [
            "## Estado de verificación",
            "",
            f"- Fecha de generación: `{generated_at}`",
            "- Estado de verificación: `ok`",
            f"- Fuentes canónicas: {', '.join(f'`{item}`' for item in wiki['fuentes_base'])}",
            "",
        ]
    )
    # Métrica de Soberanía Humana
    total_pages = len(pages)
    verified_pages = sum(1 for p in pages if p.get("verified", False))
    sovereignty = (verified_pages / total_pages * 100) if total_pages > 0 else 0
    
    lines.extend([
        "## Métrica de Soberanía Humana",
        "",
        f"Actualmente, el **{sovereignty:.1f}%** de los artefactos nucleares de esta tesis han sido verificados y firmados por el tesista humano.",
        "",
        "```mermaid",
        "graph LR",
        f"  A[Soberanía Humana] --- B({sovereignty:.1f}%)",
        "  style B fill:#f9f,stroke:#333,stroke-width:4px",
        "```",
        ""
    ])

    lines.extend(
        [
            "## Índice",
            "",
        ]
    )
    for page in pages:
        lines.append(f"- [{page['title']}]({relative_wiki_link(page['id'])})")
    lines.extend(
        [
            "",
            "## Qué explica esta documentación",
            "",
            "- Para qué y por qué existe el sistema.",
            "- Cuáles son sus módulos y cómo se relacionan.",
            "- Cuáles son sus flujos operativos principales.",
            "- Cómo interactúa con él el tesista.",
            "- Cómo puede explorarlo y evaluarlo un lector público sin acceder a superficies privadas.",
            "",
            "## Ruta de lectura",
            "",
            "- Si necesitas entender el sistema completo, empieza por [Sistema](sistema.md).",
            "- Si necesitas reglas y límites, continúa con [Gobernanza](gobernanza.md).",
            "- Si necesitas lenguaje, familias de IDs y convenciones, pasa por [Terminología](terminologia.md).",
            "- Si necesitas estado del trabajo, revisa [Planeación](planeacion.md), [Hipótesis](hipotesis.md) y [Bloques](bloques.md).",
            "- Si necesitas evidencia de avance o cobertura, revisa [Decisiones](decisiones.md), [Bitácora](bitacora.md), [Implementación](implementacion.md), [Experimentos](experimentos.md) y [Tesis](tesis.md).",
            "",
            "## Mapa de navegación por intención",
            "",
            "- Entender el sistema: [Sistema](sistema.md) -> [Gobernanza](gobernanza.md) -> [Terminología](terminologia.md).",
            "- Retomar ejecución: [Planeación](planeacion.md) -> [Bloques](bloques.md) -> [Hipótesis](hipotesis.md).",
            "- Rastrear decisiones y sesiones: [Decisiones](decisiones.md) -> [Bitácora](bitacora.md).",
            "- Revisar madurez técnica: [Experimentos](experimentos.md) -> [Implementación](implementacion.md) -> [Tesis](tesis.md).",
            "",
            "## Cómo rastrear un artefacto derivado hasta su origen canónico",
            "",
            "- Empieza por la página derivada que estás leyendo.",
            "- Revisa su bloque `Origen canónico y artefactos relacionados`.",
            "- Sigue la lista de fuentes canónicas declaradas en esa misma página.",
            "- Si necesitas validar la cadena de publicación, cruza con `06_dashboard/generado/wiki_manifest.json` y `06_dashboard/publico/manifest_publico.json`.",
            "- Si necesitas trazabilidad operativa interna, consulta `00_sistema_tesis/bitacora/matriz_trazabilidad.md` y `00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md`.",
            "",
            "## Módulos del sistema",
            "",
            "- Gobierno y soberanía humana.",
            "- Trazabilidad y evidencia.",
            "- Planeación y control del trabajo.",
            "- Canon técnico y configuración.",
            "- Automatización y validación.",
            "- Publicación derivada y superficie pública.",
            "- Tesis IoT como objeto gobernado.",
            "",
            "## Operación humana y frontera público/privado",
            "",
            "- La superficie **privada** gobierna canon, backlog, decisiones, bitácora y auditoría completa.",
            "- La superficie **pública** es un bundle sanitizado, derivado y reproducible para divulgación y evaluación externa.",
            "- La **IA es opcional**: el sistema debe poder retomarse, auditarse y publicarse siguiendo rutas humanas explícitas.",
            "",
            "## Qué revisar siempre",
            "",
            "- `00_sistema_tesis/manual_operacion_humana.md`",
            "- `00_sistema_tesis/config/sistema_tesis.yaml`",
            "- `01_planeacion/backlog.csv`",
            "- `01_planeacion/riesgos.csv`",
            "- `00_sistema_tesis/bitacora/matriz_trazabilidad.md`",
            "- `06_dashboard/generado/wiki_manifest.json`",
            "- `06_dashboard/wiki/index.md`",
            "- `06_dashboard/generado/index.html`",
            "- `06_dashboard/publico/index.md`",
            "",
            "## Criterios de verificabilidad",
            "",
        ]
    )
    for item in wiki["politica"]["criterios_verificabilidad"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)

def build_sistema_page(section: dict, generated_at: str, notice: str) -> str:
    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    publicacion = load_yaml_json("00_sistema_tesis/config/publicacion.yaml")
    tesista = load_yaml_json("00_sistema_tesis/config/tesista.json")["tesista"]
    canonical = canonical_file_status()
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation("sistema"))
    lines.extend(render_origin_block("sistema", section["fuentes"]))
    lines.extend(
        [
            "## Identidad del proyecto",
            "",
            f"- ID: `{sistema['identidad_proyecto']['id']}`",
            f"- Nombre corto: {sistema['identidad_proyecto']['nombre_corto']}",
            f"- Programa: {sistema['identidad_proyecto']['programa']}",
            f"- Línea de investigación: {sistema['identidad_proyecto']['linea_investigacion']}",
            "",
            "## Verificación de identidad humana",
            "",
            f"- Tesista: `{tesista['nombre_completo']}`",
            f"- CURP (único registro en wiki): `{tesista.get('curp', 'no_configurada')}`",
            "",
            "## Estado operativo",
            "",
            f"- Versión: `{sistema['version']}`",
            f"- Estado global: `{sistema['estado_global']}`",
            f"- Bloque activo: `{sistema['bloque_activo']}`",
            f"- Fase actual: `{sistema['fase_actual']}`",
            f"- Siguiente entregable: `{sistema['siguiente_entregable']}`",
            "",
            "## Arquitectura base",
            "",
            f"- Patrón general: `{sistema['arquitectura_base']['patron_general']}`",
            f"- Formatos fuente: {', '.join(f'`{item}`' for item in sistema['arquitectura_base']['formatos_fuente'])}",
            f"- Formatos derivados: {', '.join(f'`{item}`' for item in sistema['arquitectura_base']['formatos_derivados'])}",
            f"- Criterio de bajo rozamiento: {sistema['arquitectura_base']['criterio_bajo_rozamiento']}",
            "",
            "## Narrativa del sistema",
            "",
        ]
    )
    lines.extend(render_markdown_fragment("00_sistema_tesis/documentacion_sistema/proposito_y_alcance.md", demote_by=1))
    lines.extend(render_markdown_fragment("00_sistema_tesis/documentacion_sistema/mapa_de_modulos.md", demote_by=1))
    lines.extend(render_markdown_fragment("00_sistema_tesis/documentacion_sistema/flujos_operativos.md", demote_by=1))
    lines.extend(render_markdown_fragment("00_sistema_tesis/documentacion_sistema/interaccion_por_actor.md", demote_by=1))
    lines.extend(
        [
            "## Mapa rápido de términos e IDs",
            "",
            "- `VAL_STEP_{nnn}`: familia de validación o instrucción humana crítica trazada en canon.",
            "- `EVT_{nnnn}`: familia de evento canónico general, por ejemplo evidencia fuente.",
            "- `DEC-{nnnn}`: decisión formal.",
            "- `T-{nnn}`, `R-{nnn}`, `ENT-{nnn}`, `B{n}`, `F{n}`: planeación, riesgo, entregable, bloque y fase.",
            "- Si un término o ID no es evidente, la referencia central es `glosario_terminologia_y_convenciones.md`.",
            "",
            "## Terminología de evidencia e ingestión",
            "",
            "- `paquete`: conjunto versionado de contexto o evidencia a integrar.",
            "- `staging`: zona temporal de verificación antes de integrar al canon.",
            "- `indice maestro`: registro consolidado de ingreso y destino de artefactos.",
            "- `evidencia`, `soporte`, `politica`, `modulo`, `rol`, `nivel`, `estado`, `accion`: etiquetas de clasificación que no deben confundirse entre sí.",
            "",
        ]
    )
    lines.extend(
        [
            "## Operación humana y superficies",
            "",
            "- **Superficie privada:** canon, backlog, decisiones, bitácora, auditoría y evidencia íntegra.",
            "- **Superficie pública:** bundle sanitizado en `06_dashboard/publico/`, siempre derivado y no editable a mano.",
            "- **Ruta humana principal:** `00_sistema_tesis/manual_operacion_humana.md`.",
            "- **IA opcional:** ningún flujo crítico depende de IA para ejecutarse.",
            f"- **Aviso público:** {publicacion['politica']['aviso_no_editar']}",
            "",
            "## Estado de archivos canónicos",
            "",
        ]
    )
    lines.extend(
        render_table(
            ["Clave", "Ruta", "Existe", "Última modificación"],
            [
                [item["clave"], item["ruta"], "sí" if item["existe"] else "no", item["modificado"]]
                for item in canonical
            ],
        )
    )
    return "\n".join(lines)

def build_gobernanza_page(section: dict, generated_at: str, notice: str) -> str:
    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    ia = load_yaml_json("00_sistema_tesis/config/ia_gobernanza.yaml")
    publicacion = load_yaml_json("00_sistema_tesis/config/publicacion.yaml")
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation("gobernanza"))
    lines.extend(render_origin_block("gobernanza", section["fuentes"]))
    lines.extend(
        [
            "## Qué resuelve este subsistema",
            "",
            "- Evita que la asistencia con IA o la automatización se presenten como autoridad final.",
            "- Obliga a distinguir entre confirmación humana, evidencia fuerte y artefacto derivado.",
            "- Mantiene visible qué reglas aplican en privado y qué puede explicarse en público.",
            "",
        ]
    )
    lines.extend(["## Políticas del sistema", ""])
    for item in sistema["politicas_sistema"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Principios de gobernanza de IA", ""])
    for item in ia["principios"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Vocabulario de gobernanza y trazabilidad",
            "",
            "- `validación humana`: acto humano trazado que autoriza o confirma un cambio relevante.",
            "- `evidencia fuente`: soporte de conversación que respalda un `VAL-STEP` nuevo cuando aplica enforcement.",
            "- `source_event_id`: enlace desde una validación humana hacia la evidencia de conversación registrada.",
            "- `human_validation.confirmation_text`: texto exacto de la confirmación humana en el canon.",
            "- `enforcement`: regla obligatoria que el sistema no trata como sugerencia opcional.",
            "",
        ]
    )
    lines.extend(["", "## Política TDD operativa", ""])
    for item in ia["principios_tdd"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Flujo TDD obligatorio", ""])
    for item in ia["flujo_tdd_operativo"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Regla de operación humana",
            "",
            "- Todo flujo crítico debe tener vía manual explícita y legible para el tesista y terceros humanos.",
            "- La IA es opcional como asistencia y nunca sustituye validación, criterio metodológico ni publicación responsable.",
            "- La exposición pública solo ocurre mediante sanitización reproducible desde la base privada.",
            f"- Bundle público: `{publicacion['salida']['directorio']}`",
            "",
            "## Límites de la capa pública",
            "",
            "- La parte pública sirve para explorar y evaluar el sistema, no para sustituir el canon privado.",
            "- El ledger detallado, la matriz interna completa, las transcripciones y la evidencia fuente permanecen fuera de la superficie pública.",
            "- La arquitectura IoT se describe hasta el marco canónico vigente; los pendientes abiertos deben mostrarse como pendientes y no como diseño cerrado.",
        ]
    )
    lines.append("")
    return "\n".join(lines)

def build_terminologia_page(section: dict, generated_at: str, notice: str) -> str:
    naming = load_yaml_json("00_sistema_tesis/03_metadatos/sistema_operativo_tesis_iot__convencion_de_nombres__v09.json")
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation("terminologia"))
    lines.extend(render_origin_block("terminologia", section["fuentes"]))
    lines.extend(
        [
            "## Lectura rápida",
            "",
            "- Esta página es la referencia central para términos, familias de IDs y convenciones de nombre.",
            "- La capa privada puede mostrar ejemplos concretos como `VAL-STEP-530` o `EVT-0053`.",
            "- La capa pública explica la misma semántica usando formas seguras como `VAL_STEP_{nnn}` y `EVT_{nnnn}`.",
            "",
            "## Familias de IDs más usadas",
            "",
        ]
    )
    lines.extend(
        render_table(
            ["Familia", "Qué representa", "Fuente principal"],
            [
                ["`VAL_STEP_{nnn}`", "Validación humana o instrucción crítica trazada", "`events.jsonl` + ledger/matriz"],
                ["`EVT_{nnnn}`", "Evento canónico general", "`events.jsonl`"],
                ["`DEC-{nnnn}`", "Decisión formal", "`00_sistema_tesis/decisiones/`"],
                ["`T-{nnn}`", "Tarea del backlog", "`backlog.csv`"],
                ["`R-{nnn}`", "Riesgo", "`riesgos.csv`"],
                ["`ENT-{nnn}`", "Entregable", "`entregables.csv`"],
                ["`B{n}`", "Bloque macro", "`bloques.yaml`"],
                ["`F{n}`", "Fase del roadmap", "`roadmap.csv`"],
            ],
        )
    )
    lines.extend(
        [
            "## Convención de nombres de evidencia ingerida",
            "",
            f"- Objetivo: {naming['naming_objective']}",
            f"- Patrón base: `{naming['pattern']}`",
            "",
            "### Reglas activas",
            "",
        ]
    )
    for item in naming["rules"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Glosario canónico", ""])
    lines.extend(render_markdown_fragment("00_sistema_tesis/documentacion_sistema/glosario_terminologia_y_convenciones.md", demote_by=1))
    return "\n".join(lines)

def build_hipotesis_page(section: dict, generated_at: str, notice: str) -> str:
    hipotesis = load_yaml_json("00_sistema_tesis/config/hipotesis.yaml")["hipotesis"]
    criticas = [item for item in hipotesis if item["prioridad"] == "critica"]
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation("hipotesis"))
    lines.extend(render_origin_block("hipotesis", section["fuentes"]))
    lines.extend(
        [
            "## Qué resuelve este subsistema",
            "",
            "- Convierte el objetivo general de la tesis en afirmaciones contrastables.",
            "- Vincula cada hipótesis con bloques de trabajo, criterios de soporte y futura evidencia.",
            "- Evita que la narrativa técnica crezca sin criterios explícitos de validación o rechazo.",
            "",
            "## Lectura rápida",
            "",
            f"- Hipótesis activas: `{len(hipotesis)}`",
            f"- Hipótesis de prioridad crítica: `{len(criticas)}`",
            "- Esta página describe hipótesis vigentes, no resultados ya confirmados.",
            "",
        ]
    )
    
    # Agregar Diagrama Mermaid de Hipótesis
    lines.extend([
        "## Mapa de Hipótesis",
        "",
        "```mermaid",
        "graph TD",
    ])
    for item in hipotesis:
        # Simplificamos conexiones si hay bloques asociados
        for bloque in item["bloques_asociados"][:2]:
            lines.append(f"  {item['id']} --> {bloque}")
        lines.append(f"  style {item['id']} fill:#f9f,stroke:#333,stroke-width:2px")
    lines.extend([
        "```",
        "",
        "## Hipótesis activas",
        ""
    ])
    lines.extend(
        render_table(
            ["ID", "Nombre", "Prioridad", "Estado", "Bloques", "Criterio de soporte"],
            [
                [
                    item["id"],
                    item["nombre_corto"],
                    item["prioridad"],
                    item["estado"],
                    ", ".join(item["bloques_asociados"]),
                    item["criterio_de_soporte"],
                ]
                for item in hipotesis
            ],
        )
    )
    return "\n".join(lines)

def build_bloques_page(section: dict, generated_at: str, notice: str) -> str:
    bloques = load_yaml_json("00_sistema_tesis/config/bloques.yaml")["bloques"]
    activos = [item for item in bloques if item["estado"] == "activo"]
    no_iniciados = [item for item in bloques if item["estado"] == "no_iniciado"]
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation("bloques"))
    lines.extend(render_origin_block("bloques", section["fuentes"]))
    lines.extend(
        [
            "## Qué resuelve este subsistema",
            "",
            "- Ordena la tesis como una secuencia de bloques mayores con dependencias explícitas.",
            "- Permite distinguir qué parte del sistema está activa, cuál depende de otra y cuál sigue pendiente.",
            "- Sirve como puente entre gobernanza macro y backlog operativo detallado.",
            "",
            "## Lectura rápida",
            "",
            f"- Bloques activos: `{len(activos)}`",
            f"- Bloques no iniciados: `{len(no_iniciados)}`",
            "- Un bloque no se interpreta como completado solo por existir en la estructura; depende de su criterio de salida.",
            "",
        ]
    )

    # Agregar Diagrama Mermaid de Bloques
    lines.extend([
        "## Grafo de Dependencias",
        "",
        "```mermaid",
        "graph LR",
    ])
    for item in bloques:
        for dep in item["dependencias"]:
            if dep:
                lines.append(f"  {dep} --> {item['id']}")
        # Color según estado
        if item["estado"] == "hecho":
            lines.append(f"  style {item['id']} fill:#9f9,stroke:#333")
        elif item["estado"] == "activo":
            lines.append(f"  style {item['id']} fill:#ff9,stroke:#333")
    lines.extend([
        "```",
        "",
        "## Bloques del sistema",
        ""
    ])
    lines.extend(
        render_table(
            ["ID", "Nombre", "Estado", "Prioridad", "Dependencias", "Criterio de salida"],
            [
                [
                    item["id"],
                    item["nombre"],
                    item["estado"],
                    item["prioridad"],
                    ", ".join(item["dependencias"]) or "ninguna",
                    item["criterio_salida"],
                ]
                for item in bloques
            ],
        )
    )
    return "\n".join(lines)

def build_planeacion_page(section: dict, generated_at: str, notice: str) -> str:
    backlog = load_csv_rows("01_planeacion/backlog.csv")
    riesgos = load_csv_rows("01_planeacion/riesgos.csv")
    entregables = load_csv_rows("01_planeacion/entregables.csv")
    backlog_activo = [item for item in backlog if item["estado"] in {"pendiente", "en_progreso"}]
    riesgos_abiertos = [item for item in riesgos if str(item.get("estado", "")).strip() == "abierto"]
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    entregables = load_csv_rows("01_planeacion/entregables.csv")
    roadmap_raw = load_csv_rows("01_planeacion/roadmap.csv")
    
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation("planeacion"))
    lines.extend(render_origin_block("planeacion", section["fuentes"]))
    lines.extend(
        [
            "## Qué resuelve este subsistema",
            "",
            "- Traduce la estrategia de tesis en trabajo secuenciado, riesgos visibles y entregables verificables.",
            "- Permite entender qué sigue, qué amenaza el avance y qué artefacto representa cada salida mayor.",
            "- Hace explícita la diferencia entre estructura de bloques y ejecución operativa concreta.",
            "",
            "## Lectura rápida",
            "",
            f"- Tareas pendientes o en progreso: `{len(backlog_activo)}`",
            f"- Riesgos abiertos: `{len(riesgos_abiertos)}`",
            f"- Entregables definidos: `{len(entregables)}`",
            "",
            "## Convenciones de planeación",
            "",
            "- `B{n}`: bloque macro del sistema o de la tesis.",
            "- `T-{nnn}`: tarea concreta del backlog.",
            "- `R-{nnn}`: riesgo registrado.",
            "- `ENT-{nnn}`: entregable mayor.",
            "- `F{n}`: fase del roadmap.",
            "- El detalle normativo completo se resume en la página de terminología y en `backlog_guia.md`.",
            "",
        ]
    )
    
    # Agregar Diagrama Gantt de Roadmap
    lines.extend([
        "## Visualización del Cronograma",
        "",
        "```mermaid",
        "gantt",
        "    title Hoja de Ruta de la Tesis",
        "    dateFormat  YYYY-MM-DD",
        "    section Fases",
    ])
    for item in roadmap_raw:
        # Parsear "2026-03-23 a 2026-03-31"
        try:
            parts = item["periodo_tentativo"].split(" a ")
            start = parts[0].strip()
            end = parts[1].strip()
            lines.append(f"    {item['fase_id']} : {start}, {end}")
        except:
            continue
    
    lines.extend([
        "```",
        "",
        "## Backlog prioritario",
        ""
    ])
    lines.extend(
        render_table(
            ["Task", "Bloque", "Tarea", "Prioridad", "Estado", "Fecha objetivo"],
            [
                [
                    item["task_id"],
                    item["bloque"],
                    item["tarea"],
                    item["prioridad"],
                    item["estado"],
                    item["fecha_objetivo"],
                ]
                for item in backlog[:10]
            ],
        )
    )
    lines.extend(["## Riesgos abiertos", ""])
    lines.extend(
        render_table(
            ["Risk", "Riesgo", "Probabilidad", "Impacto", "Estado"],
            [
                [
                    item["risk_id"],
                    item["riesgo"],
                    item["probabilidad"],
                    item["impacto"],
                    item["estado"],
                ]
                for item in riesgos
            ],
        )
    )
    lines.extend(["## Entregables", ""])
    lines.extend(
        render_table(
            ["ID", "Nombre", "Estado", "Artefacto canónico"],
            [
                [
                    item["deliverable_id"],
                    item["nombre"],
                    item["estado"],
                    item["artefacto_canonico"],
                ]
                for item in entregables
            ],
        )
    )
    return "\n".join(lines)

def build_decisiones_page(section: dict, generated_at: str, notice: str) -> str:
    entries = list_markdown_entries("00_sistema_tesis/decisiones")
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation("decisiones"))
    lines.extend(render_origin_block("decisiones", section["fuentes"]))
    lines.extend(
        [
            "## Qué resuelve este subsistema",
            "",
            "- Conserva decisiones de arquitectura, método y operación como piezas defendibles y fechadas.",
            "- Evita que cambios estructurales queden solo en conversaciones o commits sin narrativa.",
            "- Se interpreta como registro de criterio, no como lista genérica de notas.",
            "",
        ]
    )
    if not entries:
        lines.extend(["## Estado", "", "Sin decisiones registradas aún.", ""])
        return "\n".join(lines)
    lines.extend(["## Decisiones registradas", ""])
    for item in entries:
        lines.append(f"- `{item['fecha']}` [{item['titulo']}]({repo_link_from_wiki(item['archivo'])})")
    lines.append("")
    return "\n".join(lines)

def build_bitacora_page(section: dict, generated_at: str, notice: str) -> str:
    bitacoras = list_markdown_entries("00_sistema_tesis/bitacora")
    bitacoras = [item for item in bitacoras if not item["archivo"].endswith("log_sesiones_trabajo_registradas.md")]
    reportes = list_markdown_entries("00_sistema_tesis/reportes_semanales")
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation("bitacora"))
    lines.extend(render_origin_block("bitacora", section["fuentes"]))
    lines.extend(
        [
            "## Qué resuelve este subsistema",
            "",
            "- Conserva el trabajo de sesión, aprendizaje operativo y continuidad entre conversaciones.",
            "- Permite distinguir entre evidencia de trabajo, cierre operativo y validación humana formal.",
            "- Complementa decisiones y planeación, pero no las sustituye.",
            "",
        ]
    )
    lines.extend(
        [
            "## Bitácoras",
            "",
            "Las entradas están agrupadas por año-mes y comprimidas en acordeones para facilitar lectura rápida.",
            "Abre solo la bitácora que necesites y usa el enlace de archivo para navegar al registro completo.",
            "",
        ]
    )
    if bitacoras:
        grouped: dict[str, list[dict]] = {}
        for item in bitacoras:
            bucket = _month_bucket_from_date(item["fecha"])
            grouped.setdefault(bucket, []).append(item)

        ordered_buckets = sorted(grouped.keys(), key=_month_bucket_sort_key, reverse=True)
        for bucket in ordered_buckets:
            bucket_title = bucket if bucket != "sin-fecha" else "Índices maestros"
            lines.extend([f"### {bucket_title}", ""])
            if bucket == "sin-fecha":
                lines.extend(
                    [
                        "Documentos de referencia vivos (matriz, índices y propuestas) que no representan una sesión fechada.",
                        "",
                    ]
                )
            for item in grouped[bucket]:
                display_date = item["fecha"] if _is_iso_date(item["fecha"]) else "Índice maestro"
                details_title = _safe_details_title(f"{display_date} - {item['titulo']}")
                lines.append(f'??? "{details_title}"')
                lines.append("")
                lines.append(f"    **Archivo completo:** [{item['archivo']}]({repo_link_from_wiki(item['archivo'])})")
                lines.append("")
                lines.append("    **Resumen breve**")
                lines.append("")
                for excerpt_line in _extract_markdown_summary(item["archivo"]):
                    lines.append(f"    - {excerpt_line}")
                lines.append("")

        lines.extend(_render_ledger_monthly_summary())
    else:
        lines.append("Sin bitácoras registradas aún.")
    lines.extend(["", "## Reportes semanales", ""])
    if reportes:
        for item in reportes:
            lines.append(f"- `{item['fecha']}` [{item['titulo']}]({repo_link_from_wiki(item['archivo'])})")
    else:
        lines.append("Sin reportes semanales registrados aún.")
    lines.append("")
    return "\n".join(lines)

def build_coverage_page(section: dict, generated_at: str, notice: str) -> str:
    status = directory_markdown_status(section["fuentes"][0])
    section_id = str(section["id"])
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation(section_id))
    lines.extend(render_origin_block(section_id, section["fuentes"]))
    lines.extend(
        [
            "## Cómo leer esta cobertura",
            "",
            "- Esta página no inventa contenido faltante.",
            "- Solo reporta si la ruta existe y si ya contiene material operativo utilizable.",
            "- El objetivo es mostrar madurez real del subsistema, no una promesa editorial.",
            "",
        ]
    )
    lines.extend(
        [
            "## Estado de cobertura",
            "",
            f"- Ruta: `{status['relative_dir']}`",
            f"- Existe: `{'sí' if status['exists'] else 'no'}`",
        ]
    )
    if not status["has_operational_content"]:
        lines.extend(
            [
                "- Cobertura: `pendiente`",
                "- Mensaje: Sin contenido operativo aún. La wiki refleja el estado real del repositorio y no inventa artefactos.",
                "",
            ]
        )
        return "\n".join(lines)

    lines.extend(
        [
            "- Cobertura: `parcial_o_activa`",
            "",
            "## Archivos detectados",
            "",
        ]
    )
    for item in status["non_keep_files"]:
        lines.append(f"- `{item}`")
    lines.append("")
    return "\n".join(lines)

def build_casos_uso_page(section: dict, generated_at: str, notice: str) -> str:
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation("casos_uso"))
    lines.extend(render_origin_block("casos_uso", section["fuentes"]))
    lines.extend(render_markdown_fragment("00_sistema_tesis/documentacion_sistema/casos_uso_agente.md", demote_by=0))
    lines.append("---")
    lines.extend(render_markdown_fragment("00_sistema_tesis/documentacion_sistema/guias_tareas_agente.md", demote_by=0))
    return "\n".join(lines)

def build_arquitectura_page(section: dict, generated_at: str, notice: str) -> str:
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(render_page_navigation("arquitectura"))
    lines.extend(render_origin_block("arquitectura", section["fuentes"]))
    
    for source in section["fuentes"]:
        if (ROOT / source).is_file():
            lines.extend(render_markdown_fragment(source, demote_by=0))
            lines.append("\n---\n")
            
    return "\n".join(lines)

SECTION_BUILDERS = {
    "casos_uso": build_casos_uso_page,
    "sistema": build_sistema_page,
    "gobernanza": build_gobernanza_page,
    "arquitectura": build_arquitectura_page,
    "terminologia": build_terminologia_page,
    "hipotesis": build_hipotesis_page,
    "bloques": build_bloques_page,
    "planeacion": build_planeacion_page,
    "decisiones": build_decisiones_page,
    "bitacora": build_bitacora_page,
    "experimentos": build_coverage_page,
    "implementacion": build_coverage_page,
    "tesis": build_coverage_page,
}

def render_markdown_to_html(markdown_text: str) -> str:
    """Conversión simple de markdown a HTML sin dependencias externas."""
    # Preservar bloques de código antes de escapar
    code_blocks = []
    def save_code_block(match):
        lang, content = match.groups()
        code_blocks.append((lang, content))
        return f"<!--CODE_BLOCK_{len(code_blocks)-1}-->"
    
    # Manejar bloques de código con triple backtick
    text = re.sub(r'```([a-z]*)\n(.*?)\n```', save_code_block, markdown_text, flags=re.DOTALL)
    
    html = escape(text)
    
    # Headers
    html = re.sub(r'^# (.*)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
    html = re.sub(r'^## (.*)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
    html = re.sub(r'^### (.*)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)

    # Admonitions MkDocs style (!!! type "Title")
    html = re.sub(
        r'!!! (success|warning|danger) "([^"]+)"\n\s+(.*)',
        r'<div class="admonition \1"><p class="admonition-title">\2</p><p>\3</p></div>',
        html,
        flags=re.MULTILINE
    )
    
    # Bold / Italic
    html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
    
    # Inline code
    html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
    
    # Links [label](href.md) -> [label](href.html)
    def link_repl(match):
        label, href = match.groups()
        # Si el enlace es externo, no tocar
        if href.startswith(SKIP_LINK_PREFIXES):
            return f'<a href="{href}">{label}</a>'
            
        # Si el enlace apunta a otra página de la wiki (están en el mismo nivel)
        is_wiki_page = any(href == f"{pid}.md" or href == f"{pid}.html" for pid in SECTION_IDS) or href == "index.md" or href == "index.html"
        
        if is_wiki_page:
            if href.endswith(".md"):
                href = href[:-3] + ".html"
        else:
            # Si no es una página de la wiki, probablemente es un archivo del repo
            # Como estamos en generado/wiki/, necesitamos un nivel extra de ../ si el link original ya usaba ../
            if href.startswith("../"):
                href = "../" + href
        
        return f'<a href="{href}">{label}</a>'
    
    html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', link_repl, html)
    
    # Lists
    html = re.sub(r'^\s*-\s+(.*)$', r'<li>\1</li>', html, flags=re.MULTILINE)
    # Wrap li in ul (simplified)
    html = re.sub(r'((?:<li>.*</li>\n?)+)', r'<ul>\1</ul>', html)
    
    # Restore code blocks
    for i, (lang, content) in enumerate(code_blocks):
        if lang == "mermaid":
            replacement = f'<div class="mermaid-container"><pre class="mermaid">{escape(content)}</pre></div>'
        else:
            replacement = f'<pre><code class="language-{lang}">{escape(content)}</code></pre>'
        html = html.replace(f"&lt;!--CODE_BLOCK_{i}--&gt;", replacement)

    # Newlines to paragraphs
    html = html.replace('\n\n', '</p><p>')
    
    return f'<div class="markdown-body"><p>{html}</p></div>'

def render_html_page(title: str, markdown_content: str, generated_at: str, current_page_id: str = "") -> str:
    rendered_body = render_markdown_to_html(markdown_content)
    
    # Navigation Sidebar
    nav_links = []
    for page_id in PAGE_ORDER:
        active_class = "active" if page_id == current_page_id else ""
        icon = PAGE_ICONS.get(page_id, "description")
        nav_links.append(
            f'<a href="{page_id}.html" class="nav-link {active_class}">'
            f'<span class="material-icons">{icon}</span>'
            f'<span>{PAGE_TITLES[page_id]}</span>'
            '</a>'
        )
    
    sidebar_nav = "\n".join(nav_links)

    return f"""<!DOCTYPE html>
<html lang="es-MX">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)} | Tesis OS Wiki</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Outfit:wght@500;700&family=Fira+Code&family=Material+Icons&display=swap" rel="stylesheet">
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'neutral' }});
  </script>
  <style>
    :root {{
      --primary: #0f766e;
      --primary-light: #14b8a6;
      --secondary: #1e293b;
      --accent: #06b6d4;
      --bg: #f8fafc;
      --surface: rgba(255, 255, 255, 0.85);
      --border: rgba(226, 232, 240, 0.8);
      --text: #1e293b;
      --text-muted: #64748b;
      --radius: 12px;
      --shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
    }}

    * {{ box-sizing: border-box; }}

    body {{
      margin: 0;
      background: var(--bg);
      background-image: 
        radial-gradient(at 0% 0%, rgba(15, 118, 110, 0.05) 0px, transparent 50%),
        radial-gradient(at 100% 0%, rgba(6, 182, 212, 0.05) 0px, transparent 50%);
      color: var(--text);
      font-family: 'Inter', system-ui, sans-serif;
      display: flex;
      min-height: 100vh;
    }}

    /* Sidebar Navigation */
    nav {{
      width: 260px;
      background: var(--surface);
      backdrop-filter: blur(12px);
      border-right: 1px solid var(--border);
      padding: 2rem 1rem;
      position: sticky;
      top: 0;
      height: 100vh;
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      z-index: 100;
    }}

    .nav-header {{
      padding: 0 0.75rem 1.5rem;
      font-family: 'Outfit', sans-serif;
      font-weight: 700;
      font-size: 1.25rem;
      color: var(--primary);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }}

    .nav-link {{
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.75rem 1rem;
      text-decoration: none;
      color: var(--text-muted);
      border-radius: var(--radius);
      transition: all 0.2s ease;
      font-weight: 500;
    }}

    .nav-link:hover {{
      background: rgba(15, 118, 110, 0.08);
      color: var(--primary);
      transform: translateX(4px);
    }}

    .nav-link.active {{
      background: var(--primary);
      color: white;
      box-shadow: var(--shadow);
    }}

    .nav-link .material-icons {{
      font-size: 20px;
    }}

    /* Main Content Area */
    main {{
      flex: 1;
      padding: 3rem 4rem;
      max-width: 1000px;
      margin: 0 auto;
    }}

    header {{
      margin-bottom: 3rem;
      animation: fadeInDown 0.6s ease-out;
    }}

    @keyframes fadeInDown {{
      from {{ opacity: 0; transform: translateY(-20px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    h1 {{
      font-family: 'Outfit', sans-serif;
      font-size: 3rem;
      margin: 0 0 0.5rem;
      background: linear-gradient(135deg, var(--secondary) 0%, var(--primary) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      letter-spacing: -0.02em;
    }}

    .stamp {{
      color: var(--text-muted);
      font-size: 0.875rem;
      display: flex;
      align-items: center;
      gap: 0.4rem;
    }}

    /* Markdown Rendering Styles */
    .markdown-body {{
      line-height: 1.7;
      font-size: 1.05rem;
    }}

    .markdown-body h2 {{
      font-family: 'Outfit', sans-serif;
      margin: 2.5rem 0 1rem;
      padding-bottom: 0.5rem;
      border-bottom: 2px solid var(--border);
      color: var(--secondary);
    }}

    .markdown-body p {{ margin-bottom: 1.25rem; }}

    .markdown-body code {{
      background: rgba(15, 118, 110, 0.08);
      padding: 0.2rem 0.4rem;
      border-radius: 6px;
      font-family: 'Fira Code', monospace;
      font-size: 0.9em;
      color: var(--primary);
    }}

    .markdown-body a {{
      color: var(--primary);
      text-decoration: none;
      border-bottom: 1px solid transparent;
      transition: border-color 0.2s;
    }}

    .markdown-body a:hover {{
      border-bottom-color: var(--primary);
    }}

    .markdown-body ul {{
      padding-left: 1.5rem;
      margin-bottom: 1.5rem;
    }}

    .markdown-body li {{
      margin-bottom: 0.5rem;
    }}

    /* Admonitions */
    .admonition {{
      margin: 1.5rem 0;
      padding: 1.25rem;
      border-radius: var(--radius);
      border-left: 4px solid #ccc;
      background: white;
      box-shadow: var(--shadow);
    }}
    .admonition.success {{ border-left-color: #10b981; background: #ecfdf5; }}
    .admonition.warning {{ border-left-color: #f59e0b; background: #fffbeb; }}
    .admonition.danger {{ border-left-color: #ef4444; background: #fef2f2; }}
    
    .admonition-title {{
      font-weight: 700;
      margin-bottom: 0.5rem;
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.05em;
    }}

    @media (max-width: 768px) {{
      body {{ flex-direction: column; }}
      nav {{
        width: 100%;
        height: auto;
        position: relative;
        flex-direction: row;
        overflow-x: auto;
        padding: 1rem;
      }}
      .nav-header {{ display: none; }}
      main {{ padding: 2rem 1.5rem; }}
      h1 {{ font-size: 2.2rem; }}
    }}
  </style>
</head>
<body>
  <nav>
    <div class="nav-header">
      <span class="material-icons">architecture</span>
      Tesis OS
    </div>
    {sidebar_nav}
  </nav>
  <main>
    <header>
      <h1>{escape(title)}</h1>
      <div class="stamp">
        <span class="material-icons" style="font-size: 16px;">update</span>
        Generado el {escape(generated_at)}
      </div>
    </header>
    {rendered_body}
  </main>
</body>
</html>
"""

def build_wiki() -> dict:
    wiki = load_yaml_json("00_sistema_tesis/config/wiki.yaml")
    sign_off_data = load_yaml_json("00_sistema_tesis/config/sign_offs.json")
    sign_offs = sign_off_data.get("sign_offs", [])

    markdown_dir = ensure_directory(wiki["salida"]["markdown_dir"])
    html_dir = ensure_directory(wiki["salida"]["html_dir"])
    source_paths = list(dict.fromkeys(wiki["fuentes_base"] + [source for section in wiki["secciones"] for source in section["fuentes"]]))
    generated_at = stable_generated_at(source_paths)
    notice = wiki["politica"]["aviso_no_editar"]
    page_records: list[dict] = []

    for section in wiki["secciones"]:
        page_id = section["id"]
        builder = SECTION_BUILDERS[page_id]
        markdown_content = builder(section, generated_at, notice)
        is_verified = False
        if len(section["fuentes"]) == 1:
            source_rel = section["fuentes"][0]
            if (ROOT / source_rel).is_file():
                current_hash = file_sha256(source_rel)
                badge = get_sign_off_badge(source_rel, current_hash, sign_offs)
                markdown_content = badge + "\n" + markdown_content
                # Determinar si está verificado para la métrica
                is_verified = any(s["archivo"] == source_rel and s["hash_verificado"] == current_hash for s in sign_offs)

        markdown_path = markdown_dir / f"{page_id}.md"
        write_text_if_changed(markdown_path, markdown_content + "\n")

        html_content = render_html_page(section["titulo"], markdown_content, generated_at, current_page_id=page_id)
        html_path = html_dir / f"{page_id}.html"
        write_text_if_changed(html_path, html_content)

        page_records.append(
            {
                "id": page_id,
                "title": section["titulo"],
                "markdown": str(markdown_path.relative_to(ROOT)).replace("\\", "/"),
                "html": str(html_path.relative_to(ROOT)).replace("\\", "/"),
                "sources": section["fuentes"],
                "verified": is_verified
            }
        )

    index_content = render_index_page(wiki, page_records, generated_at)
    index_path = markdown_dir / "index.md"
    write_text_if_changed(index_path, index_content + "\n")
    index_html_path = html_dir / "index.html"
    write_text_if_changed(index_html_path, render_html_page("Wiki verificable", index_content, generated_at, current_page_id="index"))

    page_names = ["index"] + [item["id"] for item in page_records]
    manifest = {
        "generated_at": generated_at,
        "verification": {
            "status": "ok",
            "required_page_fields": REQUIRED_PAGE_FIELDS,
        },
        "pages": page_names,
        "page_records": page_records,
        "sources": [
            {
                "path": path,
                "sha256": file_sha256(path) if (ROOT / path).is_file() else None,
                "modified": path_timestamp(path),
                "kind": "file" if (ROOT / path).is_file() else "directory",
            }
            for path in wiki["fuentes_base"]
        ],
    }
    dump_json(wiki["salida"]["manifest"], manifest)
    return {
        "generated_at": generated_at,
        "verification_status": "ok",
        "pages": page_names,
    }

def main() -> int:
    result = build_wiki()
    print(f"Wiki Markdown generada en: {ROOT / '06_dashboard' / 'wiki'}")
    print(f"Wiki HTML generada en: {ROOT / '06_dashboard' / 'generado' / 'wiki'}")
    print(f"Manifest generado en: {ROOT / '06_dashboard' / 'generado' / 'wiki_manifest.json'}")
    print(f"Estado de verificación: {result['verification_status']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())

