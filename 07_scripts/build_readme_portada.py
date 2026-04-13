from __future__ import annotations

from pathlib import Path

from common import ROOT, list_markdown_entries, load_csv_rows, load_yaml_json, stable_generated_at, write_text_if_changed


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
    docs = {
        "proposito": "00_sistema_tesis/documentacion_sistema/proposito_y_alcance.md",
        "modulos": "00_sistema_tesis/documentacion_sistema/mapa_de_modulos.md",
        "flujos": "00_sistema_tesis/documentacion_sistema/flujos_operativos.md",
        "interaccion": "00_sistema_tesis/documentacion_sistema/interaccion_por_actor.md",
        "glosario": "00_sistema_tesis/documentacion_sistema/glosario_terminologia_y_convenciones.md",
    }
    generated_at = stable_generated_at(
        [
            "README_INICIO.md",
            "00_sistema_tesis/config/sistema_tesis.yaml",
            "00_sistema_tesis/config/hipotesis.yaml",
            "00_sistema_tesis/config/bloques.yaml",
            "00_sistema_tesis/config/publicacion.yaml",
            "01_planeacion/backlog.csv",
            "01_planeacion/riesgos.csv",
            "01_planeacion/entregables.csv",
            "00_sistema_tesis/decisiones",
            docs["proposito"],
            docs["modulos"],
            docs["flujos"],
            docs["interaccion"],
            docs["glosario"],
        ]
    )

    bloque_activo = next(item for item in bloques if item["id"] == sistema["bloque_activo"])
    hipotesis_activas = [item for item in hipotesis if item["estado"] == "activa"]
    hipotesis_activas.sort(key=lambda item: (priority_rank(item["prioridad"]), item["id"]))
    backlog_prioritario = [item for item in backlog if item["estado"] in {"pendiente", "en_progreso"}]
    backlog_prioritario.sort(key=lambda item: (priority_rank(item["prioridad"]), item["fecha_objetivo"], item["task_id"]))
    riesgos_abiertos = [item for item in riesgos if item["estado"] == "abierto"]
    entregable_actual = next((item for item in entregables if item["deliverable_id"] == sistema["siguiente_entregable"]), None)

    lines = [
        "# Plataforma de Investigación para Tesis IoT",
        "",
        "![Estado de seguridad](06_dashboard/generado/badges/security_status.svg)",
        "![Estado de integridad](06_dashboard/generado/badges/integrity.svg)",
        "![Estado del ledger](06_dashboard/generado/badges/ledger.svg)",
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
        "Este repositorio documenta decisiones, hipótesis, backlog, riesgos, experimentos, datos, implementación, redacción y gobernanza de IA para una tesis de posgrado en IoT enfocada en resiliencia operativa en entornos urbanos intermitentes.",
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
        "- `00_sistema_tesis/documentacion_sistema/`: narrativa canónica del propósito, módulos, flujos e interacción.",
        "- `01_planeacion/`: backlog, riesgos, roadmap y entregables canónicos.",
        "- `02_experimentos/`: simulación y validación experimental.",
        "- `03_datos/`: datos en bruto, procesados y catálogos.",
        "- `04_implementacion/`: firmware, pasarela y analítica.",
        "- `05_tesis/`: capítulos, figuras y ensamblaje de tesis.",
        "- `06_dashboard/`: dashboard HTML y exportables derivados.",
        "- `07_scripts/`: validación, generación y consolidación.",
        "- `docs/`: arquitectura, operación, seguridad y reproducibilidad estructuradas.",
        "- `manifests/`: contratos máquina-legibles de almacenamiento, dominios, servicios y publicación.",
        "- `bootstrap/`: instalación por fases para host Windows y Orange Pi.",
        "- `runtime/openclaw/`: integración opcional, wrappers y políticas de OpenClaw.",
        "- `config/systemd/` y `config/env/`: servicios, temporizadores y variables de entorno de referencia.",
        "- `tests/smoke/`, `tests/integration/`, `benchmarks/` y `ops/`: verificación, medición y operación de campo.",
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
        f"- [`{docs['proposito']}`]({docs['proposito']})",
        f"- [`{docs['modulos']}`]({docs['modulos']})",
        f"- [`{docs['flujos']}`]({docs['flujos']})",
        f"- [`{docs['interaccion']}`]({docs['interaccion']})",
        f"- [`{docs['glosario']}`]({docs['glosario']})",
        "- [`01_planeacion/backlog.csv`](01_planeacion/backlog.csv)",
        "- [`docs/02_arquitectura/arquitectura-general.md`](docs/02_arquitectura/arquitectura-general.md)",
        "- [`manifests/storage_layout.yaml`](manifests/storage_layout.yaml)",
        "- [`bootstrap/orangepi/10_primer-arranque.sh`](bootstrap/orangepi/10_primer-arranque.sh)",
        "- [`06_dashboard/wiki/index.md`](06_dashboard/wiki/index.md)",
        "- [`06_dashboard/generado/index.html`](06_dashboard/generado/index.html)",
        "",
        "## Ruta de lectura",
        "",
        "- Para entender para qué existe el sistema: `README_INICIO.md` y `proposito_y_alcance.md`.",
        "- Para entender módulos y relaciones: `mapa_de_modulos.md`.",
        "- Para entender recorridos de trabajo: `flujos_operativos.md`.",
        "- Para entender identificadores, términos y convenciones: `glosario_terminologia_y_convenciones.md`.",
        "- Para operar como tesista: `manual_operacion_humana.md`.",
        "- Para exploración externa: wiki derivada y bundle público reproducible.",
        "",
        "## Navegación y trazabilidad",
        "",
        "- La entrada navegable del sistema es [`06_dashboard/wiki/index.md`](06_dashboard/wiki/index.md).",
        "- Cada página de la wiki debe declarar navegación local, fuentes canónicas y artefactos derivados relacionados.",
        "- Si una salida derivada necesita cambio, la intervención correcta es sobre la fuente canónica declarada, no sobre el derivado.",
        "- Para cerrar la cadena de rastreo revisa [`06_dashboard/generado/wiki_manifest.json`](06_dashboard/generado/wiki_manifest.json) y [`06_dashboard/publico/manifest_publico.json`](06_dashboard/publico/manifest_publico.json).",
        "- Para trazabilidad operativa del trabajo revisa [`00_sistema_tesis/bitacora/matriz_trazabilidad.md`](00_sistema_tesis/bitacora/matriz_trazabilidad.md) y [`00_sistema_tesis/bitacora/log_conversaciones_ia.md`](00_sistema_tesis/bitacora/log_conversaciones_ia.md).",
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
            "- La superficie canónica conserva canon, backlog, decisiones, bitácora y auditoría completa.",
            "- La superficie pública vive en `06_dashboard/publico/` como bundle derivado y curado editorialmente.",
            "- La IA es opcional; el sistema debe poder operarse y explicarse siguiendo rutas humanas explícitas.",
            "- La capa pública existe para exploración y evaluación técnica, no para sustituir el canon canónico.",
            "",
            "## Criterios de gobierno",
            "",
            "- El repositorio canónico es la fuente de verdad.",
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
            f"_Generado automáticamente el {generated_at}._",
            "",
        ]
    )

    output_path = ROOT / "README.md"
    write_text_if_changed(output_path, "\n".join(lines))
    print(f"README de portada generado en: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
