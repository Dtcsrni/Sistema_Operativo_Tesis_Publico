from __future__ import annotations

from pathlib import Path

from common import ROOT, ensure_generated_dir, extract_markdown_labeled_value, extract_markdown_section_bullets, list_markdown_entries, load_csv_rows, load_yaml_json, stable_generated_at, write_text_if_changed
from validate_structure import validate
from validate_wiki import validate_wiki


def is_meaningful_value(value: str | None) -> bool:
    if not value:
        return False
    return bool(value.strip())


def contains_actual_waste_signal(value: str | None) -> bool:
    if not is_meaningful_value(value):
        return False
    lowered = value.lower()
    avoided_markers = [
        "habría sido ineficiente",
        "se evitó",
        "evitado",
        "no se invirtió",
        "se evitara",
    ]
    return not any(marker in lowered for marker in avoided_markers)


def build_usage_recommendation(
    *,
    weekly_waste_opportunities: int,
    weekly_actual_waste_signals: int,
    session_logs_with_economy: int,
    total_logs: int,
) -> str:
    if total_logs == 0:
        return "No hay historial suficiente para evaluar economía de uso; primero debe consolidarse registro operativo."
    if session_logs_with_economy < total_logs:
        return "Antes de sacar conclusiones fuertes, conviene cerrar cobertura completa de economía de uso en bitácoras."
    if weekly_actual_waste_signals > 0:
        return "Existe al menos una semana con gasto ineficiente real; la siguiente revisión debe traducir esa señal a una regla concreta de uso."
    if weekly_waste_opportunities > 0:
        return "Las oportunidades de desperdicio registradas parecen haber sido evitadas; mantener razonamiento medio por defecto y reservar razonamiento alto para tareas fundacionales sigue siendo la estrategia más eficiente."
    return "La disciplina de uso parece estable; conviene mantener la política actual y observar si cambia cuando el proyecto entre a arquitectura, métricas y simulación."


def main() -> int:
    ensure_generated_dir()

    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    hipotesis = load_yaml_json("00_sistema_tesis/config/hipotesis.yaml")["hipotesis"]
    bloques = load_yaml_json("00_sistema_tesis/config/bloques.yaml")["bloques"]
    backlog = load_csv_rows("01_planeacion/backlog.csv")
    riesgos = load_csv_rows("01_planeacion/riesgos.csv")
    gobernanza_ia = load_yaml_json("00_sistema_tesis/config/ia_gobernanza.yaml")
    decisiones = list_markdown_entries("00_sistema_tesis/decisiones")
    reportes_semanales = list_markdown_entries("00_sistema_tesis/reportes_semanales")
    bitacoras = list_markdown_entries("00_sistema_tesis/bitacora")
    errores = validate()
    errores_wiki = validate_wiki()

    activas = [item for item in hipotesis if item["estado"] == "activa"]
    pendientes = [item for item in backlog if item["estado"] == "pendiente"]
    riesgos_abiertos = [item for item in riesgos if item["estado"] == "abierto"]
    weekly_reports_with_economy = sum(1 for item in reportes_semanales if extract_markdown_section_bullets(item["archivo"], "Economía de uso"))
    session_logs_with_economy = sum(1 for item in bitacoras if extract_markdown_section_bullets(item["archivo"], "Economía de uso"))
    weekly_waste_opportunities = sum(
        1
        for item in reportes_semanales
        if is_meaningful_value(extract_markdown_labeled_value(item["archivo"], "Economía de uso", "Qué consumió de más para el valor obtenido"))
    )
    weekly_actual_waste_signals = sum(
        1
        for item in reportes_semanales
        if contains_actual_waste_signal(extract_markdown_labeled_value(item["archivo"], "Economía de uso", "Qué consumió de más para el valor obtenido"))
    )
    task_matrix = gobernanza_ia["economia_y_optimizacion_de_uso"]["matriz_operativa_por_tipo_de_tarea"]
    generated_at = stable_generated_at(
        [
            "00_sistema_tesis/config/sistema_tesis.yaml",
            "00_sistema_tesis/config/hipotesis.yaml",
            "00_sistema_tesis/config/bloques.yaml",
            "00_sistema_tesis/config/ia_gobernanza.yaml",
            "01_planeacion/backlog.csv",
            "01_planeacion/riesgos.csv",
            "00_sistema_tesis/decisiones",
            "00_sistema_tesis/reportes_semanales",
            "00_sistema_tesis/bitacora",
        ]
    )
    usage_recommendation = build_usage_recommendation(
        weekly_waste_opportunities=weekly_waste_opportunities,
        weekly_actual_waste_signals=weekly_actual_waste_signals,
        session_logs_with_economy=session_logs_with_economy,
        total_logs=len(bitacoras),
    )

    output = f"""# Reporte de consistencia

    - Fecha de generación: {generated_at}
- Proyecto: {sistema["identidad_proyecto"]["nombre_corto"]}
- Versión del sistema: {sistema["version"]}

## Resumen

- Bloques definidos: {len(bloques)}
- Hipótesis definidas: {len(hipotesis)}
- Hipótesis activas: {len(activas)}
- Tareas en backlog: {len(backlog)}
- Tareas pendientes: {len(pendientes)}
- Riesgos abiertos: {len(riesgos_abiertos)}
- Decisiones registradas: {len(decisiones)}
- Errores de validación de wiki: {len(errores_wiki)}
- Resúmenes semanales con economía de uso: {weekly_reports_with_economy}/{len(reportes_semanales)}
- Bitácoras con economía de uso: {session_logs_with_economy}/{len(bitacoras)}
- Semanas con oportunidad de desperdicio identificada: {weekly_waste_opportunities}/{len(reportes_semanales)}
- Semanas con gasto ineficiente realmente registrado: {weekly_actual_waste_signals}/{len(reportes_semanales)}

## Resultado de validación

{"Sin errores de consistencia detectados." if not errores and not errores_wiki else "Se detectaron errores de consistencia."}
"""

    if errores:
        output += "\n## Errores\n\n"
        for error in errores:
            output += f"- {error}\n"
    if errores_wiki:
        output += "\n## Errores de wiki\n\n"
        for error in errores_wiki:
            output += f"- {error}\n"

    output += f"""
## Observaciones operativas

- El dashboard debe regenerarse desde fuentes, no editarse manualmente.
- La wiki verificable debe regenerarse desde fuentes, no editarse manualmente.
- Los subbloques y tareas finas viven en `backlog.csv`, no en `bloques.yaml`.
- La siguiente presión metodológica está en B1 y B2: contexto, línea base y operativización de hipótesis.
- La economía de uso debe revisarse semanalmente en función de avance funcional verificable, no solo de volumen de interacción.

## Recomendación de uso

{usage_recommendation}

## Matriz operativa sugerida

""" + "\n".join(
        f"- {item['tipo_de_tarea']}: usar `{item['nivel_recomendado']}`. Subir si {item['cuando_subir']}. Bajar si {item['cuando_bajar']}."
        for item in task_matrix
    ) + "\n"

    report_path = ROOT / "06_dashboard" / "generado" / "reporte_consistencia.md"
    write_text_if_changed(report_path, output)

    print(f"Reporte generado en: {report_path}")
    total_errors = len(errores) + len(errores_wiki)
    print("Resultado:", "OK" if total_errors == 0 else "CON ERRORES")
    return 0 if total_errors == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
