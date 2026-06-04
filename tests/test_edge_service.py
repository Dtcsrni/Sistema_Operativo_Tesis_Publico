from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_edge_service_manifest_entry_is_present() -> None:
    payload = _load_json("manifests/service_matrix.yaml")
    services = {item["id"]: item for item in payload["servicios"]}
    service = services["siot-edge"]

    assert service["dominio"] == "edge_iot"
    assert service["usuario"] == "edge_ops"
    assert service["healthcheck"]["type"] == "script"
    assert "openclaw-gateway" not in service["dependencias"]


def test_edge_service_unit_is_hardened_and_uses_edge_env() -> None:
    unit = (ROOT / "config/systemd/siot-edge.service").read_text(encoding="utf-8")

    assert "EnvironmentFile=/srv/tesis/repo/config/env/domains/edge.env" in unit
    assert "User=edge_ops" in unit
    assert "Group=docker" in unit
    assert "Restart=always" in unit
    assert "NoNewPrivileges=yes" in unit
    assert "PrivateTmp=yes" in unit


def test_edge_service_wrappers_exist_and_do_not_use_http_healthchecks() -> None:
    run_script = (ROOT / "ops/edge/edge-iot-run.sh").read_text(encoding="utf-8")
    preflight = (ROOT / "ops/edge/edge-iot-preflight.sh").read_text(encoding="utf-8")
    health = (ROOT / "ops/edge/edge-iot-healthcheck.sh").read_text(encoding="utf-8")

    assert "EDGE_IOT_COMMAND" in run_script
    assert "EDGE_IOT_HEALTHCHECK_CMD" in preflight
    assert "systemctl is-active --quiet siot-edge.service" in health
    assert "http" not in health.lower()


def test_bootstrap_and_postcheck_install_edge_service() -> None:
    install = (ROOT / "bootstrap/orangepi/70_instalar-servicios.sh").read_text(encoding="utf-8")
    workspace = (ROOT / "bootstrap/orangepi/80_configurar-workspace-tesis.sh").read_text(encoding="utf-8")
    postcheck = (ROOT / "bootstrap/orangepi/90_postcheck.sh").read_text(encoding="utf-8")
    smoke = (ROOT / "tests/smoke/test_edge_service.sh").read_text(encoding="utf-8")

    assert "edge-iot.env" in install
    assert "siot-edge.service" in install
    assert "/srv/tesis/workspace/edge" in workspace
    assert "test_edge_service.sh" in postcheck
    assert "Restart=always" in smoke
