from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request

from common import ROOT, file_sha256, load_yaml_json, relative_posix


SNAPSHOT_PRIVATE_PATH = "00_sistema_tesis/config/observability_dashboard_snapshot.json"
SNAPSHOT_PUBLIC_PATH = "06_dashboard/generado/observability_status_public.json"
STALE_AFTER_SECONDS = 300


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_now() -> str:
    return utc_now().isoformat(timespec="seconds")


def run_probe(command: list[str], timeout: float = 2.0) -> dict[str, Any]:
    started = time.perf_counter()
    if not command or shutil.which(command[0]) is None:
        return {
            "status": "unknown",
            "detail": f"command_not_available:{command[0] if command else 'empty'}",
            "latency_ms": 0,
        }
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "status": "degraded",
            "detail": "timeout",
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    except Exception as exc:  # pragma: no cover - defensive guard for host-specific probes
        return {
            "status": "unknown",
            "detail": f"{type(exc).__name__}:{exc}",
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    output = (result.stdout or result.stderr or "").strip().splitlines()
    return {
        "status": "ok" if result.returncode == 0 else "degraded",
        "detail": output[0][:240] if output else f"returncode={result.returncode}",
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
    }


def probe_tcp(url_or_host: str, default_port: int = 80, timeout: float = 1.0) -> dict[str, Any]:
    target = url_or_host.strip()
    if not target:
        return {"status": "unknown", "detail": "not_configured", "latency_ms": 0}
    target = target.removeprefix("http://").removeprefix("https://").split("/", 1)[0]
    if ":" in target:
        host, raw_port = target.rsplit(":", 1)
        try:
            port = int(raw_port)
        except ValueError:
            port = default_port
    else:
        host, port = target, default_port
    started = time.perf_counter()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except (OSError, ValueError) as exc:
        return {
            "status": "down",
            "detail": f"{host}:{port} {type(exc).__name__}",
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }
    return {
        "status": "ok",
        "detail": f"{host}:{port}",
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
    }


def read_json(relative_path: str, default: Any) -> Any:
    path = ROOT / relative_path
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def load_env(relative_path: str) -> dict[str, str]:
    path = ROOT / relative_path
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def service_probe(service: dict[str, Any]) -> dict[str, Any]:
    service_id = str(service.get("id") or "unknown")
    service_type = str(service.get("tipo") or "")
    if os.getenv("SIOT_OBSERVABILITY_DEEP_HOST_PROBES", "0").strip() not in {"1", "true", "yes", "on"}:
        return {"status": "unknown", "detail": "deep_host_probe_disabled", "latency_ms": 0}
    if service_type.startswith("systemd"):
        return run_probe(["systemctl", "is-active", service_id if service_id.endswith((".service", ".timer")) else f"{service_id}.service"])
    if shutil.which("docker") is not None:
        result = run_probe(["docker", "inspect", "-f", "{{.State.Status}}", service_id])
        if result["status"] == "ok" and result["detail"] == "running":
            return result
    return {"status": "unknown", "detail": "no_host_probe_available", "latency_ms": 0}


def normalize_status(raw_status: str, *, stale: bool = False, blocked: bool = False) -> str:
    if blocked:
        return "blocked_human_validation"
    if stale:
        return "stale"
    normalized = (raw_status or "").lower()
    if normalized in {"ok", "healthy", "running", "active", "ready"}:
        return "ok"
    if normalized in {"down", "failed", "critical", "unavailable", "caido"}:
        return "down"
    if normalized in {"degraded", "warning", "standby"}:
        return "degraded"
    return "unknown"


def status_rank(status: str) -> int:
    order = {
        "down": 0,
        "blocked_human_validation": 1,
        "stale": 2,
        "degraded": 3,
        "unknown": 4,
        "ok": 5,
    }
    return order.get(status, 4)


def worst_status(items: list[dict[str, Any]]) -> str:
    if not items:
        return "unknown"
    return min((str(item.get("status") or "unknown") for item in items), key=status_rank)


def snapshot_age_seconds(relative_path: str) -> int | None:
    path = ROOT / relative_path
    if not path.exists():
        return None
    return int(max(time.time() - path.stat().st_mtime, 0))


def source_record(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    record = {
        "path": relative_path,
        "exists": path.exists(),
        "sha256": "",
        "updated_at": "",
    }
    if path.exists() and path.is_file():
        record["sha256"] = file_sha256(relative_path)
        record["updated_at"] = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat(timespec="seconds")
    return record


def build_services() -> list[dict[str, Any]]:
    matrix = load_yaml_json("manifests/service_matrix.yaml")
    services: list[dict[str, Any]] = []
    for item in matrix.get("servicios", []):
        probe = service_probe(item)
        services.append(
            {
                "id": item.get("id", "unknown"),
                "domain": item.get("dominio", "unknown"),
                "type": item.get("tipo", "unknown"),
                "criticality": item.get("criticidad", "unknown"),
                "status": normalize_status(str(probe["status"])),
                "last_check": iso_now(),
                "latency_ms": probe.get("latency_ms", 0),
                "detail": probe.get("detail", ""),
                "diagnostic_request": {
                    "orchestrator": "openclaw",
                    "intent": "diagnose_service",
                    "service_id": item.get("id", "unknown"),
                    "requires_human_approval": True,
                },
                "dependencies": item.get("dependencias", []),
                "source": "manifests/service_matrix.yaml",
            }
        )
    return services


def build_compose_stack() -> list[dict[str, Any]]:
    compose = load_yaml_json("docker-compose.yml")
    rows: list[dict[str, Any]] = []
    probe_dns = os.getenv("SIOT_OBSERVABILITY_PROBE_COMPOSE_DNS", "").strip().lower() in {"1", "true", "yes", "on"}
    probe_dns = probe_dns or os.getenv("SISTEMA_TESIS_RUNTIME", "") == "docker-observability-command-center"
    for service_id, service in compose.get("services", {}).items():
        ports = service.get("ports", []) or []
        internal_port = ""
        if ports:
            raw_port = str(ports[0])
            internal_port = raw_port.rsplit(":", 1)[-1].split("/", 1)[0]
        probe = {"status": "unknown", "detail": "sin puerto interno declarado", "latency_ms": 0}
        if probe_dns and internal_port.isdigit():
            probe = probe_tcp(f"{service_id}:{internal_port}", default_port=int(internal_port), timeout=1.0)
        rows.append(
            {
                "id": service_id,
                "status": normalize_status(str(probe["status"])),
                "image": service.get("image", "build-local"),
                "ports": ports,
                "internal_port": internal_port,
                "depends_on": sorted((service.get("depends_on") or {}).keys()) if isinstance(service.get("depends_on"), dict) else service.get("depends_on", []),
                "latency_ms": probe.get("latency_ms", 0),
                "detail": probe.get("detail", ""),
                "source": "docker-compose.yml",
            }
        )
    return rows


def build_nodes(services: list[dict[str, Any]]) -> list[dict[str, Any]]:
    topology = load_yaml_json("manifests/operational_topology.yaml")
    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    openclaw_status = read_json("00_sistema_tesis/config/openclaw_status.json", {})
    pc_services = [service for service in services if service["domain"] in {"sistema_tesis", "openclaw", "administrativo"}]
    edge_services = [service for service in services if service["domain"] == "edge_iot"]
    return [
        {
            "id": "pc_hub",
            "label": "PC Hub",
            "role": sistema.get("nodos_distribuidos", {}).get("pc_hub", {}).get("rol", "coordinacion"),
            "status": worst_status(pc_services),
            "services": [service["id"] for service in pc_services],
            "host": openclaw_status.get("host", {}),
            "source": "00_sistema_tesis/config/sistema_tesis.yaml",
        },
        {
            "id": "orange_pi_edge",
            "label": "Orange Pi Edge",
            "role": topology.get("node_roles", {}).get("orange_pi_edge", {}).get("responsibilities", []),
            "status": worst_status(edge_services),
            "services": [service["id"] for service in edge_services],
            "host": topology.get("edge_hostname", "tesis-edge"),
            "source": "manifests/operational_topology.yaml",
        },
    ]


def build_runtime(env: dict[str, str]) -> dict[str, Any]:
    openclaw_status = read_json("00_sistema_tesis/config/openclaw_status.json", {})
    serena_probe = probe_tcp(env.get("OPENCLAW_SERENA_URL", "http://127.0.0.1:8765/mcp"), timeout=0.8)
    caveman_status = run_probe(["bash", "-lc", "command -v caveman >/dev/null && caveman --help >/dev/null"], timeout=3)
    telegram_probe = run_probe(["bash", "-lc", "test -n \"${OPENCLAW_TELEGRAM_BOT_TOKEN:-}\""], timeout=1)
    endpoints = [
        {
            "id": "desktop_compute",
            "label": "Desktop Compute",
            "probe": probe_tcp(env.get("OPENCLAW_DESKTOP_RUNTIME_BASE_URL", "http://127.0.0.1:21434")),
            "source": "config/env/openclaw.env",
        },
        {
            "id": "edge_ollama",
            "label": "Edge Ollama",
            "probe": probe_tcp(env.get("OPENCLAW_EDGE_OLLAMA_BASE_URL", "")),
            "source": "config/env/openclaw.env",
        },
        {
            "id": "serena_http",
            "label": "Serena HTTP",
            "probe": probe_tcp(env.get("OPENCLAW_SERENA_URL", "http://127.0.0.1:8765/mcp")),
            "source": "config/env/openclaw.env",
        },
    ]
    for endpoint in endpoints:
        endpoint["status"] = normalize_status(str(endpoint["probe"]["status"]))
    return {
        "orchestrator": "OpenClaw",
        "state": openclaw_status.get("state", "unknown"),
        "active_runtime": openclaw_status.get("active_runtime", "unknown"),
        "openclaw_status": normalize_status(openclaw_status.get("preflight", {}).get("status", "unknown")),
        "serena_status": normalize_status(str(serena_probe["status"])),
        "caveman_status": normalize_status(str(caveman_status["status"])),
        "telegram_status": normalize_status(str(telegram_probe["status"])),
        "endpoints": endpoints,
        "sources": ["00_sistema_tesis/config/openclaw_status.json", "config/env/openclaw.env"],
    }


def build_benchmarks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for node, path in {
        "pc_control": "runtime/pc_control/benchmarks/index.json",
        "edge_iot": "runtime/edge_iot/benchmarks/index.json",
    }.items():
        payload = read_json(path, {})
        age = snapshot_age_seconds(path)
        status = normalize_status(
            str(payload.get("latest_status") or "unknown"),
            stale=age is not None and age > 86400,
        )
        rows.append(
            {
                "node": node,
                "status": status,
                "latest_run_id": payload.get("latest_run_id", "n/a"),
                "latest_validity": payload.get("latest_scientific_validity", "unknown"),
                "latest_record_hash": payload.get("latest_record_hash", ""),
                "age_seconds": age,
                "source": path,
            }
        )
    return rows


def build_publication() -> dict[str, Any]:
    manifest_path = "06_dashboard/publico/manifest_publico.json"
    manifest = read_json(manifest_path, {})
    age = snapshot_age_seconds(manifest_path)
    return {
        "status": normalize_status("ok" if manifest else "unknown", stale=age is not None and age > 86400),
        "bundle_path": "06_dashboard/publico/",
        "manifest_exists": bool(manifest),
        "age_seconds": age,
        "files": len(manifest.get("archivos", [])) if isinstance(manifest, dict) else 0,
        "source": manifest_path,
    }


def build_flows() -> list[dict[str, Any]]:
    return [
        {
            "id": "retoma",
            "title": "Retomar operacion",
            "status": "ok",
            "objective": "Confirmar estado base antes de trabajo tecnico.",
            "prechecks": ["Serena recomendado", "Caveman disponible", "repo sin bloqueo critico"],
            "request": "OpenClaw: preparar diagnostico de retoma sin ejecutar cambios.",
            "ok_criteria": "status, source status y next responden sin error critico.",
            "rollback": "Continuar por filesystem y registrar bloqueo operativo.",
        },
        {
            "id": "arranque",
            "title": "Arranque stack",
            "status": "unknown",
            "objective": "Levantar servicios PC/Edge requeridos para observabilidad.",
            "prechecks": ["token LAN configurado", "env privado cargado", "puertos libres"],
            "request": "OpenClaw: preparar solicitud de arranque con impacto y servicios afectados.",
            "ok_criteria": "servicios criticos en OK o degradado justificado.",
            "rollback": "Detener solo servicios iniciados en la solicitud aprobada.",
        },
        {
            "id": "sync_pc_edge",
            "title": "Sincronizar PC-Edge",
            "status": "unknown",
            "objective": "Alinear repositorio operativo edge y recuperar evidencia.",
            "prechecks": ["tesis-edge alcanzable", "rama local publicada", "perfil sync elegido"],
            "request": "OpenClaw: preparar sync repo+postcheck o repo+restart-edge.",
            "ok_criteria": "postcheck edge y hash de repo alineados.",
            "rollback": "No revertir automaticamente; registrar divergencia y pedir decision humana.",
        },
        {
            "id": "diagnostico_recuperacion",
            "title": "Diagnostico y recuperacion",
            "status": "unknown",
            "objective": "Localizar fallas sin ejecutar acciones destructivas.",
            "prechecks": ["alerta priorizada", "fuente y ultimo log identificados"],
            "request": "OpenClaw: preparar diagnostico con comandos read-only y Step ID si aplica.",
            "ok_criteria": "causa probable, evidencia y siguiente accion documentadas.",
            "rollback": "No aplica: flujo read-only hasta aprobacion humana.",
        },
        {
            "id": "auditoria_publicacion",
            "title": "Auditoria y publicacion",
            "status": "unknown",
            "objective": "Validar build, sanitizacion y mirror publico.",
            "prechecks": ["sin secretos", "snapshot publico generado", "dashboard reconstruido"],
            "request": "OpenClaw: preparar publicacion sanitizada con evidencia de build.",
            "ok_criteria": "build_all y publish check pasan.",
            "rollback": "No publicar; conservar reporte de falla.",
        },
    ]


def build_alerts(
    services: list[dict[str, Any]],
    runtime: dict[str, Any],
    benchmarks: list[dict[str, Any]],
    compose_stack: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    for service in services:
        if service["status"] in {"down", "degraded", "stale"} and service["criticality"] in {"alta", "critica"}:
            alerts.append(
                {
                    "severity": service["status"],
                    "owner": service["domain"],
                    "impact": f"{service['id']} requiere revision",
                    "evidence": service["detail"],
                    "next_step": "Preparar solicitud de diagnostico en OpenClaw.",
                }
            )
    for key in ("serena_status", "telegram_status", "openclaw_status"):
        if runtime.get(key) not in {"ok"}:
            alerts.append(
                {
                    "severity": runtime.get(key, "unknown"),
                    "owner": "openclaw",
                    "impact": key,
                    "evidence": "estado no nominal",
                    "next_step": "Revisar pestaña OpenClaw/Agentes.",
                }
            )
    for benchmark in benchmarks:
        if benchmark["status"] != "ok":
            alerts.append(
                {
                    "severity": benchmark["status"],
                    "owner": benchmark["node"],
                    "impact": "benchmark no nominal o stale",
                    "evidence": benchmark["latest_validity"],
                    "next_step": "Revisar evidencia antes de usar claims cientificos.",
                }
            )
    for service in compose_stack:
        if service["status"] in {"down", "degraded", "stale"}:
            alerts.append(
                {
                    "severity": service["status"],
                    "owner": "docker_compose",
                    "impact": f"{service['id']} no esta nominal en la red del command center",
                    "evidence": service["detail"],
                    "next_step": "Preparar solicitud de control para OpenClaw/Compose.",
                }
            )
    return sorted(alerts, key=lambda item: status_rank(str(item["severity"])))[:16]


def build_snapshot(*, public: bool = False) -> dict[str, Any]:
    env = load_env("config/env/openclaw.env")
    services = build_services()
    compose_stack = build_compose_stack()
    runtime = build_runtime(env)
    benchmarks = build_benchmarks()
    nodes = build_nodes(services)
    publication = build_publication()
    observability = load_yaml_json("manifests/observability_policy.yaml")
    sources = [
        source_record("manifests/service_matrix.yaml"),
        source_record("manifests/operational_topology.yaml"),
        source_record("manifests/observability_policy.yaml"),
        source_record("00_sistema_tesis/config/openclaw_status.json"),
        source_record("runtime/pc_control/benchmarks/index.json"),
        source_record("runtime/edge_iot/benchmarks/index.json"),
        source_record("06_dashboard/publico/manifest_publico.json"),
    ]
    alerts = build_alerts(services, runtime, benchmarks, compose_stack)
    all_status_items = services + compose_stack + benchmarks + nodes + [{"status": publication["status"]}]
    counts: dict[str, int] = {}
    for item in all_status_items:
        status = str(item.get("status", "unknown"))
        counts[status] = counts.get(status, 0) + 1
    snapshot = {
        "schema_version": "siot-observability-dashboard-v1",
        "generated_at": iso_now(),
        "mode": "public" if public else "private",
        "access": {
            "private_lan": not public,
            "auth": "bearer_token_env:SIOT_OBSERVABILITY_TOKEN" if not public else "sanitized_public",
            "read_only": False if not public else True,
            "control_mode": "governed_request_queue" if not public else "none",
            "executes_actions": False,
        },
        "overall_status": worst_status(all_status_items),
        "status_counts": counts,
        "nodes": nodes,
        "services": services,
        "compose_stack": compose_stack,
        "runtime": runtime,
        "observability": {
            "status": "ok" if observability else "unknown",
            "stack": observability.get("stack", "unknown"),
            "mode": observability.get("modo", "unknown"),
            "layers": observability.get("capas", []),
            "logs": observability.get("logs", {}),
            "metrics": observability.get("metricas", {}),
            "source": "manifests/observability_policy.yaml",
        },
        "benchmarks": benchmarks,
        "publication": publication,
        "flows": build_flows(),
        "notification_policy": {
            "inbox": "dashboard_and_telegram_synchronized",
            "telegram_suppression": "suppress_when_dashboard_heartbeat_active",
            "dashboard_heartbeat_seconds": 90,
        },
        "control_policy": {
            "mode": "governed_request_queue",
            "queue": "runtime/observability/control_requests.jsonl",
            "heartbeat": "runtime/observability/dashboard_heartbeat.json",
            "orchestrator": "OpenClaw",
            "direct_docker_socket": False,
            "requires_human_approval_for_mutation": True,
        },
        "alerts": alerts,
        "sources": sources,
    }
    if public:
        return public_snapshot(snapshot)
    return snapshot


def public_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    sanitized = {
        "schema_version": snapshot["schema_version"],
        "generated_at": snapshot["generated_at"],
        "mode": "public",
        "access": snapshot["access"],
        "overall_status": snapshot["overall_status"],
        "status_counts": snapshot["status_counts"],
        "nodes": [
            {
                "id": node["id"],
                "label": node["label"],
                "status": node["status"],
                "service_count": len(node.get("services", [])),
                "source": node["source"],
            }
            for node in snapshot["nodes"]
        ],
        "domains": sorted({service["domain"] for service in snapshot["services"]}),
        "compose_stack": [
            {
                "id": service["id"],
                "status": service["status"],
                "depends_on": service["depends_on"],
                "source": service["source"],
            }
            for service in snapshot.get("compose_stack", [])
        ],
        "runtime": {
            "orchestrator": snapshot["runtime"]["orchestrator"],
            "state": snapshot["runtime"]["state"],
            "active_runtime": snapshot["runtime"]["active_runtime"],
            "openclaw_status": snapshot["runtime"]["openclaw_status"],
            "serena_status": snapshot["runtime"]["serena_status"],
            "telegram_status": snapshot["runtime"]["telegram_status"],
        },
        "benchmarks": [
            {
                "node": benchmark["node"],
                "status": benchmark["status"],
                "latest_validity": benchmark["latest_validity"],
                "source": benchmark["source"],
            }
            for benchmark in snapshot["benchmarks"]
        ],
        "publication": snapshot["publication"],
        "alerts": [
            {
                "severity": alert["severity"],
                "owner": alert["owner"],
                "impact": alert["impact"],
                "next_step": alert["next_step"],
            }
            for alert in snapshot["alerts"]
        ],
        "sources": snapshot["sources"],
    }
    sanitized["access"]["private_lan"] = False
    sanitized["access"]["auth"] = "sanitized_public"
    return sanitized
