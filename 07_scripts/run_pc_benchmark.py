from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib import error, request

from benchmark_science import (
    BENCHMARK_PROFILES,
    PRIMARY_PC_MODEL,
    append_hashed_record,
    build_run_header,
    build_sample_record,
    promptset_hash,
    run_log_path,
    update_index,
    utc_now,
    write_summary,
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "runtime" / "openclaw"))
from openclaw_local.contracts import BenchmarkRecord  # noqa: E402
from openclaw_local.engine import default_data_dir  # noqa: E402
from openclaw_local.storage import OpenClawStore  # noqa: E402

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
PC_REPORT = ROOT / "runtime" / "pc_control" / "benchmarks" / "scientific_report_mistral_nemo_12b.json"

CATEGORIES_CONFIG = {
    "iot_urban_pachuca": {
        "name": "Conectividad Urbana Pachuca",
        "prompt": "Actúa como un coordinador de red IoT en Pachuca de Soto. Un activo móvil (Atzin Track) se desplaza del Centro Histórico hacia la periferia (Zona Plateada). El RSSI de LoRa cae a -125dBm y el SNR es de -15dB. ¿Debería el nodo conmutar de MQTT directo a un relay P2P? Justifica brevemente considerando la topografía de Pachuca."
    },
    "hybrid_lora_logic": {
        "name": "Lógica Híbrida P2P-MQTT",
        "prompt": "Diseña un algoritmo de decisión en pseudo-código para un nodo Heltec WSL V3 que opera en una arquitectura híbrida LoRa P2P-MQTT. El criterio debe priorizar el ahorro de energía y la integridad de los datos (PDR) al monitorear una flota ligera."
    },
    "atzin_fleet_agent": {
        "name": "Agente de Gestión de Flotas Atzin",
        "prompt": "Eres un agente de IA embebido en una Orange Pi 5 Plus. Recibes telemetría de 50 nodos Atzin Track en tiempo real. Un nodo reporta una caída súbita de voltaje (3.2V) y coordenadas GPS estáticas en una zona de alta delincuencia. Genera un reporte de incidente y una acción correctiva inmediata."
    },
    "iot_sovereignty_pachuca": {
        "name": "Soberanía de Datos Urbanos",
        "prompt": "Analiza las implicaciones éticas y de soberanía de procesar datos de movilidad urbana de Pachuca en el Edge (Orange Pi) vs enviarlos a una nube comercial externa. Cita brevemente la importancia de la privacidad en sistemas operativos de tesis posgrado."
    },
    "embedded_cpp_atzin": {
        "name": "Lógica Embebida C++ (WSL V3)",
        "prompt": "Escribe una función C++ optimizada para un ESP32 (Heltec WSL V3) que implemente un buffer circular para almacenar temporalmente 10 tramas de telemetría GPS/RSSI cuando la conexión con el Gateway se pierde en un entorno urbano denso."
    }
}

CATEGORIES = [{"id": k, **v} for k, v in CATEGORIES_CONFIG.items()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark cientifico del nodo PC para Mistral Nemo 12B.")
    parser.add_argument("--model", default=PRIMARY_PC_MODEL)
    parser.add_argument("--iterations", type=int, default=50)
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--step-id", default="VAL-STEP-PENDING")
    parser.add_argument("--profile-id", default="pc_mistral_nemo_12b_extensive")
    parser.add_argument("--node", default="pc_control", choices=["pc_control", "edge_iot"])
    parser.add_argument("--num-predict", type=int, default=96)
    parser.add_argument("--num-ctx", type=int, default=2048)
    parser.add_argument("--interval-ms", type=int, default=500)
    parser.add_argument("--categories", default="", help="Lista separada por comas; por defecto ejecuta todas.")
    parser.add_argument("--skip-lm-eval", action="store_true")
    args = parser.parse_args()

    selected_categories = _select_categories(args.categories)
    promptset = [{"category": item["id"], "name": item["name"], "prompt": item["prompt"]} for item in selected_categories]
    header = build_run_header(
        profile_id=args.profile_id,
        node=args.node,
        runtime="ollama_local",
        model=args.model,
        step_id=args.step_id,
        command="python3 07_scripts/run_pc_benchmark.py",
        promptset=promptset,
        mode="real",
        repo_root=ROOT,
    )
    log_path = run_log_path(node=args.node, run_id=header["run_id"])
    append_hashed_record(log_path, header)

    samples: list[dict[str, float | None]] = []
    status = "ok"
    extra: dict[str, object] = {
        "profile": BENCHMARK_PROFILES.get(args.profile_id, {}),
        "lm_eval": _lm_eval_status(args.model, skip=args.skip_lm_eval),
    }

    if not _ollama_model_available(args.model):
        status = "blocked_missing_model"
        summary = write_summary(path=log_path, header=header, samples=[], status=status, extra=extra)
        update_index(node=args.node, summary=summary, log_path=log_path)
        _write_report(header, summary, log_path, extra)
        print(json.dumps({"status": status, "run_id": header["run_id"], "jsonl": str(log_path)}, ensure_ascii=False, indent=2))
        return 2

    sample_index = 0
    for warmup in range(args.warmups):
        sample_index += 1
        result = _ollama_generate(args.model, "Responde unicamente: listo", args.num_predict, args.num_ctx)
        append_hashed_record(
            log_path,
            build_sample_record(
                run_id=header["run_id"],
                step_id=args.step_id,
                sample_index=sample_index,
                phase="warmup",
                category="warmup",
                prompt_hash=promptset_hash([{"prompt": "warmup"}]),
                latency_ms=result.get("latency_ms"),
                ttft_ms=result.get("ttft_ms"),
                tokens_per_second=result.get("tokens_per_second"),
                status=str(result["status"]),
                stdout=str(result.get("response", "")),
                stderr=str(result.get("error", "")),
                exit_status=0 if result["status"] == "ok" else 1,
            ),
        )
        print(f"[warmup] {warmup + 1}/{args.warmups} status={result['status']}", flush=True)
        time.sleep(args.interval_ms / 1000.0)

    for category in selected_categories:
        print(f"\n--- Iniciando Categoría: {category['name']} ---", flush=True)
        # Cooldown entre categorías para evitar estrés térmico
        time.sleep(10) 
        
        for iteration in range(args.iterations):
            sample_index += 1
            
            # Verificación de salud y reinicio si es necesario
            retry_count = 0
            while retry_count < 3:
                result = _ollama_generate(args.model, category["prompt"], args.num_predict, args.num_ctx)
                if result["status"] == "ok":
                    break
                
                print(f"[warning] Error en muestra {iteration+1}. Reintentando ({retry_count+1}/3)...", flush=True)
                _restart_ollama_service()
                time.sleep(5)
                retry_count += 1

            sample = build_sample_record(
                run_id=header["run_id"],
                step_id=args.step_id,
                sample_index=sample_index,
                phase="measurement",
                category=category["id"],
                prompt_hash=promptset_hash([category]),
                latency_ms=result.get("latency_ms"),
                ttft_ms=result.get("ttft_ms"),
                tokens_per_second=result.get("tokens_per_second"),
                status=str(result["status"]),
                stdout=str(result.get("response", "")),
                stderr=str(result.get("error", "")),
                exit_status=0 if result["status"] == "ok" else 1,
            )
            append_hashed_record(log_path, sample)
            if result["status"] == "ok":
                samples.append({"latency_ms": result.get("latency_ms"), "tokens_per_second": result.get("tokens_per_second")})
            else:
                status = "partial_failure"
            
            print(
                f"[measurement] category={category['id']} {iteration + 1}/{args.iterations} "
                f"status={result['status']} latency_ms={result.get('latency_ms')}",
                flush=True,
            )
            time.sleep(args.interval_ms / 1000.0)

    summary = write_summary(path=log_path, header=header, samples=samples, status=status, extra=extra)
    update_index(node=args.node, summary=summary, log_path=log_path)
    _mirror_to_openclaw_sqlite(summary, log_path)
    _write_report(header, summary, log_path, extra)
    print(json.dumps({"status": status, "run_id": header["run_id"], "jsonl": str(log_path), "report": str(PC_REPORT)}, ensure_ascii=False, indent=2))
    return 0 if status == "ok" else 1


def _ollama_model_available(model: str) -> bool:
    cmd = shutil.which("ollama")
    if cmd:
        completed = subprocess.run([cmd, "list"], capture_output=True, text=True, check=False)
    else:
        completed = subprocess.run(["wsl", "ollama", "list"], capture_output=True, text=True, check=False)
        
    return completed.returncode == 0 and any(line.split() and line.split()[0] == model for line in completed.stdout.splitlines()[1:])


def _select_categories(raw: str) -> list[dict[str, str]]:
    if not raw.strip():
        return CATEGORIES
    wanted = {item.strip() for item in raw.split(",") if item.strip()}
    selected = [item for item in CATEGORIES if item["id"] in wanted]
    if not selected:
        raise SystemExit(f"Categorias no validas: {raw}")
    return selected


def _ollama_generate(model: str, prompt: str, num_predict: int, num_ctx: int) -> dict[str, object]:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": num_predict, "num_ctx": num_ctx},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(f"{OLLAMA_BASE_URL}/api/generate", data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    started = time.perf_counter()
    try:
        with request.urlopen(req, timeout=180) as response:
            parsed = json.loads(response.read().decode("utf-8", errors="replace"))
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        eval_count = float(parsed.get("eval_count") or 0)
        eval_duration_ns = float(parsed.get("eval_duration") or 0)
        prompt_eval_duration_ns = float(parsed.get("prompt_eval_duration") or 0)
        tokens_per_second = (eval_count / (eval_duration_ns / 1_000_000_000.0)) if eval_count and eval_duration_ns else None
        ttft_ms = (prompt_eval_duration_ns / 1_000_000.0) if prompt_eval_duration_ns else None
        return {
            "status": "ok",
            "latency_ms": round(elapsed_ms, 4),
            "ttft_ms": round(ttft_ms, 4) if ttft_ms is not None else None,
            "tokens_per_second": round(tokens_per_second, 4) if tokens_per_second is not None else None,
            "response": str(parsed.get("response", "")),
        }
    except (error.URLError, error.HTTPError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return {"status": "failed", "latency_ms": round(elapsed_ms, 4), "ttft_ms": None, "tokens_per_second": None, "error": f"{type(exc).__name__}:{exc}"}
def _restart_ollama_service():
    """Intenta reiniciar el servicio Ollama en WSL o Windows."""
    print("[system] Reiniciando servicio Ollama...", flush=True)
    if sys.platform == "win32":
        subprocess.run(["powershell", "-Command", "Start-Process wsl -ArgumentList 'ollama', 'serve' -WindowStyle Hidden"], check=False)
    elif shutil.which("systemctl"):
        restarted = subprocess.run(["systemctl", "--user", "restart", "ollama"], check=False)
        if restarted.returncode != 0 and shutil.which("sudo"):
            subprocess.run(["sudo", "-n", "systemctl", "restart", "ollama"], check=False)
        if not _ollama_http_ready():
            subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    elif shutil.which("ollama"):
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    elif shutil.which("wsl"):
        subprocess.run(["wsl", "ollama", "serve"], check=False)
    time.sleep(10) # Esperar a que inicialice


def _ollama_http_ready() -> bool:
    try:
        with request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=5) as response:
            response.read(128)
        return True
    except OSError:
        return False


def _lm_eval_status(model: str, *, skip: bool) -> dict[str, object]:
    if skip:
        return {"status": "skipped_by_operator"}
    binary = shutil.which("lm_eval")
    if not binary:
        return {
            "status": "blocked_missing_dependency",
            "tool": "lm_eval",
            "model": model,
            "note": "Instalar EleutherAI lm-evaluation-harness antes de declarar resultados comparables.",
        }
    return {"status": "available_not_executed_by_default", "tool": binary, "model": model}


def _write_report(header: dict[str, object], summary: dict[str, object], log_path: Path, extra: dict[str, object]) -> None:
    PC_REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema_version": "siot-benchmark-report-v1",
        "generated_at": utc_now(),
        "primary_jsonl": str(log_path.relative_to(ROOT)),
        "header": header,
        "summary": summary,
        "extra": extra,
    }
    PC_REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _mirror_to_openclaw_sqlite(summary: dict[str, object], log_path: Path) -> None:
    db_path = Path(default_data_dir(ROOT)) / "openclaw.db"
    payload_hash = str(summary.get("record_hash", ""))
    if not payload_hash:
        payload_hash = hashlib.sha256(json.dumps(summary, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    record = BenchmarkRecord(
        benchmark_id=str(summary["run_id"]),
        run_id=str(summary["run_id"]),
        provider="desktop_compute",
        model=str(summary["model"]),
        status=str(summary["status"]),
        latency_ms=(summary.get("statistics") or {}).get("mean_latency_ms"),
        payload_hash=payload_hash,
        primary_jsonl=str(log_path.relative_to(ROOT)),
        scientific_validity=str(summary["scientific_validity"]),
        details=summary,
        created_at=str(summary["ended_at"]),
    )
    OpenClawStore(db_path).save_benchmark_record(record)


if __name__ == "__main__":
    raise SystemExit(main())
