from __future__ import annotations

from pathlib import Path
import os
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
    "MEMORY.md",
    "docs/02_arquitectura/arquitectura-general.md",
    "docs/02_arquitectura/contrato-maestro-de-dominios.md",
    "docs/02_arquitectura/arquitectura-interna-sistema-tesis.md",
    "docs/02_arquitectura/arquitectura-objetivo-b0-desktop-first.md",
    "docs/02_arquitectura/criterio-formal-cierre-b0.md",
    "docs/03_operacion/flujo-escritorio-orange-pi.md",
    "docs/03_operacion/rol-de-openclaw-en-la-tesis.md",
    "docs/04_seguridad/politica-de-sanitizacion-y-publicacion.md",
    "docs/04_seguridad/modelo-de-amenazas-sistema-documental.md",
    "docs/05_reproducibilidad/relacion-entre-repo-privado-y-publico.md",
    "docs/05_reproducibilidad/migraciones-canonicas.md",
    "manifests/storage_layout.yaml",
    "manifests/desktop_edge_sync_contract.yaml",
    "manifests/service_matrix.yaml",
    "manifests/domain_boundaries.yaml",
    "manifests/domain_runtime_isolation.yaml",
    "manifests/domain_network_policy.yaml",
    "manifests/domain_backup_policy.yaml",
    "manifests/public_private_sync_policy.yaml",
    "manifests/openclaw_evaluation_policy.yaml",
    "manifests/system_tesis_architecture_contract.yaml",
    "manifests/system_tesis_canonical_schema.yaml",
    "manifests/system_tesis_cli_contracts.yaml",
    "manifests/system_tesis_dependency_map.yaml",
    "manifests/b0_external_gates.yaml",
    "bootstrap/host/00_validar-descargas.ps1",
    "bootstrap/orangepi/10_primer-arranque.sh",
    "bootstrap/orangepi/90_postcheck.sh",
    "config/systemd/tesis-healthcheck.service",
    "config/systemd/tesis-backup.service",
    "config/systemd/tesis-sync.service",
    "config/env/tesis-os.env.example",
    "runtime/openclaw/policies/ethics-policy.md",
    "ops/actualizacion/sync_repo_desde_desktop.sh",
    "runtime/openclaw/wrappers/healthcheck.sh",
    "data_contracts/literature_matrix_schema.md",
    "tests/smoke/test_boot.sh",
    "tests/integration/test_repo_layout.sh",
    "benchmarks/scripts/bench_repo_ops.sh",
    "07_scripts/tesis.py",
    "07_scripts/rotate_backups.py",
    "07_scripts/validate_b0_architecture.py",
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
    storage_layout = load_yaml_json("manifests/storage_layout.yaml")
    service_matrix = load_yaml_json("manifests/service_matrix.yaml")
    domain_boundaries = load_yaml_json("manifests/domain_boundaries.yaml")
    domain_runtime_isolation = load_yaml_json("manifests/domain_runtime_isolation.yaml")
    domain_network_policy = load_yaml_json("manifests/domain_network_policy.yaml")
    domain_backup_policy = load_yaml_json("manifests/domain_backup_policy.yaml")
    architecture_contract = load_yaml_json("manifests/system_tesis_architecture_contract.yaml")
    schema_contract = load_yaml_json("manifests/system_tesis_canonical_schema.yaml")
    cli_contracts = load_yaml_json("manifests/system_tesis_cli_contracts.yaml")
    dependency_map = load_yaml_json("manifests/system_tesis_dependency_map.yaml")
    b0_external_gates = load_yaml_json("manifests/b0_external_gates.yaml")
    public_sync = load_yaml_json("manifests/public_private_sync_policy.yaml")
    desktop_edge_sync = load_yaml_json("manifests/desktop_edge_sync_contract.yaml")
    openclaw_eval = load_yaml_json("manifests/openclaw_evaluation_policy.yaml")

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

    if storage_layout["medios"]["nvme"]["rol"] != "rootfs_principal":
        errors.append("storage_layout.yaml debe modelar NVMe como rootfs principal")
    if "/mnt/emmc/backups" not in storage_layout["medios"]["emmc"]["montajes"]:
        errors.append("storage_layout.yaml debe incluir /mnt/emmc/backups")

    service_ids = {service["id"] for service in service_matrix["servicios"]}
    for service_id in {"tesis-healthcheck", "tesis-backup", "tesis-sync", "openclaw-gateway"}:
        if service_id not in service_ids:
            errors.append(f"service_matrix.yaml no contiene el servicio requerido: {service_id}")

    isolation_domain_ids = set(domain_runtime_isolation["dominios"].keys())
    for domain_id in {"sistema_tesis", "openclaw", "edge_iot", "administrativo", "personal"}:
        if domain_id not in isolation_domain_ids:
            errors.append(f"domain_runtime_isolation.yaml no contiene el dominio requerido: {domain_id}")

    profile_ids = set(domain_network_policy["profiles"].keys())
    for service in service_matrix["servicios"]:
        if service["network_profile"] not in profile_ids:
            errors.append(
                f"service_matrix.yaml referencia un network_profile inexistente para {service['id']}: {service['network_profile']}"
            )

    if domain_backup_policy["domains"]["edge_iot"].get("validation_gate") != "host_real_requerido":
        errors.append("domain_backup_policy.yaml debe dejar edge_iot como host_real_requerido en desktop-first")

    if architecture_contract.get("desktop_first") is not True:
        errors.append("system_tesis_architecture_contract.yaml debe declarar desktop_first=true")
    layer_ids = [layer["id"] for layer in architecture_contract.get("layers", [])]
    if layer_ids != ["canon", "proyecciones", "auditoria_guardrails", "publicacion", "memoria_derivada"]:
        errors.append("system_tesis_architecture_contract.yaml debe declarar las 5 superficies canónicas esperadas")
    ownership_ids = {item["id"] for item in architecture_contract.get("surface_ownership", [])}
    if ownership_ids != set(layer_ids):
        errors.append("system_tesis_architecture_contract.yaml debe declarar ownership lógico por superficie")
    if schema_contract.get("schema_version") != "1.0.0":
        errors.append("system_tesis_canonical_schema.yaml debe fijar schema_version=1.0.0")
    schema_entities = dict(schema_contract.get("entities", {}))
    for entity_name in ("events", "state", "derived_artifacts", "traceability_views", "memory_summary"):
        if entity_name not in schema_entities:
            errors.append(f"system_tesis_canonical_schema.yaml debe declarar la entidad {entity_name}")
    if cli_contracts.get("entrypoint") != "07_scripts/tesis.py":
        errors.append("system_tesis_cli_contracts.yaml debe apuntar a 07_scripts/tesis.py")
    cli_ids = {item.get("id") for item in cli_contracts.get("commands", [])}
    for command_id in {"status", "next", "doctor_check", "audit_check", "materialize", "publish_build", "publish_check", "source_status_check", "sync"}:
        if command_id not in cli_ids:
            errors.append(f"system_tesis_cli_contracts.yaml debe declarar el comando {command_id}")
    if dependency_map.get("dependency_direction") != "canon_hacia_derivados":
        errors.append("system_tesis_dependency_map.yaml debe fijar dependency_direction=canon_hacia_derivados")
    if "memory_projection" not in {item.get("id") for item in dependency_map.get("critical_modules", [])}:
        errors.append("system_tesis_dependency_map.yaml debe declarar memory_projection")
    for item in b0_external_gates.get("gates", []):
        if item.get("status") != "pendiente_host_real":
            errors.append(f"b0_external_gates.yaml debe mantener pendiente_host_real para {item.get('id', 'N/A')}")

    domain_ids = {item["id"] for item in domain_boundaries["dominios"]}
    for domain_id in {"personal", "profesional", "academico", "edge", "administrativo"}:
        if domain_id not in domain_ids:
            errors.append(f"domain_boundaries.yaml no contiene el dominio requerido: {domain_id}")

    if public_sync["modelo"] != "upstream_privado_downstream_publico":
        errors.append("public_private_sync_policy.yaml debe declarar el modelo upstream_privado_downstream_publico")

    if desktop_edge_sync["source_node"] != "desktop_vscode":
        errors.append("desktop_edge_sync_contract.yaml debe fijar desktop_vscode como nodo origen")
    if desktop_edge_sync["target_node"] != "orange_pi":
        errors.append("desktop_edge_sync_contract.yaml debe fijar orange_pi como nodo destino")
    if desktop_edge_sync["sync_strategy"] != "git_pull_ff_only_plus_explicit_artifacts":
        errors.append("desktop_edge_sync_contract.yaml debe declarar git_pull_ff_only_plus_explicit_artifacts")
    if "/srv/tesis/repo" != desktop_edge_sync["repo_target_on_edge"]:
        errors.append("desktop_edge_sync_contract.yaml debe apuntar a /srv/tesis/repo como clon operativo edge")
    if "edicion_primaria_en_orange_pi" not in set(desktop_edge_sync.get("forbidden_flows", [])):
        errors.append("desktop_edge_sync_contract.yaml debe prohibir la edición primaria en Orange Pi")
    sync_profile_ids = {profile.get("id") for profile in desktop_edge_sync.get("sync_profiles", [])}
    for profile_id in {"repo-only", "repo+postcheck", "repo+restart-edge"}:
        if profile_id not in sync_profile_ids:
            errors.append(f"desktop_edge_sync_contract.yaml debe declarar el perfil requerido: {profile_id}")

    if openclaw_eval["posicion"] != "capa_asistiva_opcional":
        errors.append("openclaw_evaluation_policy.yaml debe mantener a OpenClaw como capa asistiva opcional")
    if openclaw_eval["fallo_de_openclaw_no_detiene_sistema"] is not True:
        errors.append("openclaw_evaluation_policy.yaml debe declarar que el fallo de OpenClaw no detiene el sistema")

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
    artifact_sources = {artifact["source"] for artifact in publicacion["artefactos"]}
    if "MEMORY.md" not in artifact_sources:
        errors.append("publicacion.yaml debe publicar MEMORY.md como artefacto derivado oficial")
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

    memory_text = (ROOT / "MEMORY.md").read_text(encoding="utf-8")
    for marker in ("Últimos cambios validados", "Próximos pendientes críticos", "Referencias base"):
        if marker not in memory_text:
            errors.append(f"MEMORY.md no contiene el marcador requerido: {marker}")

    desktop_edge_flow = (ROOT / "docs/03_operacion/flujo-escritorio-orange-pi.md").read_text(encoding="utf-8")
    for marker in (
        "sync_repo_desde_desktop.sh",
        "pull --ff-only",
        "/srv/tesis/repo",
        "/srv/tesis/intercambio/edge/spool",
        "repo+postcheck",
        "repo+restart-edge",
    ):
        if marker not in desktop_edge_flow:
            errors.append(f"flujo-escritorio-orange-pi.md no contiene el marcador requerido: {marker}")

    domain_contract = (ROOT / "docs/02_arquitectura/contrato-maestro-de-dominios.md").read_text(encoding="utf-8")
    for marker in ("No HTTP interdominio", "Orange Pi es clon operativo", "archivo_draft"):
        if marker not in domain_contract:
            errors.append(f"contrato-maestro-de-dominios.md no contiene el marcador requerido: {marker}")

    internal_arch = (ROOT / "docs/02_arquitectura/arquitectura-interna-sistema-tesis.md").read_text(encoding="utf-8")
    for marker in ("canon", "proyecciones", "auditoria_guardrails", "publicacion"):
        if marker not in internal_arch:
            errors.append(f"arquitectura-interna-sistema-tesis.md no contiene el marcador requerido: {marker}")

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
    is_ci = os.getenv("GITHUB_ACTIONS", "").strip().lower() == "true"
    tesista_path = "00_sistema_tesis/config/tesista.json"
    if not (ROOT / tesista_path).exists():
        errors.append("Falta el archivo de identidad: tesista.json")
        return errors

    data = load_yaml_json(tesista_path)
    emails_autorizados = data.get("tesista", {}).get("identidad_digital", {}).get("emails_autorizados", [])

    # Obtener email actual de Git (en CI puede no existir configuración local de usuario)
    try:
        git_email = subprocess.check_output(["git", "config", "user.email"], text=True).strip()
        if git_email and git_email not in emails_autorizados and not is_ci:
            errors.append(f"El email de Git '{git_email}' no está en la lista de emails autorizados en tesista.json")
    except Exception:
        if not is_ci:
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
