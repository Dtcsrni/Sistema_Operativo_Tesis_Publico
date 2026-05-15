from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


"""trigger_edge_npu_benchmark.py — Lanzador SSH del benchmark NPU desde PC Windows.

Uso:
  python 07_scripts/trigger_edge_npu_benchmark.py
  python 07_scripts/trigger_edge_npu_benchmark.py --step-id VAL-STEP-734 --model qwen3:4b

Requisitos:
  - SSH key en ~/.ssh/id_ed25519_orangepi_nopass (configurado en ssh_config)
  - Edge encendido en orangepi-lan (192.168.1.124)
  - setup_edge_rkllm.sh ejecutado previo en el edge
"""

import argparse
import json
import os
import subprocess

import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
SSH_HOST = os.getenv("OPENCLAW_EDGE_SSH_HOST", "orangepi-lan")
SSH_USER = os.getenv("OPENCLAW_EDGE_SSH_USER", "ErickV")
EDGE_REPO = os.getenv("OPENCLAW_EDGE_REPO_PATH", "~/Sistema_Operativo_Tesis_Posgrado")
LOCAL_RESULTS_DIR = ROOT / "runtime" / "edge_iot" / "benchmarks"

SSH_KEY = os.path.expanduser(os.getenv("OPENCLAW_EDGE_SSH_KEY", "~/.ssh/id_ed25519_orangepi_nopass"))

def ssh_run(cmd: str, timeout: int = 30) -> tuple[int, str, str]:
    """Ejecuta comando en el edge via SSH. Retorna (returncode, stdout, stderr)."""
    full_cmd = [
        "ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no",
        "-i", SSH_KEY, f"{SSH_USER}@{SSH_HOST}", cmd,
    ]
    try:
        r = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 1, "", f"Timeout despues de {timeout}s"
    except Exception as e:
        return 1, "", str(e)

def check_edge_connectivity() -> bool:
    rc, out, err = ssh_run("echo PONG", timeout=8)
    if rc == 0 and "PONG" in out:
        print(f"[OK] Edge conectado: {SSH_HOST}")
        return True
    print(f"[ERROR] No se puede conectar al edge: {err.strip()}")
    return False

def check_rkllm_setup() -> dict[str, bool]:
    """Verifica estado del RKLLM en el edge."""
    checks = {}
    rc, out, _ = ssh_run("ls /dev/dri/renderD* 2>/dev/null && echo NPU_OK || echo NPU_MISSING")
    checks["npu_device"] = "NPU_OK" in out

    rc, out, _ = ssh_run(f"ls ~/runtime/drivers/rknn/librkllmrt.so 2>/dev/null && echo LIB_OK || echo LIB_MISSING")
    checks["rkllm_lib"] = "LIB_OK" in out

    rc, out, _ = ssh_run(f"ls ~/runtime/models/edge/*.rkllm 2>/dev/null | wc -l")
    checks["rkllm_models"] = out.strip().isdigit() and int(out.strip()) > 0

    rc, out, _ = ssh_run("ollama list 2>/dev/null | wc -l")
    checks["ollama"] = out.strip().isdigit() and int(out.strip()) > 1

    return checks

def run_ollama_benchmark(step_id: str, model: str) -> dict:
    """Benchmark usando Ollama CPU en el edge (siempre disponible)."""
    print(f"\n[BENCH] Ejecutando benchmark Ollama CPU en edge con modelo {model}...")

    categories = [
        ("iot_decision", "Un nodo IoT tiene RSSI=-125dBm. ¿Debe conmutar a relay P2P? Responde en 2 oraciones."),
        ("edge_reasoning", "¿Qué ventaja tiene procesar datos en el edge vs nube para IoT urbano? 2 oraciones."),
        ("code_gen", "Escribe una función Python para calcular el promedio de una lista de floats."),
    ]

    results = []
    for cat_id, prompt in categories:
        print(f"  [RUN] {cat_id}...", end="", flush=True)
        payload = json.dumps({
            "model": model, "prompt": prompt, "stream": False,
            "options": {"num_predict": 80, "num_ctx": 512, "temperature": 0.1}
        })
        cmd = f"curl -s -X POST http://127.0.0.1:11434/api/generate -d '{payload}' --max-time 60"
        t0 = time.perf_counter()
        rc, out, err = ssh_run(cmd, timeout=90)
        elapsed = time.perf_counter() - t0

        if rc != 0 or not out.strip():
            print(f" FAIL ({err.strip()[:60]})")
            results.append({"category": cat_id, "status": "failed", "latency_ms": None})
            continue

        try:
            data = json.loads(out)
            response = data.get("response", "")
            eval_count = data.get("eval_count", 0)
            eval_duration_ns = data.get("eval_duration", 1)
            tps = eval_count / (eval_duration_ns / 1e9) if eval_duration_ns > 0 else 0
            latency_ms = elapsed * 1000
            print(f" OK ({latency_ms:.0f}ms, {tps:.1f} TPS)")
            results.append({
                "category": cat_id,
                "status": "ok",
                "latency_ms": round(latency_ms, 1),
                "tokens_per_second": round(tps, 2),
                "output_preview": response[:120],
            })
        except Exception as e:
            print(f" PARSE_ERROR ({e})")
            results.append({"category": cat_id, "status": "parse_error"})

    return {
        "step_id": step_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "device": "Orange Pi 5 Plus (RK3588)",
        "hardware_acceleration": f"Ollama CPU ({model})",
        "model": model,
        "samples": results,
        "summary": {
            "total": len(results),
            "ok": sum(1 for r in results if r.get("status") == "ok"),
            "avg_tps": round(
                sum(r.get("tokens_per_second", 0) for r in results if r.get("tokens_per_second"))
                / max(1, sum(1 for r in results if r.get("tokens_per_second"))), 2
            ),
            "avg_latency_ms": round(
                sum(r.get("latency_ms", 0) for r in results if r.get("latency_ms"))
                / max(1, sum(1 for r in results if r.get("latency_ms"))), 1
            ),
        }
    }

def main():
    parser = argparse.ArgumentParser(description="Lanzador SSH de benchmark NPU/Ollama en el edge")
    parser.add_argument("--step-id", default="VAL-STEP-734")
    parser.add_argument("--model", default="qwen3:4b",
                        help="Modelo Ollama a usar en el edge (default: qwen3:4b)")
    parser.add_argument("--setup-rkllm", action="store_true",
                        help="Ejecutar setup_edge_rkllm.sh primero")
    args = parser.parse_args()

    print(f"[START] Trigger Edge Benchmark — {args.step_id}")
    print(f"[TARGET] {SSH_USER}@{SSH_HOST}")

    if not check_edge_connectivity():
        return 1

    checks = check_rkllm_setup()
    print(f"\n[STATUS] Edge hardware:")
    print(f"  NPU device:   {'[OK]' if checks['npu_device'] else '[--]'}")
    print(f"  RKLLM lib:    {'[OK]' if checks['rkllm_lib'] else '[--] (ejecutar setup_edge_rkllm.sh)'}")
    print(f"  RKLLM models: {'[OK]' if checks['rkllm_models'] else '[--] (requiere conversion de modelo)'}")
    print(f"  Ollama:       {'[OK]' if checks['ollama'] else '[--]'}")

    if args.setup_rkllm:
        print("\n[INFO] Ejecutando setup RKLLM en edge...")
        rc, out, err = ssh_run("bash -s", timeout=120)  # Solo si se transfiere el script
        print(out)

    # Benchmark Ollama CPU (disponible siempre)
    if checks["ollama"]:
        result = run_ollama_benchmark(args.step_id, args.model)

        # Guardar resultado local
        LOCAL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        out_path = LOCAL_RESULTS_DIR / f"edge_ollama_benchmark_{ts}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

        # Actualizar benchmark_latest.json
        latest_path = LOCAL_RESULTS_DIR / "benchmark_latest.json"
        try:
            existing = json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            existing = {}
        existing["ollama_cpu_benchmark"] = result
        existing["last_updated"] = datetime.now(timezone.utc).isoformat()
        latest_path.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")

        ok = result["summary"]["ok"]
        total = result["summary"]["total"]
        avg_tps = result["summary"]["avg_tps"]
        print(f"\n[DONE] Benchmark completado: {ok}/{total} OK, avg TPS: {avg_tps}")
        print(f"[SAVE] Resultado en {out_path}")

        if not checks["rkllm_lib"]:
            print("\n[NEXT] Para benchmark NPU nativo:")
            print("  1. Copia setup_edge_rkllm.sh al edge y ejecútalo")
            print("  2. Descarga modelo .rkllm desde HuggingFace")
            print("  3. Ejecuta: python3 07_scripts/run_edge_npu_benchmark.py")
    else:
        print("[ERROR] Ollama no disponible en el edge. Verifica la instalación.")
        return 1

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
