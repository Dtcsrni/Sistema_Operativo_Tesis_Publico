from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_edge_resilience_policy_and_manifests_exist() -> None:
    policy = _load_json("manifests/edge_iot_resilience_policy.yaml")
    matrix = _load_json("manifests/service_matrix.yaml")
    isolation = _load_json("manifests/domain_runtime_isolation.yaml")
    services = {item["id"]: item for item in matrix["servicios"]}

    assert policy["strategy"] == "watchdog_hibrido"
    assert "quarantined" in policy["states"]
    assert services["edge-iot-watchdog"]["dominio"] == "edge_iot"
    assert services["edge-iot-watchdog"]["usuario"] == "edgeiot"
    assert "edge-iot-watchdog" in isolation["dominios"]["edge_iot"]["servicios"]
    assert "/var/lib/edge-iot/runtime" in isolation["dominios"]["edge_iot"]["rutas_read_write"]


def test_edge_env_and_scripts_define_runtime_heartbeat_and_quarantine_controls() -> None:
    env_file = (ROOT / "config/env/edge-iot.env.example").read_text(encoding="utf-8")
    run_script = (ROOT / "ops/edge/edge-iot-run.sh").read_text(encoding="utf-8")
    health = (ROOT / "ops/edge/edge-iot-healthcheck.sh").read_text(encoding="utf-8")
    watchdog = (ROOT / "ops/edge/edge-iot-watchdog.sh").read_text(encoding="utf-8")
    helper = (ROOT / "ops/edge/edge-iot-resilience.sh").read_text(encoding="utf-8")

    assert "EDGE_IOT_RUNTIME_DIR=/var/lib/edge-iot/runtime" in env_file
    assert "EDGE_IOT_QUARANTINE_SEC=1800" in env_file
    assert "heartbeat.timestamp" in run_script
    assert "force_soft_failure" in health
    assert "edge_iot_enter_quarantine" in watchdog
    assert "clear-quarantine" in helper
    assert "simulate-soft-failure" in helper


def test_edge_watchdog_systemd_units_are_isolated() -> None:
    service = (ROOT / "config/systemd/edge-iot-watchdog.service").read_text(encoding="utf-8")
    timer = (ROOT / "config/systemd/edge-iot-watchdog.timer").read_text(encoding="utf-8")
    smoke = (ROOT / "tests/smoke/test_edge_resilience.sh").read_text(encoding="utf-8")

    assert "User=edgeiot" in service
    assert "Group=edgeiot" in service
    assert "ReadWritePaths=/var/lib/edge-iot /var/log/edge-iot /srv/tesis/workspace/edge /srv/tesis/intercambio/edge" in service
    assert "OnUnitActiveSec=2min" in timer
    assert "edge-iot-watchdog.service" in smoke


def test_observability_and_docs_include_resilience_signals() -> None:
    collector = (ROOT / "ops/observabilidad/recolectar-metricas.sh").read_text(encoding="utf-8")
    docs = (ROOT / "docs/03_operacion/servicio-edge-iot.md").read_text(encoding="utf-8")
    flow = (ROOT / "00_sistema_tesis/documentacion_sistema/flujos_operativos.md").read_text(encoding="utf-8")

    assert "tesis_edge_resilience_state" in collector
    assert "tesis_edge_resilience_quarantined" in collector
    assert "clear-quarantine" in docs
    assert "Flujo 8. Recuperar `edge_iot` tras degradación o cuarentena" in flow
