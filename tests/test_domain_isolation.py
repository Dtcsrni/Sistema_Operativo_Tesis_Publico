from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_domain_runtime_isolation_manifest_declares_expected_domains() -> None:
    payload = _load_json("manifests/domain_runtime_isolation.yaml")
    domains = payload["dominios"]

    assert payload["baseline"] == "mixto_fuerte"
    assert {"sistema_tesis", "openclaw", "edge_iot", "administrativo", "personal"} == set(domains.keys())
    assert domains["openclaw"]["usuario"] == "openclaw"
    assert "/srv/tesis/intercambio/openclaw" in domains["openclaw"]["rutas_read_write"]


def test_domain_network_policy_blocks_http_between_domains() -> None:
    payload = _load_json("manifests/domain_network_policy.yaml")

    assert payload["default_policy"]["allow_interdomain_http"] is False
    assert payload["default_policy"]["allow_cross_domain_sqlite"] is False
    assert payload["dominios"]["openclaw"] == "egress_controlado_localhost_in"


def test_interdomain_exchange_contract_uses_only_file_cli_spool_mechanisms() -> None:
    payload = _load_json("manifests/interdomain_exchange_contract.yaml")
    mechanisms = {item["mechanism"] for item in payload["channels"]}

    assert payload["default_rules"]["http_entre_dominios"] is False
    assert mechanisms <= {"archivo_draft", "cli_explicita", "spool_local"}


def test_integration_security_policy_is_present_in_repo() -> None:
    payload = _load_json("manifests/domain_integration_security_policy.yaml")

    assert payload["defaults"]["allow_interdomain_http"] is False
    assert payload["defaults"]["allow_cross_domain_sqlite"] is False


def test_service_matrix_declares_ownership_and_hardening() -> None:
    payload = _load_json("manifests/service_matrix.yaml")
    services = {item["id"]: item for item in payload["servicios"]}

    assert services["openclaw-gateway"]["usuario"] == "openclaw"
    assert services["tesis-healthcheck"]["usuario"] == "tesis"
    assert services["tesis-backup"]["usuario"] == "tesisadmin"
    assert services["openclaw-gateway"]["hardening"]["protect_system"] == "strict"


def test_storage_layout_declares_interdomain_exchange_paths() -> None:
    payload = _load_json("manifests/storage_layout.yaml")

    assert payload["politicas"]["desktop_first"] is True
    assert payload["politicas"]["intercambio_interdominio_solo_por_rutas_explicitas"] is True
    assert payload["topologia_operativa"]["primary_authoring_node"] == "desktop_vscode"
    assert payload["topologia_operativa"]["edge_execution_node"] == "orange_pi"
    assert "/srv/tesis/intercambio/openclaw/spool" in payload["intercambio"]["canales"]


def test_systemd_units_include_domain_hardening_controls() -> None:
    openclaw_unit = (ROOT / "config/systemd/openclaw-gateway.service").read_text(encoding="utf-8")
    backup_unit = (ROOT / "config/systemd/tesis-backup.service").read_text(encoding="utf-8")

    assert "User=openclaw" in openclaw_unit
    assert "Group=openclaw" in openclaw_unit
    assert "NoNewPrivileges=yes" in openclaw_unit
    assert "ProtectSystem=strict" in openclaw_unit
    assert "ReadWritePaths=/var/lib/herramientas/openclaw" in openclaw_unit
    assert "User=tesisadmin" in backup_unit
    assert "RestrictAddressFamilies=AF_UNIX" in backup_unit


def test_bootstrap_creates_domain_users_and_exchange_directories() -> None:
    workspace_script = (ROOT / "bootstrap/orangepi/80_configurar-workspace-tesis.sh").read_text(encoding="utf-8")
    services_script = (ROOT / "bootstrap/orangepi/70_instalar-servicios.sh").read_text(encoding="utf-8")
    postcheck_script = (ROOT / "bootstrap/orangepi/90_postcheck.sh").read_text(encoding="utf-8")

    assert "useradd --system --gid openclaw" in workspace_script
    assert "useradd --system --gid edgeiot" in workspace_script
    assert "useradd --system --gid tesisadmin" in workspace_script
    assert "/srv/tesis/intercambio/openclaw/spool" in workspace_script
    assert "domain_runtime_isolation.yaml" in services_script
    assert "test_domain_isolation.sh" in postcheck_script
