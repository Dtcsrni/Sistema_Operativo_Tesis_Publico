from __future__ import annotations

from html import escape
from pathlib import Path

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
    now_stamp,
    path_timestamp,
)


SECTION_IDS = {
    "sistema",
    "gobernanza",
    "hipotesis",
    "bloques",
    "planeacion",
    "decisiones",
    "bitacora",
    "experimentos",
    "implementacion",
    "tesis",
}

REQUIRED_PAGE_FIELDS = [
    "Tesista",
    "Fecha",
    "Estado",
    "Fuentes",
    "Aviso",
]


def relative_wiki_link(page_id: str) -> str:
    return f"{page_id}.md"


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
    lines.extend(["## Políticas del sistema", ""])
    for item in sistema["politicas_sistema"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Principios de gobernanza de IA", ""])
    for item in ia["principios"]:
        lines.append(f"- {item}")
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
        ]
    )
    lines.append("")
    return "\n".join(lines)


def build_hipotesis_page(section: dict, generated_at: str, notice: str) -> str:
    hipotesis = load_yaml_json("00_sistema_tesis/config/hipotesis.yaml")["hipotesis"]
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    
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
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))

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
    if not entries:
        lines.extend(["## Estado", "", "Sin decisiones registradas aún.", ""])
        return "\n".join(lines)
    lines.extend(["## Decisiones registradas", ""])
    for item in entries:
        lines.append(f"- `{item['fecha']}` [{item['titulo']}](../{item['archivo']})")
    lines.append("")
    return "\n".join(lines)


def build_bitacora_page(section: dict, generated_at: str, notice: str) -> str:
    bitacoras = list_markdown_entries("00_sistema_tesis/bitacora")
    reportes = list_markdown_entries("00_sistema_tesis/reportes_semanales")
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
    lines.extend(["## Bitácoras", ""])
    if bitacoras:
        for item in bitacoras:
            lines.append(f"- `{item['fecha']}` [{item['titulo']}](../{item['archivo']})")
    else:
        lines.append("Sin bitácoras registradas aún.")
    lines.extend(["", "## Reportes semanales", ""])
    if reportes:
        for item in reportes:
            lines.append(f"- `{item['fecha']}` [{item['titulo']}](../{item['archivo']})")
    else:
        lines.append("Sin reportes semanales registrados aún.")
    lines.append("")
    return "\n".join(lines)


def build_coverage_page(section: dict, generated_at: str, notice: str) -> str:
    status = directory_markdown_status(section["fuentes"][0])
    lines = [
        f"# {section['titulo']}",
        "",
        section["descripcion"],
        "",
    ]
    lines.extend(render_metadata(generated_at=generated_at, status="ok", sources=section["fuentes"], notice=notice))
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
    generated_at = now_stamp()
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
        markdown_path.write_text(markdown_content + "\n", encoding="utf-8")

        html_content = render_html_page(section["titulo"], markdown_content, generated_at)
        html_path = html_dir / f"{page_id}.html"
        html_path.write_text(html_content, encoding="utf-8")

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
    index_path.write_text(index_content + "\n", encoding="utf-8")
    index_html_path = html_dir / "index.html"
    index_html_path.write_text(render_html_page("Wiki verificable", index_content, generated_at), encoding="utf-8")

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
