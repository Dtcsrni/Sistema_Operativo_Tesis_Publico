#!/usr/bin/env python3
"""Watcher simple para detectar `run_summary` nuevos en runtime/pc_control/benchmarks/runs.

- Actualiza `moe_run_summaries.csv` usando `collect_run_summaries.py` cuando aparece un `run_summary` nuevo.
- Registra eventos en `runtime/pc_control/benchmarks/watch_notifications.log`.
- Opcional: enviar notificación final por Telegram cuando todos los modelos esperados terminen.

Uso: python watch_runs.py --interval 15
Entorno opcional:
 - WATCHER_NOTIFY_CMD: comando a ejecutar cuando hay un nuevo run (formateable con keys del run)
 - WATCHER_EXPECTED_MODELS: lista CSV de modelos esperados para la corrida (ej: qwen3:4b,qwen2.5:1.5b)
 - WATCHER_TELEGRAM_NOTIFY: si '1', intenta usar el bot de OpenClaw para enviar el aviso final
"""
from pathlib import Path
import json
import time
import argparse
import subprocess
import sys
import os
import hashlib

# Asegurar que el root del repo esté en el path para importar 'runtime'
sys.path.append(".")

BASE = Path("runtime/pc_control/benchmarks")
RUNS_DIR = BASE / "runs"
STATE_FILE = BASE / ".watcher_state.json"
LOG_FILE = BASE / "watch_notifications.log"
CSV_SCRIPT = Path("07_scripts/benchmarks/collect_run_summaries.py")

# Optional OpenClaw integration
try:
    from runtime.openclaw.openclaw_local import telegram_bot
    from runtime.openclaw.openclaw_local import runtime_status
    _OPENCLAW_INTEGRATION = True
except Exception:
    telegram_bot = None
    runtime_status = None
    _OPENCLAW_INTEGRATION = False

_TELEGRAM_AVAILABLE = _OPENCLAW_INTEGRATION and telegram_bot is not None


def load_state():
    if not STATE_FILE.exists():
        return {"seen": [], "final_notified": []}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"seen": [], "final_notified": []}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def log(msg):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    line = f"{ts} {msg}\n"
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        LOG_FILE.open("a", encoding="utf-8").write(line)
    except Exception:
        pass
    print(line, end="")


def find_run_summaries():
    runs = []
    if not RUNS_DIR.exists():
        return runs
    for p in sorted(RUNS_DIR.glob("BENCH-*.jsonl")):
        try:
            with p.open("r", encoding="utf-8") as fh:
                for ln in fh:
                    ln = ln.strip()
                    if not ln:
                        continue
                    try:
                        obj = json.loads(ln)
                    except Exception:
                        continue
                    if obj.get("record_type") == "run_summary":
                        runs.append({
                            "run_id": obj.get("run_id"),
                            "model": obj.get("model"),
                            "status": obj.get("status"),
                            "record_hash": obj.get("record_hash"),
                            "file": str(p),
                            "started_at": obj.get("started_at"),
                            "ended_at": obj.get("ended_at"),
                            "mean_latency_ms": obj.get("mean_latency_ms"),
                        })
                        break
        except Exception:
            continue
    return runs


def update_csv():
    try:
        subprocess.run([sys.executable, str(CSV_SCRIPT)], check=True)
        log(f"Updated CSV via {CSV_SCRIPT}")
    except Exception as e:
        log(f"Failed to update CSV: {e}")


def _run_notify_cmd(run):
    cmd = os.environ.get("WATCHER_NOTIFY_CMD")
    if not cmd:
        return
    try:
        formatted = cmd.format(**run)
        subprocess.run(formatted, shell=True)
        log(f"Ran notify cmd: {formatted}")
    except Exception as e:
        log(f"Notify cmd failed: {e}")


def _send_telegram_progress(expected_models, summary_map, elapsed_seconds, remaining_estimate_seconds):
    """Envía actualización de progreso a Telegram con porcentaje, tiempo restante y barra visual."""
    if not _TELEGRAM_AVAILABLE or not os.getenv("WATCHER_TELEGRAM_NOTIFY", "0").strip() == "1":
        return {"status": "skipped"}
    try:
        chat_id = os.getenv("OPENCLAW_TELEGRAM_CHAT_ID", "").split(",")[0].strip()
        if not chat_id:
            return {"status": "skipped"}

        finished = sum(1 for m in expected_models if summary_map.get(m))
        total = len(expected_models)
        pct = int(100 * finished / total) if total > 0 else 0
        
        # Barra de progreso visual
        bar_len = 10
        filled = int(bar_len * finished / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_len - filled)

        # Formatear tiempos
        elapsed_min = int(elapsed_seconds / 60)
        elapsed_sec = int(elapsed_seconds % 60)
        # Obtener info del host para el reporte (Best Practice: Contexto de Nodo)
        node_name = os.getenv("OPENCLAW_NODE_NAME", platform.node())
        
        lines = [f"🧬 <b>Sincronización Epistémica MoE:</b> <code>{pct}%</code>"]
        lines.append(f"<code>[{bar}]</code> ({finished}/{total})")
        lines.append(f"⏱ <b>Tiempo:</b> {elapsed_min}:{elapsed_sec:02d}m transcurridos")
        if finished < total:
            rem_min, rem_sec = divmod(int(remaining_estimate_seconds), 60)
            lines.append(f"⏳ <b>Restante est.:</b> ~{rem_min}:{rem_sec:02d}m")
        
        lines.append(f"\n<i>Nodo: {node_name}</i>")
        lines.append("")
        
        for m in expected_models:
            s = summary_map.get(m)
            if s:
                status_emoji = "✅" if s.get("status") == "ok" else "⚠️"
                try:
                    latency = float(s.get("mean_latency_ms") or 0)
                    latency_str = f"{latency:.0f}ms"
                except (TypeError, ValueError):
                    latency_str = "n/a"
                lines.append(f"{status_emoji} <code>{m}</code>: {latency_str}")
            else:
                lines.append(f"⏳ <code>{m}</code>: pendiente")

        text = "\n".join(lines)
        res = telegram_bot.send_message(chat_id, text)
        log(f"Telegram progress report result: {res}")
        return res
    except Exception as e:
        log(f"Telegram progress error: {e}")
        return {"status": "error"}


def _send_telegram_final(expected_models, summary_map):
    """Notificación final cuando todos los modelos terminen."""
    if not _TELEGRAM_AVAILABLE or not os.getenv("WATCHER_TELEGRAM_NOTIFY", "0").strip() == "1":
        return {"status": "skipped", "reason": "telegram_not_enabled"}
    try:
        chat_id = os.getenv("OPENCLAW_TELEGRAM_CHAT_ID", "").split(",")[0].strip()
        if not chat_id:
            return {"status": "skipped", "reason": "no_chat_id"}

        lines = ["🎉 Bench MOE: TODOS LOS MODELOS COMPLETADOS"]
        lines.append("")
        for m in expected_models:
            s = summary_map.get(m, {"status": "missing"})
            status_emoji = "✅" if s.get("status") == "ok" else "❌"
            latency = s.get("mean_latency_ms", 0)
            lines.append(f"{status_emoji} {m}")
            if latency:
                lines.append(f"   ⏱ Latencia media: {latency:.0f}ms")
            if s.get("run_id"):
                lines.append(f"   📍 Run: {s.get('run_id')}")

        csv_path = BASE / "moe_run_summaries.csv"
        if csv_path.exists():
            lines.append(f"\n📄 Resultados CSV guardados")

        text = "\n".join(lines)
        res = telegram_bot.send_message(chat_id, text)
        log(f"Telegram final notify: {res}")
        return res
    except Exception as e:
        log(f"Telegram notify error: {e}")
        return {"status": "error", "detail": str(e)}


def _compute_summary_map(runs):
    # Keep the most recent run per model
    mapping = {}
    for r in runs:
        model = r.get("model")
        if not model:
            continue
        mapping[model] = r
    return mapping


def _estimate_remaining_time(expected_models, summary_map, elapsed_seconds):
    """Estima el tiempo restante basado en el tiempo real transcurrido."""
    finished = sum(1 for m in expected_models if summary_map.get(m))
    total = len(expected_models)
    pending = total - finished
    
    if pending <= 0:
        return 0
    
    if finished > 0:
        # Tiempo promedio por modelo completado
        avg_time_per_model = elapsed_seconds / finished
        return int(avg_time_per_model * pending)
    else:
        # Estimación inicial: 2-3 minutos por modelo (ajustable según hardware)
        return pending * 150 


def _all_expected_finished(expected_models, summary_map):
    """Verifica si todos los modelos esperados tienen un resultado registrado."""
    if not expected_models:
        return False
    for m in expected_models:
        if m not in summary_map:
            return False
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=15, help="Polling interval seconds")
    args = parser.parse_args()

    state = load_state()
    seen = set(state.get("seen", []))
    final_notified = set(state.get("final_notified", []))
    last_progress_report = {}  # Track last reported progress per model

    expected_raw = os.getenv("WATCHER_EXPECTED_MODELS", "").strip()
    expected_models = [s.strip() for s in expected_raw.split(",") if s.strip()] if expected_raw else []

    log(f"Watcher started; polling {RUNS_DIR} every {args.interval}s")
    
    is_notify_enabled = os.getenv("WATCHER_TELEGRAM_NOTIFY", "0").strip() == "1"
    if not _TELEGRAM_AVAILABLE:
        log("Telegram NOT available: failed to import telegram_bot module")
    if not is_notify_enabled:
        log("Telegram notification DISABLED (WATCHER_TELEGRAM_NOTIFY != 1)")

    if expected_models:
        log(f"Expecting models: {', '.join(expected_models)}")
        # Enviar notificación inicial
        if _TELEGRAM_AVAILABLE and is_notify_enabled:
            try:
                chat_id = os.getenv("OPENCLAW_TELEGRAM_CHAT_ID", "").split(",")[0].strip()
                if chat_id:
                    node_info = ""
                    if runtime_status:
                        try:
                            status = runtime_status.probe_runtime_status()
                            node_info = f"\n📍 <b>Nodo:</b> {status.get('host', {}).get('orange_pi_model') or platform.node()}"
                        except Exception:
                            pass
                    
                    msg = f"🚀 <b>Iniciando Watcher MOE:</b> {len(expected_models)} modelos esperados.{node_info}\n<i>Modo: Resiliencia Activa</i>"
                    res = telegram_bot.send_message(chat_id, msg)
                    log(f"Telegram startup notify sent: {res}")
                else:
                    log("Telegram startup skip: no OPENCLAW_TELEGRAM_CHAT_ID found")
            except Exception as e:
                log(f"Failed to send startup telegram: {e}")

    progress_cycles = 0
    progress_interval_cycles = max(1, int(120 / args.interval))  # Report every ~120 seconds (2 minutes)
    start_time = time.time()  # Rastrear tiempo de inicio

    try:
        while True:
            runs = find_run_summaries()
            summary_map = _compute_summary_map(runs)

            # Detectar nuevos run_summary
            for r in runs:
                rid = r.get("run_id")
                if not rid:
                    continue
                if rid not in seen:
                    msg = f"New run_summary: {rid} model={r.get('model')} status={r.get('status')}"
                    log(msg)
                    update_csv()
                    _run_notify_cmd(r)
                    seen.add(rid)
                    state["seen"] = sorted(list(seen))
                    save_state(state)
                    # Enviar notificación inmediata de modelo completado a Telegram
                    if _TELEGRAM_AVAILABLE and os.getenv("WATCHER_TELEGRAM_NOTIFY", "0").strip() == "1":
                        try:
                            chat_id = os.getenv("OPENCLAW_TELEGRAM_CHAT_ID", "").split(",")[0].strip()
                            if chat_id:
                                model = r.get('model', 'unknown')
                                latency = r.get('mean_latency_ms')
                                try:
                                    latency_val = float(latency) if latency else None
                                    latency_str = f"{latency_val:.0f}ms" if latency_val is not None else "n/a"
                                except (TypeError, ValueError):
                                    latency_str = "n/a"
                                status_emoji = "✅" if r.get('status') == 'ok' else "⚠️"
                                msg = f"{status_emoji} <b>{model} completado</b> (latencia: {latency_str})"
                                res = telegram_bot.send_message(chat_id, msg)
                                log(f"Telegram model completion notify: {res}")
                        except Exception as e:
                            log(f"Failed to send model completion telegram: {e}")

            # Enviar reporte de progreso periódicamente (cada ~60s)
            if expected_models:
                progress_cycles += 1
                elapsed = time.time() - start_time
                remaining = _estimate_remaining_time(expected_models, summary_map, elapsed)
                
                if progress_cycles >= progress_interval_cycles:
                    progress_cycles = 0
                    finished = sum(1 for m in expected_models if summary_map.get(m))
                    # Siempre enviar reporte de progreso cada minuto
                    _send_telegram_progress(expected_models, summary_map, elapsed, remaining)

                # Revisar condición final
                key_material = ",".join(sorted([f"{m}:{summary_map.get(m, {}).get('status','missing')}" for m in expected_models]))
                sig = hashlib.sha256(key_material.encode("utf-8")).hexdigest()
                if sig not in final_notified and _all_expected_finished(expected_models, summary_map):
                    _send_telegram_final(expected_models, summary_map)
                    final_notified.add(sig)
                    state["final_notified"] = sorted(list(final_notified))
                    save_state(state)

            time.sleep(args.interval)
    except KeyboardInterrupt:
        log("Watcher stopped by user")
    except Exception as e:
        log(f"Watcher exited error: {e}")


if __name__ == "__main__":
    main()
