from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request
from uuid import uuid4

from .contracts import BenchmarkRecord, RuntimeProbe


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
    ollama = detect_ollama_status()
    llamacpp = detect_llamacpp_status()
    npu = detect_npu_status()
    preflight = build_preflight_report(repo_root=root)
    state = "base_only"
    if preflight["status"] == "ok":
        state = "openclaw_ready"
    if ollama["ready"]:
        state = "ollama_ready"
    if llamacpp["ready"]:
        state = "desktop_llamacpp_ready"
    if npu["ready"]:
        state = "npu_experimental_ready"
    active_runtime = "local"
    if llamacpp["ready"]:
        active_runtime = "pc_native_llamacpp"
    elif ollama["ready"]:
        active_runtime = "ollama_local"
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
        "ollama": ollama,
        "llamacpp": llamacpp,
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
        ollama_latency = float(os.getenv("OPENCLAW_BENCHMARK_OLLAMA_MS", "120.0"))
        llamacpp_latency = float(os.getenv("OPENCLAW_BENCHMARK_LLAMACPP_MS", "95.0"))
        npu_latency = float(os.getenv("OPENCLAW_BENCHMARK_NPU_MS", "75.0"))
        ollama = _benchmark_record(
            provider="ollama_local",
            status="simulated_ok",
            latency_ms=ollama_latency,
            details={"mode": "simulated", "model": os.getenv("OPENCLAW_OLLAMA_BENCH_MODEL", "qwen3:4b")},
        )
        llamacpp = _benchmark_record(
            provider="pc_native_llamacpp",
            status="simulated_ok" if os.getenv("OPENCLAW_FORCE_LLAMACPP_READY") == "1" else "simulated_skipped",
            latency_ms=llamacpp_latency if os.getenv("OPENCLAW_FORCE_LLAMACPP_READY") == "1" else None,
            details={"mode": "simulated", "model": os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", "mistral-nemo:12b")},
        ) if include_llamacpp else None
        npu = _benchmark_record(
            provider="rknn_llm_experimental",
            status="simulated_ok" if os.getenv("OPENCLAW_FORCE_NPU_READY") == "1" else "simulated_skipped",
            latency_ms=npu_latency if os.getenv("OPENCLAW_FORCE_NPU_READY") == "1" else None,
            details={"mode": "simulated"},
        )
        recommended = _recommended_runtime(ollama.to_dict(), llamacpp.to_dict() if llamacpp else None, npu.to_dict())
        results = [ollama.to_dict()]
        if llamacpp is not None:
            results.append(llamacpp.to_dict())
        results.append(npu.to_dict())
        return {
            "active_runtime": probe_runtime_status(root)["active_runtime"],
            "recommended_runtime": recommended,
            "results": results,
        }

    ollama = _run_ollama_benchmark()
    llamacpp = _run_llamacpp_benchmark() if include_llamacpp else None
    npu = _run_npu_benchmark()
    recommended = _recommended_runtime(ollama, llamacpp, npu)
    results = [ollama]
    if llamacpp is not None:
        results.append(llamacpp)
    results.append(npu)
    return {
        "active_runtime": probe_runtime_status(root)["active_runtime"],
        "recommended_runtime": recommended,
        "results": results,
    }


def detect_ollama_status() -> dict[str, Any]:
    forced = os.getenv("OPENCLAW_FORCE_OLLAMA_READY")
    if forced == "1":
        return {
            "installed": True,
            "ready": True,
            "mode": "local_model",
            "command": os.getenv("OPENCLAW_OLLAMA_BIN", "ollama"),
            "models_dir": os.getenv("OLLAMA_MODELS", "/mnt/emmc/models/ollama"),
        }
    command = _resolve_command("ollama", env_var="OPENCLAW_OLLAMA_BIN")
    installed = command is not None
    service_active = _systemd_state("ollama.service") if installed else "not_installed"
    models_dir = os.getenv("OLLAMA_MODELS", "/mnt/emmc/models/ollama")
    return {
        "installed": installed,
        "ready": installed and service_active in {"active", "enabled", "unknown"},
        "mode": "local_model",
        "command": command or "",
        "service_state": service_active,
        "models_dir": models_dir,
    }


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
    configured_base_url = os.getenv(
        "OPENCLAW_DESKTOP_RUNTIME_BASE_URL",
        os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434"),
    ).rstrip("/")
    bind_port = os.getenv("OPENCLAW_LLAMACPP_BIND_PORT", "21435").strip() or "21435"
    local_base_url = f"http://127.0.0.1:{bind_port}"
    runtime = os.getenv("OPENCLAW_DESKTOP_RUNTIME", "llamacpp").strip() or "llamacpp"
    model = os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", os.getenv("OPENCLAW_DESKTOP_COMPUTE_MODEL", "mistral-nemo:12b")).strip() or "mistral-nemo:12b"
    local_fallback_raw = os.getenv("OPENCLAW_LLAMACPP_LOCAL_FALLBACK", "1" if os.name == "nt" else "0").strip().lower()
    local_fallback_enabled = local_fallback_raw in {"1", "true", "yes", "on", "si", "sí"}
    probe_targets = [configured_base_url]
    fallback_used = False
    if local_fallback_enabled and runtime == "llamacpp" and configured_base_url != local_base_url:
        probe_targets.append(local_base_url)
    if forced == "1":
        return {
            "installed": True,
            "ready": True,
            "mode": "desktop_native_llamacpp",
            "runtime": runtime,
            "base_url": configured_base_url,
            "model": model,
        }

    status = "unavailable"
    latency_ms = 0.0
    error_code = "not_probed"
    selected_base_url = configured_base_url
    for index, target_url in enumerate(probe_targets):
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
        "installed": runtime == "llamacpp",
        "ready": status == "ok",
        "mode": "desktop_native_llamacpp",
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


def _run_ollama_benchmark() -> dict[str, Any]:
    ollama = detect_ollama_status()
    model = os.getenv("OPENCLAW_OLLAMA_BENCH_MODEL", "qwen3:4b")
    if not ollama["installed"]:
        return _benchmark_record(
            provider="ollama_local",
            status="skipped_unavailable",
            latency_ms=None,
            details={"reason": "ollama_no_instalado"},
        ).to_dict()
    listed = _run_command([ollama["command"], "list"], timeout=15)
    if listed["returncode"] != 0 or model not in listed["stdout"]:
        return _benchmark_record(
            provider="ollama_local",
            status="skipped_model_missing",
            latency_ms=None,
            details={"model": model, "reason": "modelo_no_descargado"},
        ).to_dict()
    http_ok, http_payload = _run_ollama_http_benchmark(model=model, timeout=90)
    if http_ok:
        return _benchmark_record(
            provider="ollama_local",
            status="ok",
            latency_ms=http_payload["elapsed_ms"],
            details={
                "model": model,
                "method": "http_generate",
                "response": str(http_payload.get("response", "")).strip()[:200],
            },
        ).to_dict()
    executed = _run_command([ollama["command"], "run", model, "Responde únicamente: listo"], timeout=90)
    status = "ok" if executed["returncode"] == 0 else "failed"
    return _benchmark_record(
        provider="ollama_local",
        status=status,
        latency_ms=executed["elapsed_ms"],
        details={
            "model": model,
            "method": "cli_run_fallback",
            "stdout": executed["stdout"].strip()[:200],
            "stderr": executed["stderr"].strip()[:200],
            "http_error": str(http_payload.get("error", "")),
        },
    ).to_dict()


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


def _run_ollama_http_benchmark(*, model: str, timeout: int) -> tuple[bool, dict[str, Any]]:
    base_url = os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    endpoint = base_url + "/api/generate"
    payload = json.dumps(
        {
            "model": model,
            "prompt": "Responde únicamente: listo",
            "stream": False,
            "options": {
                "num_predict": int(os.getenv("OPENCLAW_BENCH_NUM_PREDICT", "8")),
                "num_ctx": int(os.getenv("OPENCLAW_BENCH_NUM_CTX", "512")),
                "temperature": 0,
            },
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(endpoint, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw)
        return True, {
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "response": str(parsed.get("response", "")),
        }
    except (error.URLError, error.HTTPError, json.JSONDecodeError, OSError) as exc:
        return False, {
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "error": f"{type(exc).__name__}:{exc}",
        }


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


def _recommended_runtime(ollama: dict[str, Any], llamacpp: dict[str, Any] | None, npu: dict[str, Any]) -> str:
    ollama_ok = ollama.get("status") in {"ok", "simulated_ok"}
    llamacpp_ok = bool(llamacpp) and llamacpp.get("status") in {"ok", "simulated_ok"}
    npu_ok = npu.get("status") in {"ok", "simulated_ok"}
    allow_npu_promotion = os.getenv("OPENCLAW_NPU_AUTO_PROMOTE", "").strip().lower() in {"1", "true", "yes", "on"}
    if llamacpp_ok:
        return "pc_native_llamacpp"
    if allow_npu_promotion and npu_ok and ollama_ok:
        if float(npu.get("latency_ms") or 9e9) < float(ollama.get("latency_ms") or 9e9):
            return "rknn_llm_experimental"
    if ollama_ok:
        return "ollama_local"
    return "local"


def _benchmark_record(*, provider: str, status: str, latency_ms: float | None, details: dict[str, Any]) -> BenchmarkRecord:
    return BenchmarkRecord(
        benchmark_id=f"BEN-{uuid4().hex[:12]}",
        provider=provider,
        status=status,
        latency_ms=latency_ms,
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
    return any(Path(path).exists() for path in ["/dev/rknpu", "/dev/rknn", "/dev/dri/renderD128"])


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
