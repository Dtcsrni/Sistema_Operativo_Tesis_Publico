"""rolling_summary.py — Resumen rolling de conversación para compresión de memoria.

Política de eficiencia de tokens:
  Cuando un chat acumula > TRIGGER_TURNS turnos, los turnos más antiguos
  se comprimen en un resumen compacto vía el modelo edge más ligero.
  Esto mantiene el contexto semántico con ~70% menos tokens.

Integración:
  - Se llama en background (hilo daemon) desde _save_turn_to_state()
  - Lee/escribe state["rolling_summary"] y state["turns"]
  - Usa el modelo edge más pequeño disponible (qwen2.5:0.5b → qwen3:4b)
  - Se activa cada TRIGGER_TURNS (default: 8) turnos acumulados
  - Sin imports del bot (evita circularidad): detección de modelos via HTTP
"""
from __future__ import annotations

import json
import os
import threading
import urllib.request as _req_lib
from typing import Any

# ── Configuración ─────────────────────────────────────────────────────────────
TRIGGER_TURNS = int(os.getenv("OPENCLAW_SUMMARY_TRIGGER_TURNS", "8"))
KEEP_RECENT = int(os.getenv("OPENCLAW_SUMMARY_KEEP_RECENT", "4"))
SUMMARY_MAX_CHARS = int(os.getenv("OPENCLAW_SUMMARY_MAX_CHARS", "400"))
# qwen2.5:0.5b está instalado en edge (397MB, ~15 TPS Ollama CPU)
# Orden: más ligero primero, fallback a modelos más pesados
MODEL_PREFERENCE = [
    m.strip()
    for m in os.getenv(
        "OPENCLAW_SUMMARY_MODELS",
        "qwen2.5:0.5b,gemma3:1b,qwen3:1.7b,qwen3:4b,qwen2.5:0.5b",
    ).split(",")
    if m.strip()
]

_SUMMARY_PROMPT_TEMPLATE = (
    "Eres un compresor de contexto. Resume estos {n} turnos de conversación "
    "en máximo 3 líneas compactas en español, preservando:\n"
    "- Temas tratados y decisiones tomadas\n"
    "- Preferencias o ajustes del usuario\n"
    "- Contexto técnico relevante\n"
    "No uses listas largas. Solo lo esencial.\n\n"
    "TURNOS:\n{turns_text}\n\n"
    "RESUMEN COMPACTO:"
)


def _build_turns_text(turns: list[dict[str, Any]]) -> str:
    lines = []
    for t in turns:
        u = str(t.get("user", "")).strip()[:120]
        a = str(t.get("assistant", "")).strip()[:160]
        if u:
            lines.append(f"U: {u}")
        if a:
            lines.append(f"A: {a}")
    return "\n".join(lines)


def _select_summary_model(base_url: str) -> str:
    """Selecciona el modelo más ligero disponible consultando /api/tags directamente.

    No importa telegram_bot para evitar dependencia circular.
    """
    try:
        req = _req_lib.Request(
            base_url.rstrip("/") + "/api/tags",
            method="GET",
        )
        with _req_lib.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        model_names = {m["name"] for m in data.get("models", [])}
        # Normalizar: quitar tags duplicados (qwen2.5:0.5b == qwen2.5:0.5b)
        for pref in MODEL_PREFERENCE:
            if pref in model_names:
                return pref
            # Fallback: comparar sin tag
            base_pref = pref.split(":")[0]
            for name in model_names:
                if name.split(":")[0] == base_pref:
                    return name
    except Exception:
        pass
    return MODEL_PREFERENCE[0] if MODEL_PREFERENCE else "qwen2.5:0.5b"


def _run_summary(
    state: dict[str, Any],
    *,
    base_url: str,
    model: str,
    turns_to_compress: list[dict[str, Any]],
    lock: threading.Lock | None = None,
) -> None:
    """Ejecuta la generación del resumen en background. Actualiza state in-place."""
    turns_text = _build_turns_text(turns_to_compress)
    prompt = _SUMMARY_PROMPT_TEMPLATE.format(
        n=len(turns_to_compress),
        turns_text=turns_text,
    )
    try:

        payload = json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 120, "num_ctx": 1024, "temperature": 0.1},
                "keep_alive": "5m",
            },
            ensure_ascii=False,
        ).encode("utf-8")
        r = _req_lib.Request(base_url.rstrip("/") + "/api/generate", data=payload, method="POST")
        r.add_header("Content-Type", "application/json")
        with _req_lib.urlopen(r, timeout=40) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        summary_text = str(data.get("response", "")).strip()
        if not summary_text:
            return
        summary_text = summary_text[:SUMMARY_MAX_CHARS]
        # Combinar con resumen previo si existe
        prev = str(state.get("rolling_summary", "")).strip()
        if prev:
            combined = f"{prev} | {summary_text}"
            summary_text = combined[:SUMMARY_MAX_CHARS]
        ctx = lock or _noop_ctx()
        with ctx:
            state["rolling_summary"] = summary_text
            # Eliminar los turnos comprimidos del estado
            all_turns = list(state.get("turns", []))
            compressed_ids = {id(t) for t in turns_to_compress}
            state["turns"] = [t for t in all_turns if id(t) not in compressed_ids]
    except Exception:
        pass


class _noop_ctx:
    def __enter__(self): return self
    def __exit__(self, *_): pass


def maybe_trigger_summary(
    state: dict[str, Any],
    *,
    lock: threading.Lock | None = None,
) -> bool:
    """Comprueba si se debe generar resumen rolling y lo lanza en daemon thread.

    Args:
        state: estado de sesión del chat (mutado en background)
        lock: lock opcional para acceso concurrente al state

    Returns:
        True si se disparó la generación, False si no.
    """
    all_turns = [
        t for t in list(state.get("turns", []))
        if str(t.get("kind", "normal")) != "greeting"
    ]
    if len(all_turns) < TRIGGER_TURNS:
        return False

    # Comprimir los turnos más antiguos, conservar KEEP_RECENT recientes
    turns_to_compress = all_turns[:-KEEP_RECENT] if len(all_turns) > KEEP_RECENT else all_turns[:-1]
    if not turns_to_compress:
        return False

    base_url = os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = _select_summary_model(base_url)

    thread = threading.Thread(
        target=_run_summary,
        kwargs={
            "state": state,
            "base_url": base_url,
            "model": model,
            "turns_to_compress": turns_to_compress,
            "lock": lock,
        },
        daemon=True,
        name="openclaw-rolling-summary",
    )
    thread.start()
    return True
