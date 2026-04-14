from __future__ import annotations

from html import escape
from pathlib import Path
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
    "sistema",
    "gobernanza",
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
    "sistema",
    "gobernanza",
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
    "sistema": "Sistema",
    "gobernanza": "Gobernanza",
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
    "sistema": ["gobernanza", "terminologia", "planeacion"],
    "gobernanza": ["sistema", "terminologia", "bitacora"],
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
            "- Si necesitas trazabilidad operativa interna, consulta `00_sistema_tesis/bitacora/matriz_trazabilidad.md` y `00_sistema_tesis/bitacora/log_conversaciones_ia.md`.",
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
            "- Evita que la IA o la automatización se presenten como autoridad final.",
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
            "- La IA es opcional y nunca sustituye validación, criterio metodológico ni publicación responsable.",
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
    bitacoras = [item for item in bitacoras if not item["archivo"].endswith("log_conversaciones_ia.md")]
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
            bucket_title = bucket if bucket != "sin-fecha" else "Sin fecha"
            lines.extend([f"### {bucket_title}", ""])
            for item in grouped[bucket]:
                display_date = item["fecha"] if _is_iso_date(item["fecha"]) else "Sin fecha"
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

        lines.extend(["## Bitácora de Conversaciones IA", ""])
        lines.append('??? "Mostrar contenido completo"')
        lines.append("")
        lines.extend(_indent_markdown_block(render_markdown_fragment("00_sistema_tesis/bitacora/log_conversaciones_ia.md", demote_by=1)))
        lines.append("")
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


SECTION_BUILDERS = {
    "sistema": build_sistema_page,
    "gobernanza": build_gobernanza_page,
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


def render_html_page(title: str, markdown_content: str, generated_at: str) -> str:
    body = escape(markdown_content)
    return f"""<!DOCTYPE html>
<html lang="es-MX">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    body {{
      margin: 0;
      background: #f6f3eb;
      color: #1e293b;
      font-family: Georgia, "Times New Roman", serif;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 2rem 1.25rem 3rem;
    }}
    header {{
      margin-bottom: 1.5rem;
    }}
    h1 {{
      margin: 0 0 0.5rem;
      font-size: clamp(1.8rem, 3vw, 2.8rem);
    }}
    .stamp {{
      color: #475569;
      font-family: "Segoe UI", Tahoma, sans-serif;
      font-size: 0.9rem;
    }}
    pre {{
      white-space: pre-wrap;
      background: #fff;
      border: 1px solid #d6d3d1;
      border-radius: 16px;
      padding: 1rem;
      overflow-wrap: anywhere;
      line-height: 1.55;
    }}
    a {{
      color: #0f766e;
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>{escape(title)}</h1>
      <p class="stamp">Artefacto derivado generado el {escape(generated_at)}</p>
    </header>
    <pre>{body}</pre>
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

        html_content = render_html_page(section["titulo"], markdown_content, generated_at)
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
    write_text_if_changed(index_html_path, render_html_page("Wiki verificable", index_content, generated_at))

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
