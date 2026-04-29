from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_observability_manifests_declare_local_prometheus_stack() -> None:
    policy = _load_json("manifests/observability_policy.yaml")
    retention = _load_json("manifests/log_retention_policy.yaml")
    targets = _load_json("manifests/prometheus_targets.yaml")
    negatives = _load_json("manifests/observability_negative_checks.yaml")

    assert policy["stack"] == "prometheus_local"
    assert policy["metricas"]["prometheus"]["listen"] == "127.0.0.1:9090"
    assert policy["metricas"]["node_exporter"]["listen"] == "127.0.0.1:9100"
    assert retention["retention_class"] == "larga"
    assert retention["policy"]["rotate"] == 90
    assert any(item["job_name"] == "node_exporter_local" for item in targets["targets"])
    assert "ningun_exporter_usa_http_interdominio" in negatives["checks"]


def test_service_matrix_and_runtime_isolation_include_observability_services() -> None:
    matrix = _load_json("manifests/service_matrix.yaml")
    isolation = _load_json("manifests/domain_runtime_isolation.yaml")
    storage = _load_json("manifests/storage_layout.yaml")
    services = {item["id"]: item for item in matrix["servicios"]}

    assert "prometheus" in services
    assert "prometheus-node-exporter" in services
    assert "tesis-observabilidad-collector" in services
    assert services["prometheus"]["network_profile"] == "solo_localhost_observabilidad"
    assert services["tesis-observabilidad-collector"]["usuario"] == "tesisadmin"
    assert "prometheus" in isolation["dominios"]["administrativo"]["servicios"]
    assert storage["observabilidad"]["node_exporter_textfile"] == "/var/lib/node_exporter/textfile_collector"


def test_bootstrap_and_smoke_install_observability_stack() -> None:
    install = (ROOT / "bootstrap/orangepi/74_instalar-observabilidad.sh").read_text(encoding="utf-8")
    services = (ROOT / "bootstrap/orangepi/70_instalar-servicios.sh").read_text(encoding="utf-8")
    workspace = (ROOT / "bootstrap/orangepi/80_configurar-workspace-tesis.sh").read_text(encoding="utf-8")
    postcheck = (ROOT / "bootstrap/orangepi/90_postcheck.sh").read_text(encoding="utf-8")
    smoke = (ROOT / "tests/smoke/test_observability_stack.sh").read_text(encoding="utf-8")

    assert "apt-get install -y prometheus prometheus-node-exporter logrotate" in install
    assert "/var/log/tesis-admin/prometheus.log" in install
    assert "/var/log/tesis-os/tesis-healthcheck.log" in install
    assert "observability_policy.yaml" in services
    assert "/var/lib/node_exporter/textfile_collector" in workspace
    assert "groupadd --system observabilidad" in workspace
    assert "/var/log/tesis-admin/observability-collector.log" in workspace
    assert "/var/log/edge-iot/edge-iot-watchdog.log" in workspace
    assert "test_observability_stack.sh" in postcheck
    assert "127.0.0.1:9090" in smoke


def test_systemd_units_and_overrides_append_logs_and_bind_localhost() -> None:
    openclaw = (ROOT / "config/systemd/openclaw-gateway.service").read_text(encoding="utf-8")
    edge = (ROOT / "config/systemd/edge-iot-worker.service").read_text(encoding="utf-8")
    health = (ROOT / "config/systemd/tesis-healthcheck.service").read_text(encoding="utf-8")
    backup = (ROOT / "config/systemd/tesis-backup.service").read_text(encoding="utf-8")
    collector = (ROOT / "config/systemd/tesis-observabilidad-collector.service").read_text(encoding="utf-8")
    prom_override = (ROOT / "config/systemd-overrides/prometheus.service.d/override.conf").read_text(encoding="utf-8")
    node_override = (ROOT / "config/systemd-overrides/prometheus-node-exporter.service.d/override.conf").read_text(encoding="utf-8")

    assert "StandardOutput=append:/var/log/openclaw/openclaw-gateway.log" in openclaw
    assert "StandardOutput=append:/var/log/edge-iot/edge-iot-worker.log" in edge
    assert "StandardOutput=append:/var/log/tesis-os/tesis-healthcheck.log" in health
    assert "StandardOutput=append:/var/log/tesis-admin/tesis-backup.log" in backup
    assert "EnvironmentFile=/etc/tesis-os/observabilidad.env" in collector
    assert "127.0.0.1:9090" in prom_override
    assert "127.0.0.1:9100" in node_override
    assert "collector.textfile.directory=/var/lib/node_exporter/textfile_collector" in node_override


def test_logrotate_and_collector_scripts_cover_all_domains_without_http() -> None:
    logrotate = (ROOT / "config/logrotate/tesis-observabilidad").read_text(encoding="utf-8")
    collector = (ROOT / "ops/observabilidad/recolectar-metricas.sh").read_text(encoding="utf-8")
    flow = (ROOT / "00_sistema_tesis/documentacion_sistema/flujos_operativos.md").read_text(encoding="utf-8")

    assert "/var/log/tesis-os/*.log" in logrotate
    assert "/var/log/openclaw/*.log" in logrotate
    assert "/var/log/edge-iot/*.log" in logrotate
    assert "/var/log/tesis-admin/*.log" in logrotate
    assert "openclaw.prom" in collector
    assert "edge-iot.prom" in collector
    assert "http" not in collector.lower()
    assert "Flujo 7. Observar salud y métricas por dominio" in flow
