from __future__ import annotations

from pathlib import Path

from common import ROOT, list_markdown_entries, load_csv_rows, load_yaml_json, now_stamp


def priority_rank(value: str) -> int:
    order = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
    return order.get(value, 99)


def main() -> int:
    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    hipotesis = load_yaml_json("00_sistema_tesis/config/hipotesis.yaml")["hipotesis"]
    bloques = load_yaml_json("00_sistema_tesis/config/bloques.yaml")["bloques"]
    backlog = load_csv_rows("01_planeacion/backlog.csv")
    riesgos = load_csv_rows("01_planeacion/riesgos.csv")
    entregables = load_csv_rows("01_planeacion/entregables.csv")
    decisiones = list_markdown_entries("00_sistema_tesis/decisiones")[:3]

    bloque_activo = next(item for item in bloques if item["id"] == sistema["bloque_activo"])
    hipotesis_activas = [item for item in hipotesis if item["estado"] == "activa"]
    hipotesis_activas.sort(key=lambda item: (priority_rank(item["prioridad"]), item["id"]))
    backlog_prioritario = [item for item in backlog if item["estado"] in {"pendiente", "en_progreso"}]
    backlog_prioritario.sort(key=lambda item: (priority_rank(item["prioridad"]), item["fecha_objetivo"], item["task_id"]))
    riesgos_abiertos = [item for item in riesgos if item["estado"] == "abierto"]
    entregable_actual = next((item for item in entregables if item["deliverable_id"] == sistema["siguiente_entregable"]), None)

    lines = [
        "# Sistema Operativo de la Tesis",
        "",
        "![Security Status](06_dashboard/generado/badges/security_status.svg)",
        "![Integrity Status](06_dashboard/generado/badges/integrity.svg)",
        "![Ledger Status](06_dashboard/generado/badges/ledger.svg)",
        "",
        "> Este `README.md` es un artefacto generado. No lo edites manualmente.",
        "> Fuente de verdad: `README_INICIO.md` + `00_sistema_tesis/config/` + `01_planeacion/`.",
        "",
        "## Propósito",
        "",
        sistema["titulo_vigente"],
        "",
        sistema["resumen_problema"],
        "",
        "Este repositorio privado gobierna decisiones, hipótesis, backlog, riesgos, experimentos, datos, implementación, redacción y gobernanza de IA para una tesis de posgrado en IoT enfocada en resiliencia operativa en entornos urbanos intermitentes.",
        "",
        "## Estado actual",
        "",
        f"- **Versión del sistema:** `{sistema['version']}`",
        f"- **Estado global:** `{sistema['estado_global']}`",
        f"- **Bloque activo:** `{bloque_activo['id']}` - {bloque_activo['nombre']}",
        f"- **Fase actual:** `{sistema['fase_actual']}`",
        f"- **Siguiente entregable:** `{sistema['siguiente_entregable']}`" + (f" - {entregable_actual['nombre']}" if entregable_actual else ""),
        f"- **Riesgo principal abierto:** `{sistema['riesgo_principal_abierto']}`",
        "",
        "## Qué contiene",
        "",
        "- `00_sistema_tesis/`: gobierno del sistema, decisiones, bitácora, reportes y plantillas.",
        "- `01_planeacion/`: backlog, riesgos, roadmap y entregables canónicos.",
        "- `02_experimentos/`: simulación y validación experimental.",
        "- `03_datos/`: datos raw, procesados y catálogos.",
        "- `04_implementacion/`: firmware, gateway y analítica.",
        "- `05_tesis/`: capítulos, figuras y ensamblaje de tesis.",
        "- `06_dashboard/`: dashboard HTML y exportables derivados.",
        "- `07_scripts/`: validación, generación y consolidación.",
        "",
        "## Retoma rápida",
        "",
        "Empieza por estos archivos:",
        "",
        "- [`README_INICIO.md`](README_INICIO.md)",
        "- [`00_sistema_tesis/config/sistema_tesis.yaml`](00_sistema_tesis/config/sistema_tesis.yaml)",
        "- [`00_sistema_tesis/config/hipotesis.yaml`](00_sistema_tesis/config/hipotesis.yaml)",
        "- [`00_sistema_tesis/config/bloques.yaml`](00_sistema_tesis/config/bloques.yaml)",
        "- [`00_sistema_tesis/config/publicacion.yaml`](00_sistema_tesis/config/publicacion.yaml)",
        "- [`01_planeacion/backlog.csv`](01_planeacion/backlog.csv)",
        "- [`06_dashboard/wiki/index.md`](06_dashboard/wiki/index.md)",
        "- [`06_dashboard/generado/index.html`](06_dashboard/generado/index.html)",
        "",
        "## Qué revisar siempre",
        "",
        "- [`00_sistema_tesis/manual_operacion_humana.md`](00_sistema_tesis/manual_operacion_humana.md)",
        "- [`00_sistema_tesis/config/sistema_tesis.yaml`](00_sistema_tesis/config/sistema_tesis.yaml)",
        "- [`01_planeacion/backlog.csv`](01_planeacion/backlog.csv)",
        "- [`01_planeacion/riesgos.csv`](01_planeacion/riesgos.csv)",
        "- [`00_sistema_tesis/bitacora/matriz_trazabilidad.md`](00_sistema_tesis/bitacora/matriz_trazabilidad.md)",
        "- [`06_dashboard/wiki/index.md`](06_dashboard/wiki/index.md)",
        "- [`06_dashboard/generado/index.html`](06_dashboard/generado/index.html)",
        "- [`06_dashboard/publico/index.md`](06_dashboard/publico/index.md)",
        "",
        "## Hipótesis activas prioritarias",
        "",
    ]

    for item in hipotesis_activas[:4]:
        lines.append(f"- **{item['id']}** · {item['nombre_corto']} · prioridad `{item['prioridad']}`")
        lines.append(f"  Bloques: {', '.join(item['bloques_asociados'])}")

    lines.extend(
        [
            "",
            "## Backlog inmediato",
            "",
        ]
    )

    for item in backlog_prioritario[:6]:
        lines.append(
            f"- **{item['task_id']}** · `{item['bloque']}` · {item['tarea']} · prioridad `{item['prioridad']}` · objetivo `{item['fecha_objetivo']}`"
        )

    lines.extend(
        [
            "",
            "## Riesgos abiertos",
            "",
        ]
    )

    for item in riesgos_abiertos[:4]:
        lines.append(
            f"- **{item['risk_id']}** · {item['riesgo']} · probabilidad `{item['probabilidad']}` · impacto `{item['impacto']}`"
        )

    lines.extend(
        [
            "",
            "## Decisiones recientes",
            "",
        ]
    )

    for item in decisiones:
        lines.append(f"- **{item['fecha']}** · [{item['titulo']}]({item['archivo']})")

    lines.extend(
        [
            "",
            "## Operación",
            "",
            "Ruta humana mínima:",
            "",
            "```powershell",
            "python 07_scripts/tesis.py status",
            "python 07_scripts/tesis.py doctor",
            "python 07_scripts/tesis.py next",
            "```",
            "",
            "CLI canónica:",
            "",
            "```powershell",
            "python 07_scripts/tesis.py status",
            "python 07_scripts/tesis.py doctor",
            "python 07_scripts/tesis.py next",
            "python 07_scripts/tesis.py audit --check",
            "python 07_scripts/tesis.py materialize",
            "python 07_scripts/tesis.py publish --check",
            "python 07_scripts/tesis.py publish --build",
            "```",
            "",
            "Flujo recomendado:",
            "",
            "```powershell",
            "python 07_scripts/build_all.py",
            "```",
            "",
            "Validar estructura y relaciones:",
            "",
            "```powershell",
            "python 07_scripts/validate_structure.py",
            "python 07_scripts/validate_wiki.py",
            "```",
            "",
            "Generar wiki verificable Markdown + HTML:",
            "",
            "```powershell",
            "python 07_scripts/build_wiki.py",
            "```",
            "",
            "Generar dashboard HTML:",
            "",
            "```powershell",
            "python 07_scripts/build_dashboard.py",
            "```",
            "",
            "Generar esta portada:",
            "",
            "```powershell",
            "python 07_scripts/build_readme_portada.py",
            "```",
            "",
            "Exportar hoja maestra:",
            "",
            "```powershell",
            "python 07_scripts/export_master_sheet.py",
            "```",
            "",
            "Generar reporte de consistencia:",
            "",
            "```powershell",
            "python 07_scripts/report_consistency.py",
            "```",
            "",
            "## Superficies",
            "",
            "- La superficie privada conserva canon, backlog, decisiones, bitácora y auditoría completa.",
            "- La superficie pública vive en `06_dashboard/publico/` como bundle sanitizado y derivado.",
            "- La IA es opcional; el sistema debe poder operarse y explicarse siguiendo rutas humanas explícitas.",
            "",
            "## Criterios de gobierno",
            "",
            "- El repositorio es la fuente de verdad.",
            "- Los artefactos generados no se corrigen a mano; se regeneran.",
            "- La wiki verificable es una guía derivada y trazable; no sustituye a las fuentes canónicas.",
            "- Los bloques macro viven en `bloques.yaml`; los subbloques y tareas en `backlog.csv`.",
            "- Toda decisión relevante debe registrarse.",
            "- TDD rige cambios en scripts, validadores, generadores y software nuevo.",
            "- La IA se usa como apoyo instrumental con revisión humana proporcional al riesgo.",
            "",
            "## Artefactos derivados",
            "",
            "- [`README.md`](README.md)",
            "- [`06_dashboard/wiki/index.md`](06_dashboard/wiki/index.md)",
            "- [`06_dashboard/generado/wiki/index.html`](06_dashboard/generado/wiki/index.html)",
            "- [`06_dashboard/generado/wiki_manifest.json`](06_dashboard/generado/wiki_manifest.json)",
            "- [`06_dashboard/generado/index.html`](06_dashboard/generado/index.html)",
            "- [`06_dashboard/generado/hoja_maestra_consolidada.csv`](06_dashboard/generado/hoja_maestra_consolidada.csv)",
            "- [`06_dashboard/generado/reporte_consistencia.md`](06_dashboard/generado/reporte_consistencia.md)",
            "",
            f"_Generado automáticamente el {now_stamp()}._",
            "",
        ]
    )

    output_path = ROOT / "README.md"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"README de portada generado en: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
