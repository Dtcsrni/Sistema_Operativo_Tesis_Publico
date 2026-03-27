from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys

from canon import validate_events
from common import ROOT, VALID_EVIDENCE, VALID_PRIORITIES, load_csv_rows, load_yaml_json, file_sha256


def check_human_drift() -> list[str]:
    errors = []
    sign_off_path = "00_sistema_tesis/config/sign_offs.json"
    if not (ROOT / sign_off_path).exists():
        return errors
    
    data = load_yaml_json(sign_off_path)
    for record in data.get("sign_offs", []):
        rel_path = record["archivo"]
        if (ROOT / rel_path).exists():
            current_hash = file_sha256(rel_path)
            if current_hash != record["hash_verificado"]:
                # Es una advertencia, no bloqueamos el build pero lo reportamos
                print(f"[DRIFT] El archivo {rel_path} cambió tras la firma humana ({record['fecha']})")
    return errors


REQUIRED_PATHS = [
    "00_sistema_tesis/canon/events.jsonl",
    "00_sistema_tesis/canon/state.json",
    "00_sistema_tesis/config/sistema_tesis.yaml",
    "00_sistema_tesis/config/agent_identity.json",
    "00_sistema_tesis/config/hipotesis.yaml",
    "00_sistema_tesis/config/bloques.yaml",
    "00_sistema_tesis/config/dashboard.yaml",
    "00_sistema_tesis/config/ia_gobernanza.yaml",
    "00_sistema_tesis/config/publicacion.yaml",
    "00_sistema_tesis/config/wiki.yaml",
    "00_sistema_tesis/config/backup_rotation_policy.json",
    "00_sistema_tesis/manual_operacion_humana.md",
    "00_sistema_tesis/evidencia_privada/conversaciones_codex/.gitkeep",
    "00_sistema_tesis/bitacora/indice_fuentes_conversacion.md",
    "01_planeacion/backlog.csv",
    "01_planeacion/riesgos.csv",
    "01_planeacion/roadmap.csv",
    "01_planeacion/entregables.csv",
    "README_INICIO.md",
    "README.md",
    "07_scripts/tesis.py",
    "07_scripts/rotate_backups.py",
]


def validate() -> list[str]:
    errors: list[str] = []

    for rel_path in REQUIRED_PATHS:
        if not (ROOT / rel_path).exists():
            errors.append(f"Falta la ruta requerida: {rel_path}")

    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    agent_identity = load_yaml_json("00_sistema_tesis/config/agent_identity.json")
    hipotesis_doc = load_yaml_json("00_sistema_tesis/config/hipotesis.yaml")
    bloques_doc = load_yaml_json("00_sistema_tesis/config/bloques.yaml")
    dashboard = load_yaml_json("00_sistema_tesis/config/dashboard.yaml")
    publicacion = load_yaml_json("00_sistema_tesis/config/publicacion.yaml")
    wiki = load_yaml_json("00_sistema_tesis/config/wiki.yaml")
    backlog = load_csv_rows("01_planeacion/backlog.csv")
    ia_policy = load_yaml_json("00_sistema_tesis/config/ia_gobernanza.yaml")

    bloque_ids = {item["id"] for item in bloques_doc["bloques"]}
    hipotesis_ids = {item["id"] for item in hipotesis_doc["hipotesis"]}

    if sistema["bloque_activo"] not in bloque_ids:
        errors.append("El bloque activo de sistema_tesis.yaml no existe en bloques.yaml")

    for bloque in bloques_doc["bloques"]:
        if bloque["prioridad"] not in VALID_PRIORITIES:
            errors.append(f"Bloque {bloque['id']} tiene prioridad inválida: {bloque['prioridad']}")
        if not bloque["criterio_salida"].strip():
            errors.append(f"Bloque {bloque['id']} no tiene criterio de salida")
        for hip in bloque["hipotesis_relacionadas"]:
            if hip not in hipotesis_ids:
                errors.append(f"Bloque {bloque['id']} referencia hipótesis inexistente: {hip}")

    active_associations = {hip["id"]: 0 for hip in hipotesis_doc["hipotesis"] if hip["estado"] == "activa"}
    for bloque in bloques_doc["bloques"]:
        for hip in bloque["hipotesis_relacionadas"]:
            if hip in active_associations:
                active_associations[hip] += 1

    for hip, count in active_associations.items():
        if hip != "HG" and count == 0:
            errors.append(f"La hipótesis activa {hip} no está asociada a ningún bloque")

    for hip in hipotesis_doc["hipotesis"]:
        if hip["prioridad"] not in VALID_PRIORITIES:
            errors.append(f"Hipótesis {hip['id']} tiene prioridad inválida: {hip['prioridad']}")
        for evidence_name, value in hip["evidencia_disponible"].items():
            if value not in VALID_EVIDENCE:
                errors.append(f"Hipótesis {hip['id']} tiene evidencia inválida en {evidence_name}: {value}")

    for task in backlog:
        if task["prioridad"] not in VALID_PRIORITIES:
            errors.append(f"Tarea {task['task_id']} tiene prioridad inválida: {task['prioridad']}")
        if task["bloque"] not in bloque_ids:
            errors.append(f"Tarea {task['task_id']} referencia bloque inexistente: {task['bloque']}")
        if task["hipotesis"]:
            for hip in task["hipotesis"].split("|"):
                if hip and hip not in hipotesis_ids:
                    errors.append(f"Tarea {task['task_id']} referencia hipótesis inexistente: {hip}")

    html_output = Path(ROOT / dashboard["salida"]["html"])
    if html_output.suffix.lower() != ".html":
        errors.append("La salida del dashboard debe ser un archivo HTML")

    if dashboard["reglas"]["editable_directamente"] is not False:
        errors.append("dashboard.yaml debe indicar que el dashboard no es editable directamente")

    if wiki["politica"]["editable_directamente"] is not False:
        errors.append("wiki.yaml debe indicar que la wiki no es editable directamente")

    if publicacion["politica"]["editable_directamente"] is not False:
        errors.append("publicacion.yaml debe indicar que el bundle público no es editable directamente")

    source_policy = dict(ia_policy.get("evidencia_fuente_conversacion", {}))
    if not source_policy:
        errors.append("ia_gobernanza.yaml no contiene la política evidencia_fuente_conversacion")
    else:
        activation = dict(source_policy.get("activacion", {}))
        if not str(activation.get("desde_step_id", "")).startswith("VAL-STEP-"):
            errors.append("evidencia_fuente_conversacion.activacion.desde_step_id debe ser un VAL-STEP válido")

    for artifact in publicacion["artefactos"]:
        source = artifact["source"]
        if not (ROOT / source).exists():
            errors.append(f"publicacion.yaml referencia una fuente inexistente: {source}")
    excluded_prefixes = set(publicacion.get("sanitizacion", {}).get("excluir_prefijos", []))
    if "00_sistema_tesis/evidencia_privada/" not in excluded_prefixes:
        errors.append("publicacion.yaml debe excluir 00_sistema_tesis/evidencia_privada/ del bundle público")

    manual_humano = (ROOT / "00_sistema_tesis" / "manual_operacion_humana.md").read_text(encoding="utf-8")
    for marker in ("Retomar", "Registrar cambio", "Auditar", "Publicación pública"):
        if marker not in manual_humano:
            errors.append(f"manual_operacion_humana.md no contiene el recorrido requerido: {marker}")
    for marker in ("source register", "source verify", "evidencia fuente"):
        if marker not in manual_humano:
            errors.append(f"manual_operacion_humana.md no documenta el flujo requerido: {marker}")

    section_ids = {section["id"] for section in wiki["secciones"]}
    required_wiki_sections = {
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
    for section_id in sorted(required_wiki_sections - section_ids):
        errors.append(f"wiki.yaml no contiene la sección requerida: {section_id}")

    for source in wiki["fuentes_base"]:
        if not (ROOT / source).exists():
            errors.append(f"wiki.yaml referencia una fuente base inexistente: {source}")

    for section in wiki["secciones"]:
        if not section["fuentes"]:
            errors.append(f"La sección de wiki {section['id']} no tiene fuentes declaradas")
        for source in section["fuentes"]:
            if not (ROOT / source).exists():
                errors.append(f"La sección de wiki {section['id']} referencia una fuente inexistente: {source}")

    required_agent_fields = {"agent_role", "provider", "model_version", "runtime_label"}
    actual_agent_fields = set(agent_identity.get("agent_identity", {}).keys())
    for field in sorted(required_agent_fields - actual_agent_fields):
        errors.append(f"agent_identity.json no contiene el campo requerido: {field}")

    gitignore_content = (ROOT / ".gitignore").read_text(encoding="utf-8")
    if "00_sistema_tesis/evidencia_privada/conversaciones_codex/" not in gitignore_content:
        errors.append(".gitignore debe excluir la evidencia privada de conversaciones Codex")

    errors.extend(validate_events())

    return errors


def validate_identity() -> list[str]:
    errors = []
    tesista_path = "00_sistema_tesis/config/tesista.json"
    if not (ROOT / tesista_path).exists():
        errors.append("Falta el archivo de identidad: tesista.json")
        return errors

    data = load_yaml_json(tesista_path)
    emails_autorizados = data.get("tesista", {}).get("identidad_digital", {}).get("emails_autorizados", [])

    # Obtener email actual de Git
    try:
        git_email = subprocess.check_output(["git", "config", "user.email"], text=True).strip()
        if git_email not in emails_autorizados:
            errors.append(f"El email de Git '{git_email}' no está en la lista de emails autorizados en tesista.json")
    except Exception:
        errors.append("No se pudo obtener el email de Git o Git no está configurado")

    # Validar CURP
    curp = data.get("tesista", {}).get("curp", "")
    if curp and curp != "PONER_AQUÍ_TU_CURP":
        # Regex estándar para CURP de México
        curp_regex = r"^[A-Z][AEIOU][A-Z]{2}\d{6}[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z\d]\d$"
        if not re.match(curp_regex, curp):
            errors.append(f"El CURP '{curp}' no tiene un formato válido (18 caracteres).")
    elif curp == "PONER_AQUÍ_TU_CURP":
        errors.append("Falta configurar el CURP real en tesista.json")

    return errors


def main() -> int:
    errors = validate()
    errors.extend(validate_identity())
    if errors:
        print("VALIDACION: ERROR")
        for item in errors:
            print(f"- {item}")
        return 1

    print("VALIDACION: OK")
    print(f"Rutas revisadas: {len(REQUIRED_PATHS)}")
    print("Reglas clave: bloque activo, referencias de hipótesis, prioridades, criterio de salida y dashboard derivado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
