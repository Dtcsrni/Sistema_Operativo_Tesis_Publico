from __future__ import annotations

import sys

from common import ROOT, load_yaml_json


REQUIRED_PATHS = [
    "docs/02_arquitectura/contrato-maestro-de-dominios.md",
    "docs/02_arquitectura/arquitectura-interna-sistema-tesis.md",
    "docs/02_arquitectura/arquitectura-objetivo-b0-desktop-first.md",
    "docs/04_seguridad/modelo-de-amenazas-sistema-documental.md",
    "docs/05_reproducibilidad/migraciones-canonicas.md",
    "manifests/system_tesis_architecture_contract.yaml",
    "manifests/system_tesis_canonical_schema.yaml",
    "manifests/system_tesis_cli_contracts.yaml",
    "manifests/b0_external_gates.yaml",
]


def _load_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def validate() -> list[str]:
    errors: list[str] = []

    for rel_path in REQUIRED_PATHS:
        if not (ROOT / rel_path).exists():
            errors.append(f"Falta la ruta requerida para B0: {rel_path}")

    if errors:
        return errors

    runtime = load_yaml_json("manifests/domain_runtime_isolation.yaml")
    network = load_yaml_json("manifests/domain_network_policy.yaml")
    backup = load_yaml_json("manifests/domain_backup_policy.yaml")
    services = load_yaml_json("manifests/service_matrix.yaml")
    exchanges = load_yaml_json("manifests/interdomain_exchange_contract.yaml")
    architecture = load_yaml_json("manifests/system_tesis_architecture_contract.yaml")
    schema = load_yaml_json("manifests/system_tesis_canonical_schema.yaml")
    cli = load_yaml_json("manifests/system_tesis_cli_contracts.yaml")
    gates = load_yaml_json("manifests/b0_external_gates.yaml")

    runtime_domains = runtime["dominios"]
    network_profiles = set(network["profiles"].keys())
    domain_to_profile = network["dominios"]
    service_rows = services["servicios"]
    service_ids = {item["id"] for item in service_rows}

    expected_runtime_secrets = {
        "sistema_tesis": [],
        "openclaw": [
            "/etc/tesis-os/openclaw.env",
            "/etc/tesis-os/domains/academico.env",
            "/etc/tesis-os/domains/profesional.env",
        ],
        "edge_iot": ["/etc/tesis-os/edge-iot.env"],
        "administrativo": ["/etc/tesis-os/domains/administrativo.env", "/etc/tesis-os/observabilidad.env"],
        "personal": ["/etc/tesis-os/domains/personal.env"],
    }

    for domain_id, expected in expected_runtime_secrets.items():
        actual = runtime_domains[domain_id]["secretos"]
        if actual != expected:
            errors.append(f"Secretos inconsistentes para {domain_id}: {actual} != {expected}")

    for domain_id, payload in runtime_domains.items():
        profile = payload["network_profile"]
        if profile not in network_profiles:
            errors.append(f"{domain_id} referencia un network_profile inexistente: {profile}")
        if domain_to_profile.get(domain_id) != profile:
            errors.append(f"{domain_id} no coincide entre domain_runtime_isolation y domain_network_policy")

    for row in service_rows:
        profile = row["network_profile"]
        if profile not in network_profiles:
            errors.append(f"El servicio {row['id']} usa un network_profile inexistente: {profile}")

    services_by_domain: dict[str, set[str]] = {}
    for row in service_rows:
        services_by_domain.setdefault(row["dominio"], set()).add(row["id"])
    for domain_id, payload in runtime_domains.items():
        expected_services = set(payload["servicios"])
        actual_services = services_by_domain.get(domain_id, set())
        if expected_services != actual_services:
            errors.append(
                f"Servicios inconsistentes para {domain_id}: runtime={sorted(expected_services)} matrix={sorted(actual_services)}"
            )

    expected_channels = {
        "openclaw_drafts": "archivo_draft",
        "openclaw_requests": "cli_explicita",
        "edge_spool": "spool_local",
    }
    channels = {item["id"]: item["mechanism"] for item in exchanges["channels"]}
    if channels != expected_channels:
        errors.append(f"Canales interdominio inconsistentes: {channels}")

    defaults = exchanges["default_rules"]
    if defaults["http_entre_dominios"] is not False:
        errors.append("interdomain_exchange_contract debe prohibir HTTP entre dominios")
    if defaults["db_compartida_directa"] is not False:
        errors.append("interdomain_exchange_contract debe prohibir DB compartida directa")

    for domain_id in ("sistema_tesis", "openclaw", "edge_iot"):
        if domain_id not in backup["domains"]:
            errors.append(f"domain_backup_policy no contiene el dominio requerido: {domain_id}")
    edge_backup = backup["domains"].get("edge_iot", {})
    if "/etc/tesis-os/edge-iot.env" not in edge_backup.get("include_paths", []):
        errors.append("domain_backup_policy debe respaldar /etc/tesis-os/edge-iot.env")
    if edge_backup.get("validation_gate") != "host_real_requerido":
        errors.append("edge_iot debe declararse como host_real_requerido en backup policy")

    layer_ids = [item["id"] for item in architecture["layers"]]
    if layer_ids != ["canon", "proyecciones", "auditoria_guardrails", "publicacion"]:
        errors.append(f"Capas de arquitectura inesperadas: {layer_ids}")
    if architecture["desktop_first"] is not True:
        errors.append("system_tesis_architecture_contract debe ser desktop_first")
    for coupling in (
        "edge_iot_to_canon_write",
        "publicacion_to_canon_write",
        "proyecciones_as_source_of_truth",
        "orange_pi_as_primary_authoring_node",
    ):
        if coupling not in architecture["forbidden_couplings"]:
            errors.append(f"Falta acoplamiento prohibido en architecture contract: {coupling}")

    if schema["schema_version"] != "1.0.0":
        errors.append("system_tesis_canonical_schema debe declarar schema_version 1.0.0")
    if schema["compatibility"]["breaking_change_requires_major_bump"] is not True:
        errors.append("system_tesis_canonical_schema debe forzar major bump en cambios breaking")
    if schema["migration_policy"]["requires_explicit_record"] is not True:
        errors.append("system_tesis_canonical_schema debe exigir registro explicito de migracion")

    expected_cli_ids = {
        "status",
        "next",
        "doctor_check",
        "publish_build",
        "publish_check",
        "source_status_check",
        "sync",
    }
    cli_ids = {item["id"] for item in cli["commands"]}
    if cli_ids != expected_cli_ids:
        errors.append(f"system_tesis_cli_contracts no coincide con los comandos esperados: {sorted(cli_ids)}")

    expected_gate_ids = {
        "host_runtime_isolation_validation",
        "host_restore_validation",
        "host_benchmark_edge_iot",
        "host_go_no_go_orange_pi",
    }
    gate_ids = {item["id"] for item in gates["gates"]}
    if gate_ids != expected_gate_ids:
        errors.append(f"b0_external_gates no coincide con los gates esperados: {sorted(gate_ids)}")
    for item in gates["gates"]:
        if item["status"] != "pendiente_host_real":
            errors.append(f"El gate {item['id']} debe quedar en pendiente_host_real")

    doc_markers = {
        "docs/02_arquitectura/contrato-maestro-de-dominios.md": [
            "No HTTP interdominio",
            "Orange Pi es clon operativo",
            "archivo_draft",
        ],
        "docs/02_arquitectura/arquitectura-interna-sistema-tesis.md": [
            "canon",
            "proyecciones",
            "auditoria_guardrails",
            "publicacion",
        ],
        "docs/04_seguridad/modelo-de-amenazas-sistema-documental.md": [
            "Canon privado",
            "bundle publico",
            "Orange Pi",
        ],
        "docs/02_arquitectura/arquitectura-objetivo-b0-desktop-first.md": [
            "Gates externos",
            "Orange Pi",
            "ENT-013",
        ],
    }
    for rel_path, markers in doc_markers.items():
        content = _load_text(rel_path)
        for marker in markers:
            if marker not in content:
                errors.append(f"{rel_path} no contiene el marcador requerido: {marker}")

    for script in architecture["critical_scripts"]:
        if script not in {"07_scripts/tesis.py", "07_scripts/build_all.py", "07_scripts/validate_structure.py", "07_scripts/validate_b0_architecture.py"}:
            errors.append(f"Script critico inesperado en architecture contract: {script}")
        if not (ROOT / script).exists():
            errors.append(f"No existe el script critico declarado: {script}")

    if "07_scripts/validate_b0_architecture.py" not in architecture["critical_scripts"]:
        errors.append("architecture contract debe declarar validate_b0_architecture.py como script critico")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("B0_ARCH: ERROR")
        for item in errors:
            print(f"- {item}")
        return 1

    print("B0_ARCH: OK")
    print("Desktop-first, contratos internos y gates externos consistentes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
