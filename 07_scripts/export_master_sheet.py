from __future__ import annotations

import csv
from pathlib import Path

from common import ROOT, ensure_generated_dir, load_csv_rows, load_yaml_json


def main() -> int:
    ensure_generated_dir()
    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    hipotesis = load_yaml_json("00_sistema_tesis/config/hipotesis.yaml")["hipotesis"]
    bloques = load_yaml_json("00_sistema_tesis/config/bloques.yaml")["bloques"]
    backlog = load_csv_rows("01_planeacion/backlog.csv")
    riesgos = load_csv_rows("01_planeacion/riesgos.csv")
    entregables = load_csv_rows("01_planeacion/entregables.csv")

    output_path = Path(ROOT / sistema["rutas_canonicas"]["dashboard_generado"]).with_name("hoja_maestra_consolidada.csv")
    fieldnames = ["tipo_registro", "id", "nombre", "estado", "prioridad", "referencia_1", "referencia_2", "notas"]
    rows = []

    for item in bloques:
        rows.append(
            {
                "tipo_registro": "bloque",
                "id": item["id"],
                "nombre": item["nombre"],
                "estado": item["estado"],
                "prioridad": item["prioridad"],
                "referencia_1": "|".join(item["hipotesis_relacionadas"]),
                "referencia_2": "|".join(item["entregables"]),
                "notas": item["descripcion"],
            }
        )
    for item in hipotesis:
        rows.append(
            {
                "tipo_registro": "hipotesis",
                "id": item["id"],
                "nombre": item["nombre_corto"],
                "estado": item["estado"],
                "prioridad": item["prioridad"],
                "referencia_1": "|".join(item["bloques_asociados"]),
                "referencia_2": "|".join(item["metricas_clave"]),
                "notas": item["descripcion"],
            }
        )
    for item in backlog:
        rows.append(
            {
                "tipo_registro": "tarea",
                "id": item["task_id"],
                "nombre": item["tarea"],
                "estado": item["estado"],
                "prioridad": item["prioridad"],
                "referencia_1": item["bloque"],
                "referencia_2": item["entregable"],
                "notas": item["notas"],
            }
        )
    for item in riesgos:
        rows.append(
            {
                "tipo_registro": "riesgo",
                "id": item["risk_id"],
                "nombre": item["riesgo"],
                "estado": item["estado"],
                "prioridad": item["impacto"],
                "referencia_1": item["tipo"],
                "referencia_2": item["probabilidad"],
                "notas": item["mitigacion"],
            }
        )
    for item in entregables:
        rows.append(
            {
                "tipo_registro": "entregable",
                "id": item["deliverable_id"],
                "nombre": item["nombre"],
                "estado": item["estado"],
                "prioridad": item["bloque_principal"],
                "referencia_1": item["artefacto_canonico"],
                "referencia_2": "",
                "notas": item["descripcion"],
            }
        )

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Hoja maestra exportada en: {output_path}")
    print(f"Registros exportados: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
