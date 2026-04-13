from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_integration_security_policy_declares_positive_and_negative_matrix() -> None:
    payload = _load_json("manifests/domain_integration_security_policy.yaml")

    assert payload["enforcement"] == "ownership_permissions_paths"
    assert len(payload["allowed_channels"]) == 3
    assert any(item["mechanism"] == "archivo_draft" for item in payload["allowed_channels"])
    assert any(item["mechanism"] == "cli_explicita" for item in payload["allowed_channels"])
    assert any(item["mechanism"] == "spool_local" for item in payload["allowed_channels"])
    denied_ids = {item["id"] for item in payload["denied_access"]}
    assert {"edge_to_openclaw_db", "openclaw_to_edge_runtime", "cross_secret_read", "interdomain_http", "cross_domain_restore"} <= denied_ids


def test_bootstrap_and_postcheck_install_integration_security_policy() -> None:
    services_script = (ROOT / "bootstrap/orangepi/70_instalar-servicios.sh").read_text(encoding="utf-8")
    workspace_script = (ROOT / "bootstrap/orangepi/80_configurar-workspace-tesis.sh").read_text(encoding="utf-8")
    postcheck_script = (ROOT / "bootstrap/orangepi/90_postcheck.sh").read_text(encoding="utf-8")
    host_test = (ROOT / "tests/smoke/test_domain_integration_security.sh").read_text(encoding="utf-8")
    wrapper = (ROOT / "ops/seguridad/validar_integracion_entre_dominios.sh").read_text(encoding="utf-8")

    assert "domain_integration_security_policy.yaml" in services_script
    assert "chmod 0750 /srv/tesis/intercambio/openclaw/inbox" in workspace_script
    assert "validar_integracion_entre_dominios.sh" in postcheck_script
    assert "DOMAIN_INTEGRATION_SECURITY_OK" in host_test
    assert "test_domain_integration_security.sh" in wrapper


def test_domain_docs_and_contracts_forbid_direct_cross_domain_access() -> None:
    contract = _load_json("manifests/interdomain_exchange_contract.yaml")
    isolation = _load_json("manifests/domain_runtime_isolation.yaml")
    network = _load_json("manifests/domain_network_policy.yaml")
    doc = (ROOT / "docs/02_arquitectura/aislamiento-de-red-y-runtime-por-dominio.md").read_text(encoding="utf-8")

    assert contract["default_rules"]["http_entre_dominios"] is False
    assert network["default_policy"]["allow_cross_domain_sqlite"] is False
    assert "/var/lib/edge-iot/runtime" in isolation["dominios"]["edge_iot"]["rutas_read_write"]
    assert "nada de lectura libre entre workspaces ni acceso directo a SQLite de otros dominios" in doc


def test_operational_topology_manifest_declares_desktop_first_edge_model() -> None:
    payload = _load_json("manifests/operational_topology.yaml")

    assert payload["primary_authoring_node"] == "desktop_vscode"
    assert payload["edge_execution_node"] == "orange_pi"
    assert payload["integration_mode"] == "git_and_artifacts"
    assert "git_sync" in payload["allowed_remote_operations"]
    assert "artefactos_generados" in payload["allowed_remote_operations"]
    assert "workspace_montado_por_red_como_flujo_normal" in payload["forbidden_remote_operations"]


def test_docs_describe_desktop_first_and_orange_pi_edge_roles() -> None:
    architecture = (ROOT / "docs/02_arquitectura/arquitectura-general.md").read_text(encoding="utf-8")
    manual = (ROOT / "00_sistema_tesis/manual_operacion_humana.md").read_text(encoding="utf-8")
    storage = (ROOT / "docs/02_arquitectura/topologia-de-almacenamiento.md").read_text(encoding="utf-8")

    assert "desktop_workspace" in architecture
    assert "orange_pi_edge" in architecture
    assert "git_sync" in architecture
    assert "workspace remoto montado por red" in manual
    assert "clon operativo local de despliegue y supervisión" in manual
    assert "clon operativo para despliegue, supervision y ejecucion local" in storage


def test_host_script_exercises_positive_and_negative_cases() -> None:
    host_test = (ROOT / "tests/smoke/test_domain_integration_security.sh").read_text(encoding="utf-8")
    wrapper = (ROOT / "ops/seguridad/validar_integracion_entre_dominios.sh").read_text(encoding="utf-8")

    assert "t036_openclaw_draft.txt" in host_test
    assert "t036_edge_spool.txt" in host_test
    assert "openclaw_local.py --help" in host_test
    assert "cat /etc/tesis-os/domains/academico.env" in host_test
    assert "http://127.0.0.1:18789" in host_test
    assert "restaurar_desde_emmc.sh --domain edge_iot" in host_test
    assert "DOMAIN_INTEGRATION_SECURITY_OK" in wrapper
    assert "domain_integration_security_report_" in wrapper
