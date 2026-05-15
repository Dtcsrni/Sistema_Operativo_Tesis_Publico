from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import hashlib
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request
from uuid import uuid4

from .contracts import BenchmarkRecord, RuntimeProbe


def _env_flag(name: str, *, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "si", "sí"}


def summarize_host(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[3]
    disk = shutil.disk_usage(root)
    total_memory = _memory_total_bytes()
    rootfs = _detect_rootfs()
    orange_pi_model = _orange_pi_model()
    emmc_paths = _emmc_paths()
    return {
        "platform": platform.platform(),
        "cpu_count": os.cpu_count() or 1,
        "machine": os.getenv("OPENCLAW_FORCE_MACHINE", platform.machine()),
        "orange_pi_model": orange_pi_model,
        "memory": {
            "total_bytes": total_memory,
        },
        "disk": {
            "total_bytes": disk.total,
            "used_bytes": disk.used,
            "free_bytes": disk.free,
            "rootfs_device": rootfs["device"],
            "rootfs_fstype": rootfs["fstype"],
            "rootfs_on_nvme": rootfs["on_nvme"],
        },
        "temperature_celsius": _temperature_celsius(),
        "network": {
            "interfaces": _network_interfaces(),
            "default_route": _default_route_present(),
        },
        "storage": {
            "emmc_paths_present": emmc_paths,
            "emmc_available": bool(emmc_paths),
        },
        "accelerators": {
            "rockchip_npu_present": _rockchip_npu_present(),
            "rk3588_compatible": _rk3588_compatible(),
        },
    }


def probe_runtime_status(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[3]
    defaults = _runtime_path_defaults(root)
    data_dir = Path(os.getenv("OPENCLAW_DATA_DIR", str(defaults["data_dir"])))
    cache_dir = Path(os.getenv("OPENCLAW_CACHE_DIR", str(defaults["cache_dir"])))
    log_dir = Path(os.getenv("OPENCLAW_LOG_DIR", str(defaults["log_dir"])))
    env_file = Path(os.getenv("OPENCLAW_ENV_FILE", str(defaults["env_file"])))
    db_path = Path(os.getenv("OPENCLAW_DB_PATH", data_dir / "openclaw.db"))
    
    edge = detect_edge_inference_status()
    llamacpp = detect_llamacpp_status()
    npu = detect_npu_status()
    preflight = build_preflight_report(repo_root=root)
    
    state = "base_only"
    if preflight["status"] == "ok":
        state = "openclaw_ready"
    if edge["ready"]:
        state = "edge_inference_ready"
    if llamacpp["ready"]:
        state = "desktop_llamacpp_ready"
    if npu["ready"]:
        state = "npu_experimental_ready"
        
    active_runtime = "local"
    if llamacpp["ready"]:
        active_runtime = "llamacpp_local"
    elif edge["ready"]:
        active_runtime = "edge_inference"
        
    return {
        "state": state,
        "active_runtime": active_runtime,
        "service_user": "tesis",
        "repo_root": str(root),
        "env_file": str(env_file),
        "data_dir": str(data_dir),
        "cache_dir": str(cache_dir),
        "log_dir": str(log_dir),
        "db_path": str(db_path),
        "paths": {
            "repo_root_exists": root.exists(),
            "env_file_exists": env_file.exists(),
            "data_dir_exists": data_dir.exists(),
            "cache_dir_exists": cache_dir.exists(),
            "log_dir_exists": log_dir.exists(),
            "db_parent_exists": db_path.parent.exists(),
        },
        "edge": edge,
        "llamacpp": llamacpp,
        "desktop_compute": llamacpp,
        "npu": npu,
        "host": summarize_host(root),
        "preflight": preflight,
    }


def build_runtime_probe(repo_root: Path | None = None, *, source_command: str = "") -> RuntimeProbe:
    status = probe_runtime_status(repo_root)
    return RuntimeProbe(
        probe_id=f"RTP-{uuid4().hex[:12]}",
        source_command=source_command,
        system_state=status["state"],
        active_runtime=status["active_runtime"],
        payload=status,
        created_at=datetime.now(UTC).isoformat(),
    )


def build_preflight_report(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[3]
    defaults = _runtime_path_defaults(root)
    env_file = Path(os.getenv("OPENCLAW_ENV_FILE", str(defaults["env_file"])))
    data_dir = Path(os.getenv("OPENCLAW_DATA_DIR", str(defaults["data_dir"])))
    db_path = Path(os.getenv("OPENCLAW_DB_PATH", data_dir / "openclaw.db"))
    wrapper = root / "runtime" / "openclaw" / "wrappers" / "openclaw-gateway.sh"
    checks = [
        _check("repo_root", root.exists(), str(root)),
        _check("gateway_wrapper", wrapper.exists(), str(wrapper)),
        _check("env_file", env_file.exists(), str(env_file)),
        _check("data_dir", data_dir.exists(), str(data_dir)),
        _check("db_parent", db_path.parent.exists(), str(db_path.parent)),
        _check("python_bin", Path(os.getenv("OPENCLAW_PYTHON_BIN", "python3")).exists() if os.path.isabs(os.getenv("OPENCLAW_PYTHON_BIN", "")) else True, os.getenv("OPENCLAW_PYTHON_BIN", "python3")),
    ]
    status = "ok" if all(item["status"] == "ok" for item in checks) else "fail"
    return {
        "status": status,
        "checks": checks,
    }


def run_runtime_benchmarks(repo_root: Path | None = None) -> dict[str, Any]:
    root = repo_root or Path(__file__).resolve().parents[3]
    include_llamacpp = os.getenv("OPENCLAW_DESKTOP_RUNTIME", "").strip().lower() == "llamacpp" or os.getenv("OPENCLAW_FORCE_LLAMACPP_READY") == "1"
    
    if os.getenv("OPENCLAW_BENCHMARK_SIMULATION") == "1":
        force_edge = os.getenv("OPENCLAW_FORCE_EDGE_READY") == "1"
        force_npu = os.getenv("OPENCLAW_FORCE_NPU_READY") == "1"
        force_llamacpp = os.getenv("OPENCLAW_FORCE_LLAMACPP_READY") == "1"
        
        edge = _benchmark_record(
            provider="edge_inference",
            status="ok" if force_edge else "failed",
            latency_ms=250.0 if force_edge else None,
            details={
                "reason": "forced_simulation" if force_edge else "simulation_mode_disabled",
                "model": os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b"),
            },
        )
        
        npu = _benchmark_record(
            provider="rknn_llm_experimental",
            status="ok" if force_npu else "failed",
            latency_ms=120.0 if force_npu else None,
            details={"reason": "forced_simulation" if force_npu else "simulation_mode_disabled"},
        )
        
        llamacpp = (
            _benchmark_record(
                provider="llamacpp_local",
                status="ok" if force_llamacpp else "failed",
                latency_ms=180.0 if force_llamacpp else None,
                details={
                    "reason": "forced_simulation" if force_llamacpp else "simulation_mode_disabled",
                    "model": os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", "mistral-nemo:12b"),
                },
            )
            if include_llamacpp
            else None
        )
        if force_npu and _env_flag("OPENCLAW_NPU_AUTO_PROMOTE", default=False):
            recommended = "rknn_llm_experimental"
        elif force_llamacpp:
            recommended = "llamacpp_local"
        elif force_edge:
            recommended = "edge_inference"
        else:
            recommended = "local"
        results = [edge.to_dict()]
        if llamacpp is not None:
            results.append(llamacpp.to_dict())
        results.append(npu.to_dict())
        return {
            "active_runtime": probe_runtime_status(root)["active_runtime"],
            "recommended_runtime": recommended,
            "results": results,
        }

    edge = _run_edge_inference_benchmark()
    llamacpp = _run_llamacpp_benchmark() if include_llamacpp else None
    npu = _run_npu_benchmark()
    recommended = "desktop_compute" if (llamacpp and llamacpp.get("status") == "ok") else ("edge_inference" if (edge and edge.get("status") == "ok") else ("rknn_llm_experimental" if (npu and npu.get("status") == "ok") else "local"))
    
    results = [edge]
    if llamacpp is not None:
        results.append(llamacpp)
    results.append(npu)
    return {
        "active_runtime": probe_runtime_status(root)["active_runtime"],
        "recommended_runtime": recommended,
        "results": results,
    }


def detect_edge_inference_status() -> dict[str, Any]:
    forced = os.getenv("OPENCLAW_FORCE_EDGE_READY")
    base_url = os.getenv("OPENCLAW_EDGE_INFERENCE_BASE_URL", os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434")).rstrip("/")
    model = os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")
    if forced == "1":
        return {
            "installed": True,
            "ready": True,
            "mode": "local_model",
            "base_url": base_url,
            "model": model,
        }
    status, latency_ms, error_code = _http_probe(base_url + "/health", timeout=2.0)
    return {
        "installed": True,
        "ready": status == "ok",
        "mode": "local_model",
        "base_url": base_url,
        "model": model,
        "probe_status": status,
        "probe_latency_ms": latency_ms,
        "probe_error": error_code,
    }


def _run_edge_inference_benchmark() -> dict[str, Any]:
    status = detect_edge_inference_status()
    if not status["ready"]:
        return _benchmark_record(
            provider="edge_inference",
            status="skipped_unavailable",
            latency_ms=None,
            details={"reason": status.get("probe_error", "edge_unavailable"), "base_url": status["base_url"]},
        ).to_dict()

    payload = json.dumps(
        {
            "model": status["model"],
            "messages": [{"role": "user", "content": "Responde únicamente: listo"}],
            "max_tokens": 8,
            "temperature": 0,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(status["base_url"] + "/v1/chat/completions", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        choices = parsed.get("choices") or []
        text = ""
        if choices and isinstance(choices[0], dict):
            text = str((choices[0].get("message") or {}).get("content", "")).strip()
        return _benchmark_record(
            provider="edge_inference",
            status="ok",
            latency_ms=round((time.perf_counter() - started) * 1000.0, 3),
            details={"model": status["model"], "response": text[:200], "base_url": status["base_url"]},
        ).to_dict()
    except (error.URLError, error.HTTPError, json.JSONDecodeError, OSError) as exc:
        return _benchmark_record(
            provider="edge_inference",
            status="failed",
            latency_ms=round((time.perf_counter() - started) * 1000.0, 3),
            details={"model": status["model"], "error": f"{type(exc).__name__}:{exc}", "base_url": status["base_url"]},
        ).to_dict()


def detect_npu_status() -> dict[str, Any]:
    forced = os.getenv("OPENCLAW_FORCE_NPU_READY")
    root = Path(os.getenv("OPENCLAW_RKLLM_ROOT", "/opt/tesis-os/vendor/rknn-llm"))
    installed = root.exists() or _rockchip_npu_present() or forced == "1"
    return {
        "installed": installed,
        "ready": forced == "1" or (installed and _rk3588_compatible()),
        "mode": "experimental_secondary",
        "root": str(root),
        "device_present": _rockchip_npu_present(),
        "rk3588_compatible": _rk3588_compatible(),
    }


def detect_llamacpp_status() -> dict[str, Any]:
    forced = os.getenv("OPENCLAW_FORCE_LLAMACPP_READY")
    bind_port = os.getenv("OPENCLAW_LLAMACPP_BIND_PORT", "21435").strip() or "21435"
    local_base_url = f"http://127.0.0.1:{bind_port}"
    runtime = os.getenv("OPENCLAW_DESKTOP_RUNTIME", "desktop_compute").strip() or "desktop_compute"
    configured_base_url = (
        os.getenv("OPENCLAW_DESKTOP_RUNTIME_BASE_URL", "").strip()
        or os.getenv("OPENCLAW_LLAMACPP_BASE_URL", "").strip()
        or (local_base_url if runtime == "llamacpp" else os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434").strip())
    ).rstrip("/")
    legacy_compute_base_url = os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "").strip().rstrip("/")
    model = os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", os.getenv("OPENCLAW_DESKTOP_COMPUTE_MODEL", "deepseek-r1:7b")).strip() or "deepseek-r1:7b"
    local_fallback_raw = os.getenv("OPENCLAW_LLAMACPP_LOCAL_FALLBACK", "1" if os.name == "nt" else "0").strip().lower()
    local_fallback_enabled = local_fallback_raw in {"1", "true", "yes", "on", "si", "sí"}
    probe_targets = [configured_base_url]
    if runtime in {"llamacpp", "desktop_compute"} and legacy_compute_base_url and legacy_compute_base_url != configured_base_url:
        probe_targets.append(legacy_compute_base_url)
    fallback_used = False
    if local_fallback_enabled and runtime in {"llamacpp", "desktop_compute"} and configured_base_url != local_base_url:
        probe_targets.append(local_base_url)
    if forced == "1":
        return {
            "installed": True,
            "ready": True,
            "mode": "desktop_compute",
            "runtime": runtime,
            "base_url": configured_base_url,
            "model": model,
        }

    status = "unavailable"
    latency_ms = 0.0
    error_code = "not_probed"
    selected_base_url = configured_base_url
    
    for index, target_url in enumerate(probe_targets):
        # llama.cpp probe: /health then /props
        status, latency_ms, error_code = _http_probe(target_url + "/health", timeout=2.0)
        if status != "ok":
            props_status, props_latency_ms, props_error_code = _http_probe(target_url + "/props", timeout=2.0)
            if props_status == "ok":
                status, latency_ms, error_code = props_status, props_latency_ms, props_error_code
        if status == "ok":
            selected_base_url = target_url
            fallback_used = index > 0
            break
    return {
        "installed": runtime in {"llamacpp", "desktop_compute"},
        "ready": status == "ok",
        "mode": "desktop_compute",
        "runtime": runtime,
        "base_url": selected_base_url,
        "configured_base_url": configured_base_url,
        "local_base_url": local_base_url,
        "local_fallback_enabled": local_fallback_enabled,
        "fallback_used": fallback_used,
        "model": model,
        "probe_status": status,
        "probe_latency_ms": latency_ms,
        "probe_error": error_code,
    }


def _run_npu_benchmark() -> dict[str, Any]:
    npu = detect_npu_status()
    command = _env_value("OPENCLAW_NPU_BENCH_CMD").strip()
    if not npu["installed"]:
        return _benchmark_record(
            provider="rknn_llm_experimental",
            status="skipped_unavailable",
            latency_ms=None,
            details={"reason": "npu_no_instalada"},
        ).to_dict()
    if not command:
        return _benchmark_record(
            provider="rknn_llm_experimental",
            status="skipped_unconfigured",
            latency_ms=None,
            details={"reason": "OPENCLAW_NPU_BENCH_CMD_no_definido"},
        ).to_dict()
    executed = _run_command(command, timeout=90, shell=True)
    status = "ok" if executed["returncode"] == 0 else "failed"
    return _benchmark_record(
        provider="rknn_llm_experimental",
        status=status,
        latency_ms=executed["elapsed_ms"],
        details={"command": command, "stdout": executed["stdout"].strip()[:200], "stderr": executed["stderr"].strip()[:200]},
    ).to_dict()


def _run_llamacpp_benchmark() -> dict[str, Any]:
    status = detect_llamacpp_status()
    if not status["installed"]:
        return _benchmark_record(
            provider="pc_native_llamacpp",
            status="skipped_unconfigured",
            latency_ms=None,
            details={"reason": "desktop_runtime_no_configurado"},
        ).to_dict()
    if not status["ready"]:
        return _benchmark_record(
            provider="pc_native_llamacpp",
            status="skipped_unavailable",
            latency_ms=None,
            details={"reason": status.get("probe_error", "llamacpp_unavailable"), "base_url": status["base_url"]},
        ).to_dict()

    payload = json.dumps(
        {
            "model": status["model"],
            "messages": [{"role": "user", "content": "Responde únicamente: listo"}],
            "max_tokens": 8,
            "temperature": 0,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(status["base_url"] + "/v1/chat/completions", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=60) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        choices = parsed.get("choices") or []
        text = ""
        if choices and isinstance(choices[0], dict):
            text = str((choices[0].get("message") or {}).get("content", "")).strip()
        return _benchmark_record(
            provider="pc_native_llamacpp",
            status="ok",
            latency_ms=round((time.perf_counter() - started) * 1000.0, 3),
            details={"model": status["model"], "response": text[:200], "base_url": status["base_url"]},
        ).to_dict()
    except (error.URLError, error.HTTPError, json.JSONDecodeError, OSError) as exc:
        return _benchmark_record(
            provider="pc_native_llamacpp",
            status="failed",
            latency_ms=round((time.perf_counter() - started) * 1000.0, 3),
            details={"model": status["model"], "error": f"{type(exc).__name__}:{exc}", "base_url": status["base_url"]},
        ).to_dict()


def _benchmark_record(*, provider: str, status: str, latency_ms: float | None, details: dict[str, Any]) -> BenchmarkRecord:
    model = str(details.get("model", ""))
    run_id = str(details.get("run_id", ""))
    primary_jsonl = str(details.get("primary_jsonl", ""))
    scientific_validity = str(details.get("scientific_validity", ""))
    if not scientific_validity:
        scientific_validity = "operational_probe_only"
    payload_hash = hashlib.sha256(json.dumps(details, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return BenchmarkRecord(
        benchmark_id=f"BEN-{uuid4().hex[:12]}",
        run_id=run_id,
        provider=provider,
        model=model,
        status=status,
        latency_ms=latency_ms,
        payload_hash=payload_hash,
        primary_jsonl=primary_jsonl,
        scientific_validity=scientific_validity,
        details=details,
        created_at=datetime.now(UTC).isoformat(),
    )


def _run_command(command: list[str] | str, *, timeout: int, shell: bool = False) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=shell,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "elapsed_ms": round(elapsed_ms, 3),
        }
    except (OSError, subprocess.SubprocessError) as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {
            "returncode": 1,
            "stdout": "",
            "stderr": str(exc),
            "elapsed_ms": round(elapsed_ms, 3),
        }


def _http_probe(url: str, *, timeout: float = 4.0) -> tuple[str, float | None, str]:
    started = time.perf_counter()
    req = request.Request(url, method="GET")
    try:
        with request.urlopen(req, timeout=timeout) as response:
            _ = response.read(256)
            latency = (time.perf_counter() - started) * 1000.0
            return "ok", round(latency, 3), ""
    except error.HTTPError as exc:
        latency = (time.perf_counter() - started) * 1000.0
        return "degraded", round(latency, 3), f"http_{exc.code}"
    except Exception as exc:  # noqa: BLE001
        latency = (time.perf_counter() - started) * 1000.0
        return "unavailable", round(latency, 3), f"{type(exc).__name__}:{exc}"


def _memory_total_bytes() -> int:
    forced = os.getenv("OPENCLAW_FORCE_MEMORY_BYTES")
    if forced:
        return int(forced)
    if hasattr(os, "sysconf") and "SC_PAGE_SIZE" in os.sysconf_names and "SC_PHYS_PAGES" in os.sysconf_names:
        page_size = os.sysconf("SC_PAGE_SIZE")
        phys_pages = os.sysconf("SC_PHYS_PAGES")
        if page_size and phys_pages:
            return page_size * phys_pages
    return 0


def _env_value(name: str, default: str = "") -> str:
    raw = os.getenv(name, "").strip()
    if raw:
        return raw
    defaults = _runtime_path_defaults(Path(__file__).resolve().parents[3])
    env_file = Path(os.getenv("OPENCLAW_ENV_FILE", str(defaults["env_file"])))
    if not env_file.exists():
        return default
    try:
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() != name:
                continue
            return value.strip().strip("'\"")
    except OSError:
        return default
    return default


def _runtime_path_defaults(repo_root: Path) -> dict[str, Path]:
    if os.name == "nt":
        local_env = repo_root / "config" / "env" / "openclaw.env"
        fallback_env = repo_root / "config" / "env" / "openclaw.env.example"
        return {
            "env_file": local_env if local_env.exists() else fallback_env,
            "data_dir": repo_root / "runtime" / "openclaw" / "state",
            "cache_dir": repo_root / "runtime" / "openclaw" / "cache",
            "log_dir": repo_root / "runtime" / "openclaw" / "logs",
        }
    return {
        "env_file": Path("/etc/tesis-os/openclaw.env"),
        "data_dir": Path("/var/lib/herramientas/openclaw"),
        "cache_dir": Path("/var/cache/herramientas/openclaw"),
        "log_dir": Path("/var/log/openclaw"),
    }


def _detect_rootfs() -> dict[str, Any]:
    forced_device = os.getenv("OPENCLAW_FORCE_ROOT_DEVICE")
    forced_fstype = os.getenv("OPENCLAW_FORCE_ROOTFS_TYPE")
    if forced_device:
        return {
            "device": forced_device,
            "fstype": forced_fstype or "unknown",
            "on_nvme": "nvme" in forced_device.lower(),
        }
    mounts = Path("/proc/mounts")
    if mounts.exists():
        for line in mounts.read_text(encoding="utf-8", errors="ignore").splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[1] == "/":
                device = parts[0]
                fstype = parts[2]
                return {
                    "device": device,
                    "fstype": fstype,
                    "on_nvme": "nvme" in device.lower(),
                }
    return {"device": "", "fstype": "", "on_nvme": False}


def _orange_pi_model() -> str:
    forced = os.getenv("OPENCLAW_FORCE_ORANGE_PI_MODEL")
    if forced:
        return forced
    model_path = Path("/proc/device-tree/model")
    if model_path.exists():
        return model_path.read_text(encoding="utf-8", errors="ignore").replace("\x00", "").strip()
    return platform.node()


def _temperature_celsius() -> float | None:
    forced = os.getenv("OPENCLAW_FORCE_TEMPERATURE_C")
    if forced:
        return float(forced)
    thermal_root = Path("/sys/class/thermal")
    readings: list[float] = []
    if thermal_root.exists():
        for path in thermal_root.glob("thermal_zone*/temp"):
            try:
                value = path.read_text(encoding="utf-8").strip()
                readings.append(int(value) / 1000.0)
            except ValueError:
                continue
    return round(max(readings), 2) if readings else None


def _network_interfaces() -> list[str]:
    if Path("/sys/class/net").exists():
        return sorted(path.name for path in Path("/sys/class/net").iterdir() if path.is_dir())
    return []


def _default_route_present() -> bool:
    route_file = Path("/proc/net/route")
    if route_file.exists():
        for line in route_file.read_text(encoding="utf-8", errors="ignore").splitlines()[1:]:
            parts = line.split()
            if len(parts) > 1 and parts[1] == "00000000":
                return True
    return False


def _emmc_paths() -> list[str]:
    forced = os.getenv("OPENCLAW_FORCE_EMMC_PRESENT")
    base = Path("/mnt/emmc")
    expected = ["archive", "backups", "corpus", "datasets", "exports", "models", "snapshots"]
    if forced == "1":
        return [str(base / item) for item in expected]
    if not base.exists():
        return []
    return [str(base / item) for item in expected if (base / item).exists()]


def _rockchip_npu_present() -> bool:
    forced = os.getenv("OPENCLAW_FORCE_NPU_READY")
    if forced == "1":
        return True
    if any(Path(path).exists() for path in ["/dev/rknpu", "/dev/rknn"]):
        return True
    drm_root = Path("/sys/class/drm")
    if not drm_root.exists():
        return False
    for uevent in drm_root.glob("renderD*/device/uevent"):
        try:
            if "DRIVER=RKNPU" in uevent.read_text(encoding="utf-8", errors="ignore").splitlines():
                device = Path("/dev/dri") / uevent.parents[1].name
                if device.exists():
                    return True
        except OSError:
            continue
    return False


def _rk3588_compatible() -> bool:
    compatible = Path("/proc/device-tree/compatible")
    if os.getenv("OPENCLAW_FORCE_NPU_READY") == "1":
        return True
    if compatible.exists():
        text = compatible.read_text(encoding="utf-8", errors="ignore").lower()
        return "rk3588" in text or "rockchip" in text
    return False


def _resolve_command(name: str, *, env_var: str) -> str | None:
    forced = os.getenv(env_var)
    if forced:
        return forced
    return shutil.which(name)


def _systemd_state(unit: str) -> str:
    systemctl = shutil.which("systemctl")
    if not systemctl:
        return "unknown"
    active = _run_command([systemctl, "is-active", unit], timeout=5)
    if active["returncode"] == 0:
        return active["stdout"].strip() or "active"
    enabled = _run_command([systemctl, "is-enabled", unit], timeout=5)
    if enabled["returncode"] == 0:
        return enabled["stdout"].strip() or "enabled"
    return "inactive"


def _check(name: str, ok: bool, detail: str) -> dict[str, str]:
    return {
        "name": name,
        "status": "ok" if ok else "fail",
        "detail": detail,
    }
