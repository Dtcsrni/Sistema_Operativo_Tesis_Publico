from __future__ import annotations

import json
import os
import platform
import re
import shutil
import socket
import struct
import threading
import time
import unicodedata
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime, timezone
from html import unescape
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from urllib import error, parse, request
from uuid import uuid4

from .audio_engine import download_telegram_file, synthesize_speech, transcribe_audio
from .contracts import RequestTrace, TaskEnvelope, VoiceMessageArtifact
from .engine import route_task
from .image_backend import generate_image_from_prompt
from .policies import load_domain_policies, load_provider_registry
from .runtime_status import build_preflight_report, probe_runtime_status
from .session_layer import parse_channel_command, process_channel_text
from .storage import OpenClawStore
from .web_session import generate_web_session_response


MUTATION_MARKERS = {
    "aplica",
    "borra",
    "cambia",
    "commit",
    "deploy",
    "edita",
    "elimina",
    "escribe",
    "instala",
    "merge",
    "modifica",
    "push",
    "reinicia",
    "restart",
    "systemctl",
}
READ_ONLY_TOOLS = {
    "aprobaciones",
    "estado",
    "eventos",
    "equipo",
    "logs",
    "memoria",
    "modelos",
    "preflight",
    "doctor",
    "presupuesto",
    "secretos",
}
AMBIGUOUS_ACTION_MARKERS = {
    "caracteristicas",
    "características",
    "equipo",
    "genera",
    "generar",
    "imagen",
    "resultado del escaneo",
    "scan",
    "scanner",
    "escaneo",
}
MODEL_REQUEST_MARKERS = {
    "con mistral",
    "ejecuta con",
    "modelo",
    "usa mistral",
    "usar mistral",
}
CHAT_MEMORY_LIMIT = 12
CHAT_SUMMARY_LIMIT = 900
MEMORY_ITEM_LIMIT = 20
MEXICO_TZ = "America/Mexico_City"
NTP_SERVER = "cronos.cenam.mx"
CALL_STYLES = {"estable", "rapida"}
APPROVAL_CONFIRMATIONS = {"si", "sí", "valido", "válido", "apruebo", "aprobado", "ejecuta", "ejecutalo", "ejecútalo", "hazlo"}
APPROVAL_TTL_SECONDS = 30 * 60
AMBIGUOUS_INTENTS = {"ambiguous", "general_chat"}


@dataclass(frozen=True)
class ChatBackendCandidate:
    provider: str
    base_url: str
    model: str
    timeout_seconds: int
    label: str
    semantic: bool = True


@dataclass(frozen=True)
class ChatExecutionPlan:
    trace_id: str
    request_kind: str
    complexity: str
    deadline_seconds: int
    use_web_assisted: bool
    web_timeout_seconds: int
    api_timeout_seconds: int
    candidates: list[ChatBackendCandidate]
    fallback_policy: str


class TypingHeartbeat:
    def __init__(self, chat_id: str, interval: float = 4.5):
        self.chat_id = chat_id
        self.interval = interval
        self.stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self):
        def _heartbeat():
            while not self.stop_event.is_set():
                send_chat_action(self.chat_id, "typing")
                # Wait for interval or stop event
                self.stop_event.wait(self.interval)

        self._thread = threading.Thread(target=_heartbeat, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)


def _env_int(name: str, default: int, *, minimum: int = 1, maximum: int = 3600) -> int:
    try:
        value = int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


def _env_flag(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on", "si", "sí"}


def _elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000.0, 3)


def _token_estimate(text: str) -> int:
    stripped = text.strip()
    if not stripped:
        return 0
    # Estimación rápida para trazabilidad de latencia sin dependencia de tokenizer.
    return max(1, (len(stripped) + 3) // 4)


def _normalized_message_hash(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text or "").lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _should_use_semantic_profile(argument: str, fallback: dict[str, str]) -> bool:
    if _env_flag("OPENCLAW_CHAT_FORCE_SEMANTIC", default=False):
        return True
    lowered = argument.lower()
    if any(marker in lowered for marker in AMBIGUOUS_ACTION_MARKERS):
        return True
    if len(argument.strip()) >= _env_int("OPENCLAW_CHAT_AMBIGUOUS_MIN_CHARS", 140, minimum=20, maximum=800):
        return True
    try:
        confidence = float(str(fallback.get("confidence", "0") or "0"))
    except ValueError:
        confidence = 0.0
    if fallback.get("intent") in AMBIGUOUS_INTENTS and confidence <= 0.60:
        return True
    return False


_CHAT_LOCKS: dict[str, threading.Lock] = {}
_CHAT_LOCKS_GUARD = threading.Lock()
_EDGE_SEMAPHORE = threading.BoundedSemaphore(_env_int("OPENCLAW_EDGE_MAX_CONCURRENT", 1, minimum=1, maximum=8))
_DESKTOP_SEMAPHORE = threading.BoundedSemaphore(_env_int("OPENCLAW_DESKTOP_MAX_CONCURRENT", 1, minimum=1, maximum=8))
_WARMUP_DONE = False
_WARMUP_GUARD = threading.Lock()


def _chat_lock(chat_id: str) -> threading.Lock:
    key = chat_id or "unknown"
    with _CHAT_LOCKS_GUARD:
        lock = _CHAT_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _CHAT_LOCKS[key] = lock
        return lock


def telegram_configured() -> bool:
    return bool(os.getenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "").strip() and os.getenv("OPENCLAW_TELEGRAM_CHAT_ID", "").strip())


def parse_command(text: str) -> tuple[str, str]:
    return parse_channel_command(text)


def is_authorized_chat(chat_id: str) -> bool:
    allowed = {
        item.strip()
        for item in os.getenv("OPENCLAW_TELEGRAM_CHAT_ID", "").replace(";", ",").split(",")
        if item.strip()
    }
    return chat_id in allowed


def redact_text(text: str) -> str:
    redacted = text
    for marker in ("TOKEN", "KEY", "SECRET", "PASSWORD"):
        if marker.lower() in redacted.lower():
            return "<redacted>"
    return redacted[:1000]


def get_updates(*, offset: int | None = None, timeout_seconds: int = 20, limit: int = 10) -> list[dict[str, Any]]:
    token = os.getenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return []
    params: dict[str, str] = {
        "timeout": str(max(0, timeout_seconds)),
        "limit": str(max(1, min(limit, 100))),
        "allowed_updates": json.dumps(["message"], ensure_ascii=False),
    }
    if offset is not None:
        params["offset"] = str(offset)
    url = f"https://api.telegram.org/bot{token}/getUpdates?{parse.urlencode(params)}"
    try:
        with request.urlopen(url, timeout=timeout_seconds + 5) as response:
            raw = response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        print(f"[DEBUG] Error fetching updates: {exc}")
        return []
    data = json.loads(raw)
    if not data.get("ok"):
        return []
    return list(data.get("result", []))


def send_message(chat_id: str, text: str) -> dict[str, Any]:
    token = os.getenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {"status": "skipped", "reason": "telegram_not_configured"}
    payload = parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text[:3900],
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    # Asegurar que usamos POST con el modo correcto
    req = request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with request.urlopen(req, timeout=int(os.getenv("OPENCLAW_TELEGRAM_TIMEOUT_SECONDS", "15"))) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except Exception as exc:
        print(f"[DEBUG] Error sending message: {exc}")
        return {"status": "error", "detail": str(exc)}
    return {"status": "sent" if data.get("ok") else "error", "detail": data.get("description", "sent")}


def send_chat_action(chat_id: str, action: str = "typing") -> dict[str, Any]:
    token = os.getenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {"status": "skipped", "reason": "telegram_not_configured"}
    payload = parse.urlencode({"chat_id": chat_id, "action": action}).encode("utf-8")
    req = request.Request(f"https://api.telegram.org/bot{token}/sendChatAction", data=payload, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with request.urlopen(req, timeout=int(os.getenv("OPENCLAW_TELEGRAM_TIMEOUT_SECONDS", "5"))) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except (error.URLError, json.JSONDecodeError, OSError) as exc:
        return {"status": "error", "detail": str(exc)}
    return {"status": "sent" if data.get("ok") else "error", "detail": data.get("description", "sent")}


def send_voice_message(chat_id: str, audio_path: Path, *, caption: str = "") -> dict[str, Any]:
    token = os.getenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {"status": "skipped", "reason": "telegram_not_configured"}
    if not audio_path.exists():
        return {"status": "error", "detail": f"audio_not_found:{audio_path}"}

    fields: dict[str, str] = {"chat_id": chat_id}
    if caption.strip():
        fields["caption"] = caption[:500]
    body, content_type = _multipart_for_telegram(fields=fields, file_field="voice", file_path=audio_path)
    req = request.Request(f"https://api.telegram.org/bot{token}/sendVoice", data=body, method="POST")
    req.add_header("Content-Type", content_type)

    try:
        with request.urlopen(req, timeout=int(os.getenv("OPENCLAW_TELEGRAM_TIMEOUT_SECONDS", "20"))) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except (error.URLError, json.JSONDecodeError) as exc:
        return {"status": "error", "detail": str(exc)}
    return {"status": "sent" if data.get("ok") else "error", "detail": data.get("description", "sent")}


def send_photo_message(chat_id: str, image_path: Path, *, caption: str = "") -> dict[str, Any]:
    token = os.getenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return {"status": "skipped", "reason": "telegram_not_configured"}
    if not image_path.exists():
        return {"status": "error", "detail": f"image_not_found:{image_path}"}

    fields: dict[str, str] = {"chat_id": chat_id}
    if caption.strip():
        fields["caption"] = caption[:900]
    body, content_type = _multipart_for_telegram(fields=fields, file_field="photo", file_path=image_path)
    req = request.Request(f"https://api.telegram.org/bot{token}/sendPhoto", data=body, method="POST")
    req.add_header("Content-Type", content_type)

    try:
        with request.urlopen(req, timeout=int(os.getenv("OPENCLAW_TELEGRAM_TIMEOUT_SECONDS", "30"))) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except (error.URLError, json.JSONDecodeError) as exc:
        return {"status": "error", "detail": str(exc)}
    return {"status": "sent" if data.get("ok") else "error", "detail": data.get("description", "sent")}


def _ollama_request_options(*, model: str, timeout_seconds: int) -> dict[str, Any]:
    if timeout_seconds <= 10:
        num_predict = _env_int("OPENCLAW_CHAT_SIMPLE_MAX_TOKENS", 96, minimum=16, maximum=512)
        num_ctx = _env_int("OPENCLAW_CHAT_SIMPLE_NUM_CTX", 2048, minimum=512, maximum=8192)
    elif timeout_seconds <= 45:
        num_predict = _env_int("OPENCLAW_CHAT_FACTUAL_MAX_TOKENS", 160, minimum=32, maximum=512)
        num_ctx = _env_int("OPENCLAW_CHAT_FACTUAL_NUM_CTX", 512, minimum=128, maximum=2048)
    else:
        num_predict = _env_int("OPENCLAW_CHAT_HEAVY_MAX_TOKENS", 600, minimum=64, maximum=2048)
        num_ctx = _env_int("OPENCLAW_CHAT_HEAVY_NUM_CTX", 1024, minimum=256, maximum=4096)
    temperature = 0.2 if model.startswith(("qwen3", "gemma3", "mistral")) else 0.3
    return {
        "num_predict": num_predict,
        "num_ctx": num_ctx,
        "temperature": temperature,
    }


def ollama_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120) -> tuple[bool, str]:
    endpoint = base_url.rstrip("/") + "/api/generate"
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": os.getenv("OPENCLAW_MODEL_KEEPALIVE", "10m").strip() or "10m",
            "options": _ollama_request_options(model=model, timeout_seconds=timeout_seconds),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(endpoint, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        return False, f"modelo_no_disponible:http_{exc.code}:{detail[:220]}"
    except Exception as exc:
        return False, f"modelo_no_disponible:{type(exc).__name__}:{exc}"
    return True, str(data.get("response", "")).strip()


def list_ollama_models(base_url: str) -> tuple[bool, list[str]]:
    try:
        with request.urlopen(base_url.rstrip("/") + "/api/tags", timeout=5) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except (error.URLError, json.JSONDecodeError):
        return False, []
    return True, sorted(str(item.get("name", "")) for item in data.get("models", []) if item.get("name"))


def llamacpp_ready(base_url: str) -> bool:
    for path in ("/health", "/props"):
        try:
            with request.urlopen(base_url.rstrip("/") + path, timeout=3):
                return True
        except (error.URLError, error.HTTPError, OSError):
            continue
    return False


def llamacpp_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120) -> tuple[bool, str]:
    endpoint = base_url.rstrip("/") + "/v1/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": min(_env_int("OPENCLAW_CHAT_HEAVY_MAX_TOKENS", 800, minimum=64, maximum=2048), 1024),
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(endpoint, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        return False, f"llamacpp_http_error:{detail[:220]}"
    except Exception as exc:
        return False, f"llamacpp_unavailable:{type(exc).__name__}:{exc}"
    choices = data.get("choices") or []
    if not choices:
        return False, "llamacpp_empty_choices"
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = str(message.get("content", "")).strip()
    if not content:
        return False, "llamacpp_empty_text"
    return True, content


def list_loaded_ollama_models(base_url: str) -> set[str]:
    try:
        with request.urlopen(base_url.rstrip("/") + "/api/ps", timeout=2) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except (error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return set()
    return {str(item.get("name") or item.get("model") or "").strip() for item in data.get("models", []) if item.get("name") or item.get("model")}


def warmup_ollama_model(*, base_url: str, model: str, timeout_seconds: int = 45) -> tuple[bool, str]:
    endpoint = base_url.rstrip("/") + "/api/generate"
    payload = json.dumps(
        {
            "model": model,
            "prompt": "OK",
            "stream": False,
            "keep_alive": os.getenv("OPENCLAW_MODEL_KEEPALIVE", "10m").strip() or "10m",
            "options": {"num_predict": 1, "num_ctx": 512, "temperature": 0},
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request(endpoint, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with request.urlopen(req, timeout=timeout_seconds):
            return True, "ok"
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        return False, f"http_{exc.code}:{detail[:180]}"
    except Exception as exc:
        return False, f"{type(exc).__name__}:{exc}"


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default).strip()
    return [item.strip() for item in raw.split(",") if item.strip()]


def warmup_chat_models(repo_root: Path) -> dict[str, Any]:
    if not _env_flag("OPENCLAW_MODEL_WARMUP_ON_START", default=True):
        return {"status": "skipped", "reason": "disabled"}
    global _WARMUP_DONE
    with _WARMUP_GUARD:
        if _WARMUP_DONE:
            return {"status": "skipped", "reason": "already_done"}
        _WARMUP_DONE = True

    edge_base = os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    desktop_base = os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434")
    edge_models = _csv_env("OPENCLAW_WARMUP_MODELS", os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b"))
    desktop_models = _csv_env("OPENCLAW_DESKTOP_WARMUP_MODELS", os.getenv("OPENCLAW_DESKTOP_COMPUTE_MODEL", "mistral-nemo:12b"))
    timeout_seconds = _env_int("OPENCLAW_MODEL_WARMUP_TIMEOUT", 45, minimum=5, maximum=180)
    results: list[dict[str, Any]] = []

    def warm(base_url: str, provider: str, model: str) -> None:
        if not model:
            return
        if model in list_loaded_ollama_models(base_url):
            results.append({"provider": provider, "model": model, "status": "already_loaded"})
            return
        ok, detail = warmup_ollama_model(base_url=base_url, model=model, timeout_seconds=timeout_seconds)
        results.append({"provider": provider, "model": model, "status": "ok" if ok else "error", "detail": detail})

    for model in edge_models:
        warm(edge_base, "ollama_local", model)
    if _env_flag("OPENCLAW_DESKTOP_COMPUTE_ENABLED", default=True):
        for model in desktop_models:
            warm(desktop_base, "desktop_compute", model)
    return {"status": "ok", "results": results}


def _semantic_intent_prompt(argument: str, *, state: dict[str, Any] | None = None) -> str:
    turns = list(state.get("turns", [])) if state else []
    recent_turns = []
    for turn in turns[-2:]:
        user_turn = str(turn.get("user", "")).strip()
        if user_turn:
            recent_turns.append(f"- usuario: {user_turn[:160]}")
    context_block = "\n".join(recent_turns) if recent_turns else "- contexto: vacío"
    return "\n".join(
        [
            "Eres un clasificador semántico de intención para OpenClaw Telegram.",
            "Devuelve SOLO JSON válido, sin markdown ni texto extra.",
            "Claves requeridas: intent, request_kind, complexity, confidence, route_hint, rationale.",
            "Intents válidos: greeting, system_status, system_models, system_routing, time, memory_summary, factual_short, reasoning, coding, research, general_chat, ambiguous.",
            "request_kind válido: standard, knowledge, coding, reasoning, system, deep.",
            "complexity válido: low, medium, high.",
            "route_hint válido: deterministic_local, model_local, model_desktop, web_assisted.",
            "Reglas semánticas:",
            "- greeting: saludo breve o apertura social.",
            "- system_status: pide estado, salud, latencia, colas, runtime o datos operativos.",
            "- system_models: pide modelos visibles o disponibles.",
            "- system_routing: pide decisión o explicación de ruteo/modelo/backend.",
            "- time: pregunta por hora o fecha actual.",
            "- memory_summary: pregunta por memoria o contexto del chat.",
            "- factual_short: pregunta factual breve que normalmente se puede responder con un modelo local sin web.",
            "- reasoning: pide análisis, comparación, explicación o justificación.",
            "- coding: pide diagnóstico, corrección o revisión de código, scripts, tests o errores.",
            "- research: pide investigar, contrastar fuentes o usar evidencia externa.",
            "- general_chat: charla libre, respuesta breve o ambigüa que no cae en otra clase.",
            "- ambiguous: si no hay señal suficiente.",
            "Mensaje del usuario:",
            argument.strip() or "<vacío>",
            "Contexto reciente:",
            context_block,
        ]
    )


def _parse_json_fragment(text: str) -> dict[str, Any] | None:
    raw = text.strip()
    if not raw:
        return None
    if raw.startswith("{") and raw.endswith("}"):
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            return payload
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        payload = json.loads(raw[start : end + 1])
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _intent_defaults_for_label(intent: str, argument: str) -> dict[str, str]:
    length = len(argument.strip())
    if intent == "greeting":
        return {"intent": intent, "request_kind": "standard", "complexity": "low"}
    if intent in {"system_status", "system_models", "system_routing", "time", "memory_summary"}:
        return {"intent": intent, "request_kind": "system", "complexity": "low"}
    if intent == "factual_short":
        return {"intent": intent, "request_kind": "knowledge", "complexity": "low"}
    if intent == "coding":
        return {"intent": intent, "request_kind": "coding", "complexity": "high"}
    if intent == "reasoning":
        return {"intent": intent, "request_kind": "reasoning", "complexity": "high"}
    if intent == "research":
        return {"intent": intent, "request_kind": "knowledge", "complexity": "high"}
    if intent == "general_chat":
        return {"intent": intent, "request_kind": "standard", "complexity": "medium" if length >= 180 else "low"}
    return {"intent": "ambiguous", "request_kind": "deep" if length >= 180 else "standard", "complexity": "medium" if length >= 180 else "low"}


def _semantic_chat_profile(argument: str, *, repo_root: Path, state: dict[str, Any] | None = None) -> dict[str, str] | None:
    edge_base = os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    default_model = os.getenv("OPENCLAW_CHAT_INTENT_MODEL", os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")).strip() or "qwen3:4b"
    candidates: list[str] = []
    for candidate in (
        default_model,
        "gemma3:4b",
        "qwen3:4b",
        "mistral-nemo:12b",
    ):
        if candidate and candidate not in candidates:
            candidates.append(candidate)
    model = _select_available_model(edge_base, candidates)
    if not model:
        return None

    timeout_seconds = _env_int("OPENCLAW_CHAT_INTENT_TIMEOUT", 8, minimum=2, maximum=30)
    prompt = _semantic_intent_prompt(argument, state=state)
    max_chars = _env_int("OPENCLAW_CHAT_INTENT_PROMPT_MAX_CHARS", 800, minimum=160, maximum=4000)
    prompt = prompt[:max_chars]
    started = time.perf_counter()
    ok, response = ollama_generate(
        base_url=edge_base,
        model=model,
        prompt=prompt,
        timeout_seconds=timeout_seconds,
    )
    if not ok:
        return None

    payload = _parse_json_fragment(response)
    if not payload:
        return None

    intent = str(payload.get("intent", "")).strip().lower()
    profile = _intent_defaults_for_label(intent, argument)
    request_kind = str(payload.get("request_kind", "")).strip().lower()
    if request_kind in {"standard", "knowledge", "coding", "reasoning", "system", "deep"}:
        profile["request_kind"] = request_kind
    complexity = str(payload.get("complexity", "")).strip().lower()
    if complexity in {"low", "medium", "high"}:
        profile["complexity"] = complexity
    confidence = str(payload.get("confidence", "")).strip()
    route_hint = str(payload.get("route_hint", "")).strip().lower()
    rationale = str(payload.get("rationale", "")).strip()
    profile.update(
        {
            "confidence": confidence or "0",
            "route_hint": route_hint or "model_local",
            "rationale": rationale,
            "semantic_model": model,
            "semantic_backend": edge_base,
            "semantic_status": "ok",
            "semantic_ms": f"{_elapsed_ms(started):.3f}",
            "semantic_prompt_chars": str(len(prompt)),
        }
    )
    return profile


def _chat_request_profile_fallback(argument: str) -> dict[str, str]:
    lowered = argument.lower()
    normalized = _normalize_greeting_text(argument)
    coding_markers = (
        "bug",
        "código",
        "codigo",
        "error",
        "errores",
        "fix",
        "patch",
        "python",
        "script",
        "sql",
        "stack trace",
        "traceback",
        "test",
        "tests",
        "terminal",
        "refactor",
        "yaml",
        "json",
        "docker",
        "bash",
        "powershell",
    )
    deep_reasoning_markers = (
        "analiza",
        "compara",
        "corrige",
        "detalla",
        "diagnostica",
        "explica",
        "justifica",
        "más a fondo",
        "mas a fondo",
        "piénsalo",
        "piensalo",
        "profundiza",
        "razona",
        "revisa",
        "seguro",
    )
    reasoning_markers = (
        "por qué",
        "por que",
        "cómo funciona",
        "como funciona",
        "diseña",
        "arquitectura",
        "evalúa",
        "evalua",
        "critica",
        "analiza",
        "analiza a fondo",
        "compara en detalle",
    )
    system_markers = (
        "estado",
        "modelos",
        "routing",
        "arquitectura",
        "diagnostico",
        "diagnóstico",
        "flujo",
        "modelo",
        "selección",
        "seleccion",
        "sistema",
        "datos del sistema",
        "info del sistema",
        "información del sistema",
        "informacion del sistema",
        "datos del equipo",
        "info del equipo",
    )
    latency_markers = (
        "tardo",
        "tardaste",
        "tardaron",
        "demora",
        "demoraste",
        "demoro",
        "demoraron",
        "latencia",
        "espera",
        "cola",
        "saturado",
        "saturada",
        "saturados",
        "saturadas",
        "tiempo de respuesta",
    )
    knowledge_markers = (
        "capital",
        "quién",
        "quien",
        "qué es",
        "que es",
        "cuál",
        "cual",
        "dónde",
        "donde",
        "país",
        "pais",
        "historia",
        "biografía",
        "biografia",
        "poblacion",
        "población",
    )
    if any(marker in lowered for marker in coding_markers):
        return {"intent": "coding", "complexity": "high", "request_kind": "coding", "confidence": "0.80", "route_hint": "model_desktop", "semantic_status": "fallback_rule"}
    if any(marker in normalized for marker in latency_markers) or ("por que" in normalized and "tard" in normalized):
        return {"intent": "system_routing", "complexity": "low", "request_kind": "system", "confidence": "0.88", "route_hint": "deterministic_local", "semantic_status": "fallback_rule"}
    if any(marker in lowered for marker in reasoning_markers):
        return {"intent": "reasoning", "complexity": "high", "request_kind": "reasoning", "confidence": "0.72", "route_hint": "model_desktop", "semantic_status": "fallback_rule"}
    if any(marker in lowered for marker in knowledge_markers):
        return {"intent": "factual_short", "complexity": "low", "request_kind": "knowledge", "confidence": "0.66", "route_hint": "model_local", "semantic_status": "fallback_rule"}
    if any(marker in lowered for marker in system_markers):
        intent = "system_models" if "model" in lowered else "system_status"
        return {"intent": intent, "complexity": "low", "request_kind": "system", "confidence": "0.70", "route_hint": "deterministic_local", "semantic_status": "fallback_rule"}
    if _is_greeting(argument):
        return {"intent": "greeting", "complexity": "low", "request_kind": "standard", "confidence": "0.99", "route_hint": "deterministic_local", "semantic_status": "fallback_rule"}
    if len(argument.strip()) >= 180 or any(marker in lowered for marker in deep_reasoning_markers):
        return {"intent": "general_chat", "complexity": "medium", "request_kind": "deep", "confidence": "0.55", "route_hint": "model_desktop", "semantic_status": "fallback_rule"}
    return {"intent": "general_chat", "complexity": "low", "request_kind": "standard", "confidence": "0.50", "route_hint": "model_local", "semantic_status": "fallback_rule"}


def _chat_request_profile(
    argument: str,
    *,
    repo_root: Path | None = None,
    state: dict[str, Any] | None = None,
    store: OpenClawStore | None = None,
    chat_id: str = "",
) -> dict[str, str]:
    repo = repo_root or Path(__file__).resolve().parents[3]
    fallback = _chat_request_profile_fallback(argument)
    if not _should_use_semantic_profile(argument, fallback):
        fallback["semantic_status"] = "heuristic_only"
        return fallback

    message_hash = _normalized_message_hash(argument)
    cache_key = f"telegram:intent:{chat_id or 'global'}:{message_hash}"
    cached = store.get_cached_context(cache_key) if store else None
    if cached:
        cached_profile = dict(cached.get("profile") or {})
        if cached_profile:
            cached_profile["semantic_status"] = "cached"
            return cached_profile

    semantic = _semantic_chat_profile(argument, repo_root=repo, state=state)
    if semantic is None:
        fallback["semantic_status"] = "fallback_rule"
        return fallback
    if store is not None:
        store.cache_context(cache_key, {"profile": semantic})
    return semantic


_GREETING_PHRASES = {
    "buen dia",
    "buenas",
    "buenas tardes",
    "buenas noches",
    "buenos dias",
    "buenos dias",
    "buendia",
    "hello",
    "hey",
    "hi",
    "hola",
    "holi",
    "holis",
    "orale",
    "orale pues",
    "quiubo",
    "que onda",
    "que ondas",
    "que tal",
    "que transa",
    "que hubo",
    "que pedo",
    "saludos",
    "wena",
    "wenas",
    "buenas compa",
    "buenas compitas",
    "buenas mi gente",
    "que onda compa",
    "que onda compita",
    "que onda amigo",
    "que onda amiga",
    "que onda banda",
    "que onda raza",
    "que hubo compa",
    "que hubo banda",
    "que pedo compa",
    "que pedo banda",
    "que pedo wey",
    "que tranza",
}

def _normalize_greeting_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    stripped = re.sub(r"[^a-z0-9]+", " ", stripped)
    return re.sub(r"\s+", " ", stripped).strip()


def _is_greeting(argument: str) -> bool:
    normalized = _normalize_greeting_text(argument)
    if not normalized:
        return False
    if normalized in _GREETING_PHRASES:
        return True

    tokens = normalized.split()
    if len(tokens) > 4:
        return False

    prefixes = (
        "buen dia",
        "buenas",
        "buenas tardes",
        "buenas noches",
        "buenos dias",
        "hola",
        "holi",
        "holis",
        "hey",
        "hi",
        "orale",
        "quiubo",
        "que onda",
        "que ondas",
        "que tal",
        "que transa",
        "que hubo",
        "que pedo",
        "saludos",
        "wena",
        "wenas",
    )
    return any(normalized == prefix or normalized.startswith(f"{prefix} ") for prefix in prefixes)


def _deterministic_chat_response(
    argument: str,
    *,
    repo_root: Path,
    store: OpenClawStore,
    started_at: float,
    state: dict[str, Any] | None = None,
    profile: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    profile = profile or _chat_request_profile(argument, repo_root=repo_root)
    text = ""
    reason = ""
    intent = str(profile.get("intent", "")).strip().lower()
    if intent == "greeting":
        text = "Hola. OpenClaw Edge está listo; usa /estado, /modelos o dime la tarea concreta."
        reason = "greeting_sla"
    elif intent in {"system_status", "system_models", "system_routing"}:
        if intent == "system_models":
            text = "Modelos visibles:\n" + _models_text()
            reason = "system_models_readonly"
        elif intent == "system_routing":
            latency_response = _latency_question_response(argument, profile=profile)
            if latency_response is not None:
                text = latency_response["text"]
                reason = "latency_routing_readonly"
            else:
                text = _routing_text(argument, repo_root=repo_root, store=store)["text"]
                reason = "system_routing_readonly"
        else:
            status = _status_text(repo_root, store)
            text = "Resumen operativo breve:\n" + status
            reason = "runtime_status_readonly"
    elif intent == "time":
        text = _time_text()
        reason = "time_readonly"
    elif intent == "memory_summary":
        state = state or {}
        text = _memory_summary_text(state)
        reason = "memory_summary_readonly"

    if not text:
        return None

    task_id = f"TGM-DET-{uuid4().hex[:8]}"
    latency_ms = (time.perf_counter() - started_at) * 1000.0
    store.log_task_outcome(
        task_id=task_id,
        domain="academico",
        provider="deterministic_local",
        outcome="ok",
        request_kind=profile["request_kind"],
        complexity=profile["complexity"],
        latency_ms=latency_ms,
        error_text="",
        payload={
            "model": "deterministic",
            "provider_mode": "semantic_local",
            "trace_id": task_id,
            "request_kind": profile["request_kind"],
            "deadline_seconds": _chat_deadline_for(profile["request_kind"], profile["complexity"]),
            "prompt_chars": len(argument),
            "selected_backend": "semantic_local",
            "selected_label": reason,
            "semantic_intent": intent,
            "semantic_model": profile.get("semantic_model", ""),
            "semantic_status": profile.get("semantic_status", "semantic"),
            "fallback_policy": "not_required",
            "web_status": "skipped",
            "backend_errors": [],
            "candidate_models": [],
        },
    )
    return {"status": "ok", "text": text, "model": "deterministic"}


def _summary_request_response(argument: str, *, state: dict[str, Any]) -> dict[str, Any] | None:
    normalized = _normalize_greeting_text(argument)
    summary_markers = {
        "resumelo",
        "resume",
        "resumen",
        "sintetiza",
        "sintetizalo",
        "haz un resumen",
        "hazme un resumen",
        "resumen del chat",
    }
    if not normalized:
        return None
    if normalized in summary_markers or any(normalized.startswith(f"{marker} ") for marker in summary_markers):
        return {
            "status": "context_recalled",
            "text": _memory_summary_text(state),
        }
    return None


def _unit_conversion_response(argument: str) -> dict[str, Any] | None:
    normalized = _normalize_greeting_text(argument)
    if not normalized:
        return None
    match = re.search(
        r"(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<from>libras?|lbs?|lb|pounds?)\s*(?:a|en|to)\s*(?P<to>kg|kilos?|kilogramos?|kilogramos?)",
        normalized,
    )
    reverse = False
    if match is None:
        match = re.search(
            r"(?P<value>-?\d+(?:[.,]\d+)?)\s*(?P<from>kg|kilos?|kilogramos?|kilogramos?)\s*(?:a|en|to)\s*(?P<to>libras?|lbs?|lb|pounds?)",
            normalized,
        )
        reverse = match is not None
    if match is None:
        return None

    value = float(match.group("value").replace(",", "."))
    from_unit = match.group("from")
    if reverse:
        pounds = value / 0.45359237
        text = "\n".join(
            [
                "Conversión directa:",
                f"- {value:.2f} kg equivalen a {pounds:.2f} libras.",
                f"- Fórmula: {value:.2f} ÷ 0.45359237 = {pounds:.2f}",
                "- Redondeo: dos decimales.",
            ]
        )
        return {"status": "ok", "text": text}
    kilograms = value * 0.45359237
    text = "\n".join(
        [
            "Conversión directa:",
            f"- {value:.2f} {from_unit} equivalen a {kilograms:.2f} kg.",
            f"- Fórmula: {value:.2f} × 0.45359237 = {kilograms:.2f}",
            "- Redondeo: dos decimales.",
        ]
    )
    return {"status": "ok", "text": text}


def _provider_measured_candidates(repo_root: Path, provider_id: str, *, request_kind: str) -> list[str]:
    registry = load_provider_registry(repo_root)
    provider_meta = next((item for item in registry.get("providers", []) if str(item.get("id", "")) == provider_id), {})
    measured = dict(provider_meta.get("measured_candidates") or {})
    candidates: list[str] = []

    def append(name: Any) -> None:
        candidate = str(name or "").strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    if provider_id in {"desktop_compute", "pc_native_llamacpp"}:
        if request_kind == "coding":
            append(measured.get("coding_heavy"))
            append(measured.get("daily_recommended"))
            append(measured.get("alternative_ceiling"))
        elif request_kind == "deep":
            append(measured.get("experimental_ceiling"))
            append(measured.get("alternative_ceiling"))
            append(measured.get("daily_recommended"))
            append(measured.get("coding_heavy"))
        else:
            append(measured.get("daily_recommended"))
            append(measured.get("coding_heavy"))
            append(measured.get("alternative_ceiling"))
    elif provider_id == "ollama_local":
        if request_kind in {"coding", "deep", "knowledge"}:
            append(measured.get("experimental_ceiling"))
            append(measured.get("daily_recommended"))
        else:
            append(measured.get("daily_recommended"))
            append(measured.get("experimental_ceiling"))
        append(measured.get("fallback"))

    return candidates


def _desktop_provider_id() -> str:
    runtime = os.getenv("OPENCLAW_DESKTOP_RUNTIME", "").strip().lower()
    if runtime == "llamacpp":
        return "pc_native_llamacpp"
    return "desktop_compute"


def _desktop_runtime_base_url() -> str:
    return os.getenv(
        "OPENCLAW_DESKTOP_RUNTIME_BASE_URL",
        os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434"),
    ).strip() or "http://127.0.0.1:21434"


def _select_available_model(base_url: str, candidates: list[str], *, provider: str = "ollama_local") -> str:
    if provider == "pc_native_llamacpp":
        return candidates[0] if llamacpp_ready(base_url) and candidates else ""
    ok, models = list_ollama_models(base_url)
    if not ok:
        return ""
    available = set(models)
    loaded = list_loaded_ollama_models(base_url)
    for candidate in candidates:
        if candidate in available and candidate in loaded:
            return candidate
    for candidate in candidates:
        if candidate in available:
            return candidate
    return ""


def _explicit_chatgpt_requested(argument: str) -> bool:
    lowered = argument.lower()
    markers = (
        "chatgpt",
        "gpt-5",
        "gpt5",
        "modelo premium",
        "premium en la nube",
        "usa la nube",
        "usa nube",
        "usar nube",
        "usa openai",
        "usar openai",
    )
    return any(marker in lowered for marker in markers)


def _model_timeout_for(request_kind: str, complexity: str, *, backend: str) -> int:
    if request_kind == "standard" and complexity == "low":
        return _env_int("OPENCLAW_CHAT_SIMPLE_TIMEOUT", 25, minimum=5, maximum=90)
    if request_kind == "knowledge":
        return _env_int("OPENCLAW_CHAT_FACTUAL_TIMEOUT", 90, minimum=10, maximum=180)
    if request_kind in {"coding", "deep", "reasoning", "system"}:
        default = 120 if backend in {"desktop_compute", "pc_native_llamacpp"} else 90
        return _env_int("OPENCLAW_CHAT_HEAVY_TIMEOUT", default, minimum=10, maximum=300)
    return _env_int("OPENCLAW_CHAT_MEDIUM_TIMEOUT", 40, minimum=10, maximum=120)


def _chat_deadline_for(request_kind: str, complexity: str) -> int:
    if request_kind == "standard" and complexity == "low":
        return _env_int("OPENCLAW_CHAT_SIMPLE_TIMEOUT", 25, minimum=5, maximum=90)
    if request_kind == "knowledge":
        return _env_int("OPENCLAW_CHAT_FACTUAL_TIMEOUT", 90, minimum=10, maximum=180)
    return _env_int("OPENCLAW_CHAT_HEAVY_TIMEOUT", 90, minimum=10, maximum=300)


def _dedupe_candidates(items: list[ChatBackendCandidate]) -> list[ChatBackendCandidate]:
    seen: set[tuple[str, str, str]] = set()
    output: list[ChatBackendCandidate] = []
    for item in items:
        key = (item.provider, item.base_url, item.model)
        if item.model and key not in seen:
            seen.add(key)
            output.append(item)
    return output


def _chat_backend_candidates(repo_root: Path, profile: dict[str, str]) -> list[ChatBackendCandidate]:
    request_kind = profile["request_kind"]
    complexity = profile["complexity"]
    edge_base = os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    desktop_base = _desktop_runtime_base_url()
    desktop_provider = _desktop_provider_id()
    desktop_enabled = _env_flag("OPENCLAW_DESKTOP_COMPUTE_ENABLED", default=True)
    edge_timeout = _model_timeout_for(request_kind, complexity, backend="ollama_local")
    desktop_timeout = _model_timeout_for(request_kind, complexity, backend=desktop_provider)

    edge_candidates = _provider_measured_candidates(repo_root, "ollama_local", request_kind=request_kind)
    for stable_model in (os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b"), "gemma3:4b", "qwen3:4b"):
        if stable_model and stable_model not in edge_candidates:
            edge_candidates.append(stable_model)
    edge_candidates = [item for item in edge_candidates if item and not item.startswith("qwen2.5:0.5b")]
    if request_kind in {"standard", "knowledge", "reasoning"}:
        stable_edge = []
        for model in (os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b"), "gemma3:4b", "qwen3:4b"):
            if model and model not in stable_edge:
                stable_edge.append(model)
        edge_candidates = [item for item in stable_edge if item in edge_candidates or item]
    elif request_kind != "coding":
        edge_candidates = [item for item in edge_candidates if "coder" not in item]

    desktop_candidates: list[str] = []
    if desktop_enabled:
        desktop_candidates = _provider_measured_candidates(repo_root, desktop_provider, request_kind=request_kind)
        for stable_model in (
            os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", os.getenv("OPENCLAW_DESKTOP_COMPUTE_MODEL", "mistral-nemo:12b")),
            "mistral-nemo:12b",
            "qwen2.5-coder:14b",
            "phi4:14b",
        ):
            if stable_model and stable_model not in desktop_candidates:
                desktop_candidates.append(stable_model)

    candidates: list[ChatBackendCandidate] = []
    if request_kind == "standard" and complexity == "low":
        for model in edge_candidates:
            candidates.append(ChatBackendCandidate("ollama_local", edge_base, model, edge_timeout, "edge_fast"))
        for model in desktop_candidates[:2]:
            candidates.append(ChatBackendCandidate(desktop_provider, desktop_base, model, desktop_timeout, "desktop_warm"))
    elif request_kind == "knowledge":
        for model in edge_candidates:
            candidates.append(ChatBackendCandidate("ollama_local", edge_base, model, edge_timeout, "edge_factual"))
        for model in desktop_candidates[:2]:
            candidates.append(ChatBackendCandidate(desktop_provider, desktop_base, model, desktop_timeout, "desktop_factual"))
    else:
        for model in desktop_candidates:
            candidates.append(ChatBackendCandidate(desktop_provider, desktop_base, model, desktop_timeout, "desktop_heavy"))
        for model in edge_candidates:
            candidates.append(ChatBackendCandidate("ollama_local", edge_base, model, edge_timeout, "edge_degraded"))
    return _dedupe_candidates(candidates)


def _build_chat_execution_plan(*, repo_root: Path, argument: str, profile: dict[str, str], decision_provider: str) -> ChatExecutionPlan:
    explicit_web = _explicit_chatgpt_requested(argument)
    use_web = explicit_web and decision_provider == "chatgpt_plus_web_assisted"
    request_kind = profile["request_kind"]
    complexity = profile["complexity"]
    return ChatExecutionPlan(
        trace_id=f"CHAT-{uuid4().hex[:10]}",
        request_kind=request_kind,
        complexity=complexity,
        deadline_seconds=_chat_deadline_for(request_kind, complexity),
        use_web_assisted=use_web,
        web_timeout_seconds=_env_int("OPENCLAW_CHAT_WEB_TIMEOUT", 30, minimum=5, maximum=120),
        api_timeout_seconds=_env_int("OPENCLAW_CHAT_API_TIMEOUT", 25, minimum=5, maximum=120),
        candidates=_chat_backend_candidates(repo_root, profile),
        fallback_policy="semantic_fallback_edge_recommended",
    )


def _backend_semaphore(candidate: ChatBackendCandidate) -> threading.BoundedSemaphore:
    return _DESKTOP_SEMAPHORE if candidate.provider in {"desktop_compute", "pc_native_llamacpp"} else _EDGE_SEMAPHORE


def _openai_chat_generate(prompt: str, *, timeout_seconds: int = 120) -> tuple[bool, str, str]:
    provider = os.getenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "openai").strip().lower()
    if provider != "openai":
        return False, f"chat_provider_not_supported:{provider}", ""

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return False, "openai_api_key_missing", ""

    model = os.getenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4").strip() or "gpt-5.4"
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = request.Request("https://api.openai.com/v1/chat/completions", data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {api_key}")
    req.add_header("Content-Type", "application/json")

    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        return False, f"openai_chat_http_error:{detail[:300]}", model
    except (error.URLError, json.JSONDecodeError) as exc:
        return False, f"openai_chat_error:{exc}", model

    choices = payload.get("choices") or []
    if not choices:
        return False, "openai_chat_empty_choices", model

    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = str(message.get("content", "")).strip()
    if not content:
        return False, "openai_chat_empty_text", model

    return True, content, model


def _chat_session_generate(prompt: str, *, timeout_seconds: int = 180) -> tuple[bool, str, str]:
    provider = os.getenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session").strip().lower()
    if provider in {"web_session", "chatgpt_web_session", "chatgpt_plus_web_session"}:
        ok, response, model = generate_web_session_response(prompt, timeout_seconds=timeout_seconds)
        if ok:
            return ok, response, model or os.getenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4").strip() or "gpt-5.4"
        return ok, response, model
    if provider == "openai":
        return _openai_chat_generate(prompt, timeout_seconds=timeout_seconds)
    return False, f"chat_provider_not_supported:{provider}", ""


def _select_chat_runtime(repo_root: Path, argument: str) -> tuple[str, str]:
    profile = _chat_request_profile(argument, repo_root=repo_root)
    for candidate in _chat_backend_candidates(repo_root, profile):
        selected = _select_available_model(candidate.base_url, [candidate.model], provider=candidate.provider)
        if selected:
            return candidate.base_url, selected
    return os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434"), os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")


def _select_research_runtime(repo_root: Path, argument: str) -> tuple[str, str]:
    lowered = argument.lower()
    coding_markers = (
        "bug",
        "código",
        "codigo",
        "error",
        "errores",
        "fix",
        "patch",
        "python",
        "script",
        "sql",
        "stack trace",
        "traceback",
        "test",
        "tests",
        "terminal",
        "refactor",
        "yaml",
        "json",
        "docker",
        "bash",
        "powershell",
    )
    deep_markers = (
        "analiza",
        "corrige",
        "detalla",
        "diagnostica",
        "explica",
        "justifica",
        "más a fondo",
        "mas a fondo",
        "piénsalo",
        "piensalo",
        "profundiza",
        "razona",
        "revisa",
    )
    request_kind = "coding" if any(marker in lowered for marker in coding_markers) else "deep" if any(marker in lowered for marker in deep_markers) or len(argument.strip()) >= 260 else "standard"
    desktop_base = _desktop_runtime_base_url()
    desktop_provider = _desktop_provider_id()
    edge_base = os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    desktop_enabled = os.getenv("OPENCLAW_DESKTOP_COMPUTE_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
    desktop_candidates: list[str] = []
    if desktop_enabled:
        desktop_request_kind = request_kind if request_kind != "standard" else ""
        desktop_candidates = _provider_measured_candidates(repo_root, desktop_provider, request_kind=desktop_request_kind)
    edge_candidates = _provider_measured_candidates(repo_root, "ollama_local", request_kind=request_kind)
    if request_kind == "knowledge" and desktop_enabled:
        model = _select_available_model(desktop_base, desktop_candidates, provider=desktop_provider)
        if model:
            return desktop_base, model
        model = _select_available_model(edge_base, edge_candidates, provider="ollama_local")
        if model:
            return edge_base, model
    else:
        if desktop_enabled:
            model = _select_available_model(desktop_base, desktop_candidates, provider=desktop_provider)
            if model:
                return desktop_base, model
        model = _select_available_model(edge_base, edge_candidates, provider="ollama_local")
        if model:
            return edge_base, model
    fallback_model = os.getenv("OPENCLAW_TELEGRAM_FALLBACK_MODEL", os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")).strip() or "qwen3:4b"
    if fallback_model.startswith("qwen2.5:0.5b"):
        fallback_model = "qwen3:4b"
    return edge_base, fallback_model


def handle_update(update: dict[str, Any], *, repo_root: Path, store: OpenClawStore) -> dict[str, Any]:
    up_id = int(update.get("update_id", 0))
    message = update.get("message") or update.get("callback_query", {}).get("message") or {}
    chat_id = str(message.get("chat", {}).get("id", ""))
    text = str(message.get("text", "")).strip()
    command, argument = parse_command(text)
    
    state = store.get_cached_context(f"telegram:state:{chat_id}") or {}
    has_voice = bool(message.get("voice") or message.get("audio"))
    if has_voice and not text:
        command = "voz"
        argument = ""

    print(f"[DEBUG] [Update {up_id}] Checking authorization for {chat_id}...", flush=True)
    authorized = is_authorized_chat(chat_id)
    print(f"[DEBUG] [Update {up_id}] Authorized: {authorized}", flush=True)
    payload = {
        "event_id": f"TGM-{uuid4().hex[:12]}",
        "update_id": up_id,
        "chat_id": chat_id,
        "command": command,
        "authorized": authorized,
        "text": redact_text(text),
    }
    if not authorized:
        print(f"[DEBUG] [Update {up_id}] Unauthorized chat {chat_id}.", flush=True)
        store.save_telegram_event(status="ignored_unauthorized", payload=payload, **_event_keys(payload))
        return {"status": "ignored", "reason": "unauthorized", "reply_sent": False}

    voice_enabled = os.getenv("OPENCLAW_TELEGRAM_VOICE_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
    if command == "voz":
        if not voice_enabled:
            response = {"status": "skipped", "text": "El procesamiento de voz está temporalmente desactivado. 🔇"}
        else:
            send_chat_action(chat_id)
            response = _voice_response(message=message, repo_root=repo_root, store=store, chat_id=chat_id)
    else:
        print(f"[DEBUG] [Update {up_id}] Dispatching command '{command}'...", flush=True)
        session_result = process_channel_text(
            store=store,
            repo_root=repo_root,
            channel="telegram",
            peer_id=chat_id,
            text=text,
            dispatcher=lambda resolved_command, resolved_argument: dispatch_command(
                resolved_command,
                resolved_argument,
                repo_root=repo_root,
                store=store,
                chat_id=chat_id,
            ),
            operator_identity=f"telegram:{chat_id}",
        )
        response = dict(session_result["response"])
        response["session_id"] = session_result["session"]["session_id"]
        print(f"[DEBUG] [Update {up_id}] Command dispatched. Response length: {len(str(response.get('text', '')))}", flush=True)

    payload["response"] = redact_text(response.get("text", ""))
    store.save_telegram_event(status=response.get("status", "error"), payload=payload, **_event_keys(payload))

    sent_voice: dict[str, Any] | None = None
    voice_path = str(response.get("audio_path", "")).strip()
    if voice_path:
        sent_voice = send_voice_message(chat_id, Path(voice_path), caption=response.get("audio_caption", ""))

    sent_photo: dict[str, Any] | None = None
    image_path = str(response.get("image_path", "")).strip()
    if image_path:
        sent_photo = send_photo_message(chat_id, Path(image_path), caption=response.get("image_caption", ""))

    send_text_ack = os.getenv("OPENCLAW_TELEGRAM_VOICE_SEND_TEXT_ACK", "0").strip().lower() in {"1", "true", "yes", "on"}
    if sent_voice and sent_voice.get("status") == "sent" and not send_text_ack:
        return {
            **response,
            "telegram": {"voice": sent_voice, "photo": sent_photo},
            "reply_sent": True,
        }

    print(f"[DEBUG] [Update {up_id}] Sending final text response...", flush=True)
    model_name = response.get('model') or "sin_modelo"
    status_emoji = "🟢" if response.get("status") == "ok" else "🟡"
    
    # Única fuente de verdad para el encabezado estético
    header = f"<b>{status_emoji} [{model_name}]</b> ➸ " if model_name else "➸ "
    
    # Escapar SOLO el contenido de la respuesta, no el encabezado
    raw_content = response.get('text', '')
    safe_content = raw_content.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    
    final_text = f"{header}{safe_content}"
    sent_text = send_message(chat_id, final_text)
    
    status = "delivered" if sent_text.get("status") == "sent" else "delivery_failed"
    print(f"[DEBUG] [Update {up_id}] Sent text status: {sent_text.get('status')} -> {status}", flush=True)
    
    # Actualizar evento con estado de entrega
    payload["sent_text_result"] = sent_text
    store.save_telegram_event(status=status, payload=payload, **_event_keys(payload))

    reply_sent = sent_text.get("status") == "sent" or bool(sent_voice and sent_voice.get("status") == "sent") or bool(sent_photo and sent_photo.get("status") == "sent")
    return {
        **response,
        "telegram": {"text": sent_text, "voice": sent_voice, "photo": sent_photo},
        "reply_sent": reply_sent,
    }


def dispatch_command(
    command: str,
    argument: str,
    *,
    repo_root: Path,
    store: OpenClawStore,
    chat_id: str = "cli",
) -> dict[str, Any]:
    state = _load_chat_state(store, chat_id)
    send_chat_action(chat_id)
    if command in {"start", "help", "ayuda"}:
        response = {"status": "ok", "text": _help_text()}
    elif command == "estado":
        response = {"status": "ok", "text": _status_text(repo_root, store)}
    elif command == "modelos":
        response = _routing_text(argument, repo_root=repo_root, store=store) if argument.strip() else {"status": "ok", "text": _models_text()}
    elif command == "hora":
        response = {"status": "ok", "text": _time_text()}
    elif command == "memoria":
        response = {"status": "ok", "text": _memory_summary_text(state)}
    elif command == "llamada":
        response = _call_mode_response(argument, state=state)
    elif command == "aprender":
        response = _learn_response(argument, state=state)
    elif command == "olvidar":
        response = _forget_response(argument, chat_id=chat_id, store=store)
    elif command == "chat":
        response = _chat_response(argument or "Hola", repo_root=repo_root, store=store, chat_id=chat_id, state=state)
    elif command == "investiga":
        response = _research_response(_resolve_research_argument(argument, state), repo_root=repo_root, store=store, chat_id=chat_id, state=state)
    elif command == "herramienta":
        response = _tool_response(argument, repo_root=repo_root, store=store, state=state, chat_id=chat_id)
    elif command in {"modelo", "model"}:
        response = _routing_text(argument, repo_root=repo_root, store=store)
    elif command == "aprobar":
        response = _approval_response(argument, repo_root=repo_root, store=store, state=state, chat_id=chat_id)
    else:
        response = {"status": "unknown_command", "text": f"Comando no reconocido: /{command}\nUsa /ayuda."}
    if response.get("skip_memory_update"):
        response = {key: value for key, value in response.items() if key != "skip_memory_update"}
    else:
        _remember_turn(store, chat_id=chat_id, command=command, user_text=argument, response=response, state_override=state)
    return response


_executor = ThreadPoolExecutor(max_workers=_env_int("OPENCLAW_TELEGRAM_MAX_WORKERS", 2, minimum=1, maximum=8))


def _process_update_safe(update: dict[str, Any], repo_root: Path, store: OpenClawStore) -> None:
    up_id = int(update.get("update_id", 0))
    message = update.get("message") or update.get("callback_query", {}).get("message") or {}
    chat_id = str(message.get("chat", {}).get("id", ""))
    print(f"[DEBUG] [Thread] Starting processing for update {up_id}...", flush=True)
    try:
        with _chat_lock(chat_id):
            handle_update(update, repo_root=repo_root, store=store)
        print(f"[DEBUG] [Thread] Finished processing update {up_id}.", flush=True)
    except Exception as exc:
        # Estética de error: Flechita roja y negrita
        error_msg = f"<b>🔴 [ERROR]</b> ➸ Error interno {up_id}: <i>{exc}</i>"
        print(f"[DEBUG] {error_msg}", flush=True)
        if chat_id:
            try:
                send_message(chat_id, f"{error_msg}\n\nPor favor, intenta de nuevo o contacta al administrador. 🛠️")
            except Exception:
                pass
        store.save_telegram_event(
            event_id=f"ERR-{up_id}",
            update_id=up_id,
            chat_id=chat_id or "unknown",
            command="error",
            authorized=False,
            status="unhandled_exception",
            payload={"error": str(exc)},
        )


def poll_once(*, repo_root: Path, store: OpenClawStore, timeout_seconds: int = 20, limit: int = 10) -> dict[str, Any]:
    cached = store.get_cached_context("telegram:last_update_id") or {}
    last_update_id = int(cached.get("value", 0) or 0)
    print(f"[DEBUG] Fetching updates from offset {last_update_id + 1 if last_update_id else 'None'}...", flush=True)
    updates = get_updates(offset=last_update_id + 1 if last_update_id else None, timeout_seconds=timeout_seconds, limit=limit)
    print(f"[DEBUG] Fetched {len(updates)} updates.", flush=True)
    if updates:
        max_id = max(int(u.get("update_id", 0)) for u in updates)
        print(f"[DEBUG] Advancing last_update_id to {max_id}", flush=True)
        store.cache_context("telegram:last_update_id", {"value": max_id})
    
    for update in updates:
        _executor.submit(_process_update_safe, update, repo_root, store)
    return {"status": "ok", "updates": len(updates)}


def run_polling_loop(*, repo_root: Path, store: OpenClawStore, interval_seconds: int = 2, timeout_seconds: int = 20) -> None:
    print(f"[DEBUG] Starting polling loop (interval={interval_seconds}s, timeout={timeout_seconds}s)", flush=True)
    warmup = warmup_chat_models(repo_root)
    print(f"[DEBUG] Warmup chat models: {warmup}", flush=True)
    while True:
        try:
            poll_once(repo_root=repo_root, store=store, timeout_seconds=timeout_seconds)
        except Exception as exc:
            print(f"[DEBUG] Loop error: {exc}", flush=True)
        time.sleep(max(0.1, interval_seconds))


def _event_keys(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(payload["event_id"]),
        "update_id": int(payload["update_id"]),
        "chat_id": str(payload["chat_id"]),
        "command": str(payload["command"]),
        "authorized": bool(payload["authorized"]),
    }


def _help_text() -> str:
    return "\n".join(
        [
            "OpenClaw Edge listo.",
            "Comandos:",
            "/estado - salud del gateway, DB y runtime",
            "/modelos - modelos edge y desktop visibles",
            "/hora - fecha y hora con CENAM/NTP o reloj local",
            "/memoria - resumen de contexto y aprendizajes del chat",
            "/llamada [on|off] [estable|rapida] - activa modo llamada simulada por turnos",
            "/aprender <preferencia> - guardar preferencia o ajuste revisable",
            "/olvidar [todo|preferencias|turnos] - limpiar memoria del chat",
            "Mensajes de voz: transcribe, enruta y responde con audio cuando hay STT/TTS configurado.",
            "/chat <texto> - chat ligero local",
            "/investiga <pregunta> - investigación web read-only con routing",
            "/herramienta <accion> - solo herramientas read-only; mutaciones generan aprobación",
            "/aprobar <id> - reservado para fase posterior",
        ]
    )


def _status_text(repo_root: Path, store: OpenClawStore) -> str:
    runtime = probe_runtime_status(repo_root)
    summary = store.audit_summary()
    latest_trace = store.list_request_traces(limit=1)
    latest_fallback_reason = "none"
    latest_model = "none"
    latest_provider = "none"
    latest_backend_busy = "none"
    latest_backend_busy_count = 0
    if latest_trace:
        trace = latest_trace[0]
        latest_fallback_reason = str(trace.get("fallback_reason", "")).strip() or "none"
        latest_model = str(trace.get("selected_model", "")).strip() or "none"
        latest_provider = str(trace.get("selected_provider", "")).strip() or "none"
        payload = trace.get("payload") if isinstance(trace, dict) else {}
        backend_errors = list((payload or {}).get("backend_errors") or []) if isinstance(payload, dict) else []
        busy_errors = [item for item in backend_errors if str(item.get("error", "")).strip() == "backend_busy"]
        latest_backend_busy_count = len(busy_errors)
        if busy_errors:
            last_busy = busy_errors[-1]
            busy_provider = str(last_busy.get("provider", "")).strip() or "none"
            busy_model = str(last_busy.get("model", "")).strip() or "none"
            latest_backend_busy = f"{busy_provider}:{busy_model}"
    desktop_provider = _desktop_provider_id()
    desktop_base = _desktop_runtime_base_url()
    desktop_model = os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", os.getenv("OPENCLAW_DESKTOP_COMPUTE_MODEL", "mistral-nemo:12b")).strip() or "mistral-nemo:12b"
    desktop_ok = llamacpp_ready(desktop_base) if desktop_provider == "pc_native_llamacpp" else list_ollama_models(desktop_base)[0]
    chat_provider = os.getenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session").strip().lower()
    chat_model = os.getenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4").strip() or "gpt-5.4"
    return "\n".join(
        [
            "Estado OpenClaw:",
            f"runtime={runtime.get('active_runtime')} state={runtime.get('state')}",
            f"chat_provider={chat_provider} chat_model={chat_model}",
            f"db={summary.get('db_path')}",
            f"tasks={summary.get('tasks')} approvals={summary.get('pending_approvals')} telegram_events={summary.get('telegram_events')}",
            f"sessions={summary.get('sessions', 0)} session_messages={summary.get('session_messages', 0)}",
            f"request_traces={summary.get('request_traces')} last_fallback_reason={latest_fallback_reason} last_trace_provider={latest_provider} last_trace_model={latest_model}",
            f"last_backend_busy={latest_backend_busy} count={latest_backend_busy_count}",
            f"{desktop_provider}={'ok' if desktop_ok else 'degradado'} model={desktop_model}",
            f"preflight={build_preflight_report(repo_root).get('status')}",
        ]
    )


def _models_text() -> str:
    edge_ok, edge_models = list_ollama_models(os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
    desktop_provider = _desktop_provider_id()
    desktop_base = _desktop_runtime_base_url()
    if desktop_provider == "pc_native_llamacpp":
        desktop_ok = llamacpp_ready(desktop_base)
        desktop_models = [os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", os.getenv("OPENCLAW_DESKTOP_COMPUTE_MODEL", "mistral-nemo:12b")).strip() or "mistral-nemo:12b"]
    else:
        desktop_ok, desktop_models = list_ollama_models(desktop_base)
    return "\n".join(
        [
            "Modelos OpenClaw:",
            f"edge={'ok' if edge_ok else 'no_disponible'}: {', '.join(edge_models[:8]) or 'sin modelos'}",
            f"desktop={'ok' if desktop_ok else 'no_disponible'}: {', '.join(desktop_models[:8]) or 'sin modelos'}",
        ]
    )


def _save_request_trace(
    *,
    store: OpenClawStore,
    trace_id: str,
    task_id: str,
    channel: str,
    command: str,
    request_kind: str,
    complexity: str,
    selected_provider: str,
    selected_model: str,
    fallback_reason: str,
    stage_ms: dict[str, float | None],
    prompt: str,
    payload: dict[str, Any] | None = None,
) -> None:
    trace = RequestTrace(
        trace_id=trace_id,
        task_id=task_id,
        channel=channel,
        command=command,
        request_kind=request_kind,
        complexity=complexity,
        selected_provider=selected_provider,
        selected_model=selected_model,
        fallback_reason=fallback_reason,
        parse_ms=stage_ms.get("parse_ms"),
        profile_ms=stage_ms.get("profile_ms"),
        semantic_ms=stage_ms.get("semantic_ms"),
        routing_ms=stage_ms.get("routing_ms"),
        web_search_ms=stage_ms.get("web_search_ms"),
        provider_ms=stage_ms.get("provider_ms"),
        delivery_ms=stage_ms.get("delivery_ms"),
        total_ms=stage_ms.get("total_ms"),
        prompt_chars=len(prompt),
        prompt_tokens_est=_token_estimate(prompt),
        payload=payload or {},
        created_at=datetime.now(UTC).isoformat(),
    )
    store.save_request_trace(trace)


def _chat_response(
    argument: str,
    *,
    repo_root: Path,
    store: OpenClawStore,
    chat_id: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    started_at = time.perf_counter()
    stage_ms: dict[str, float | None] = {
        "parse_ms": 0.0,
        "profile_ms": None,
        "semantic_ms": None,
        "routing_ms": None,
        "web_search_ms": None,
        "provider_ms": None,
        "delivery_ms": None,
        "total_ms": None,
    }
    approval = _approval_response_if_confirmation(argument, repo_root=repo_root, store=store, state=state, chat_id=chat_id)
    if approval is not None:
        return approval
    natural = _natural_command_response(argument, repo_root=repo_root, store=store, state=state)
    if natural is not None:
        return natural
    explicit_chatgpt = _explicit_chatgpt_requested(argument)
    if explicit_chatgpt:
        profile = _chat_request_profile_fallback(argument)
    else:
        profile_started = time.perf_counter()
        profile = _chat_request_profile(argument, repo_root=repo_root, state=state, store=store, chat_id=chat_id)
        stage_ms["profile_ms"] = _elapsed_ms(profile_started)
        semantic_ms = profile.get("semantic_ms")
        if semantic_ms:
            try:
                stage_ms["semantic_ms"] = float(semantic_ms)
            except ValueError:
                stage_ms["semantic_ms"] = None
        deterministic = _deterministic_chat_response(argument, repo_root=repo_root, store=store, started_at=started_at, state=state, profile=profile)
        if deterministic is not None:
            return deterministic
    if _asks_for_previous_scan_result(argument, state):
        approval = state.get("last_approval") or {}
        approval_id = approval.get("approval_id", "sin_apr")
        draft = approval.get("draft_command", "sin borrador registrado")
        intent = approval.get("intent", "acción pendiente")
        return {
            "status": "context_recalled",
            "text": "\n".join(
                [
                    "Resultado del escaneo: no se ejecutó ningún escaneo desde Telegram.",
                    f"Propuesta pendiente: {approval_id}",
                    f"Intención: {intent}",
                    f"Borrador no ejecutado: {draft}",
                ]
            ),
        }
    if _asks_memory_summary(argument):
        return {"status": "context_recalled", "text": _memory_summary_text(state)}
    if _is_learning_request(argument):
        return _learn_response(argument, state=state, auto_proposal=True)
    if _asks_command_examples(argument, state):
        return {"status": "ok", "text": _command_examples_text(argument, state)}
    if _is_model_request(argument):
        return _routing_text(argument, repo_root=repo_root, store=store)
    if _is_ambiguous_action(argument):
        return _approval_proposal(argument, repo_root=repo_root, store=store, source_command="chat", chat_id=chat_id)
    send_chat_action(chat_id)

    task = TaskEnvelope(
        task_id=f"TGM-CHAT-{uuid4().hex[:8]}",
        title="Chat Telegram",
        domain="academico",
        objective=argument,
        complexity=profile["complexity"],
        risk_level="low",
        extra_context={
            "telegram_command": "chat",
            "chat_id": chat_id,
            "request_profile": profile["request_kind"],
            "task_type": "generacion_extensa" if profile["complexity"] == "high" else "",
            "desktop_compute": profile["complexity"] == "high",
            "prefer_chatgpt_plus": explicit_chatgpt,
            "preferred_web_assisted": "chatgpt_plus_web_assisted" if explicit_chatgpt else "",
        },
    )
    routing_started = time.perf_counter()
    decision = route_task(task, load_domain_policies(repo_root), repo_root=repo_root, store=store)
    stage_ms["routing_ms"] = _elapsed_ms(routing_started)
    store.save_task(task, decision)

    plan = _build_chat_execution_plan(repo_root=repo_root, argument=argument, profile=profile, decision_provider=decision.provider)
    ok = False
    response = ""
    model_name = ""
    last_attempted_model = ""
    backend_errors: list[dict[str, Any]] = []
    selected_candidate: ChatBackendCandidate | None = None
    web_status = "skipped"

    with TypingHeartbeat(chat_id):
        web_evidence = None
        if profile["request_kind"] == "knowledge":
            web_started = time.perf_counter()
            send_message(chat_id, "<i>🔍 Buscando evidencia externa relevante...</i>")
            web_result = web_search(argument, limit=3)
            stage_ms["web_search_ms"] = _elapsed_ms(web_started)
            if web_result.get("status") == "ok":
                web_evidence = web_result
                send_message(chat_id, f"<i>✅ Evidencia encontrada ({len(web_result.get('results', []))} fuentes). Integrando al contexto...</i>")
            else:
                send_message(chat_id, f"<i>⚠️ Búsqueda limitada: {web_result.get('error', 'sin resultados')}. Usando conocimiento base.</i>")

        prompt = _safe_prompt(argument, state=state, web=web_evidence, profile=profile)

        if plan.use_web_assisted:
            send_message(chat_id, "<i>☁️ Consultando modelo premium solicitado explícitamente...</i>")
            provider_started = time.perf_counter()
            ok, response, model_name = _chat_session_generate(prompt, timeout_seconds=plan.web_timeout_seconds)
            stage_ms["provider_ms"] = _elapsed_ms(provider_started)
            web_status = "ok" if ok else response
            if not ok:
                web_model = model_name or os.getenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4").strip() or "gpt-5.4"
                send_message(chat_id, f"<i>⚠️ Fallo en sesión web ({decision.provider}/{web_model}). Intentando API directa breve...</i>")
                provider_started = time.perf_counter()
                ok, response, model_name = _openai_chat_generate(prompt, timeout_seconds=plan.api_timeout_seconds)
                stage_ms["provider_ms"] = _elapsed_ms(provider_started)
                web_status = "api_ok" if ok else f"{web_status}|api:{response}"

        deadline_at = started_at + plan.deadline_seconds
        for candidate in plan.candidates:
            if ok:
                break
            remaining = deadline_at - time.perf_counter()
            if remaining <= 0:
                backend_errors.append({"provider": candidate.provider, "model": candidate.model, "error": "deadline_exceeded_before_attempt"})
                break
            timeout_seconds = max(3, min(candidate.timeout_seconds, int(remaining)))
            if not _select_available_model(candidate.base_url, [candidate.model], provider=candidate.provider):
                backend_errors.append({"provider": candidate.provider, "model": candidate.model, "error": "model_not_available", "base_url": candidate.base_url})
                continue
            print(
                f"[DEBUG] Ruteo chat plan={plan.trace_id} provider={candidate.provider} "
                f"base_url={candidate.base_url} model={candidate.model} timeout={timeout_seconds}",
                flush=True,
            )
            send_message(chat_id, f"<i>🧠 Consultando {candidate.label}: {candidate.model}...</i>")
            backend_semaphore = _backend_semaphore(candidate)
            if not backend_semaphore.acquire(blocking=False):
                backend_errors.append(
                    {
                        "provider": candidate.provider,
                        "model": candidate.model,
                        "base_url": candidate.base_url,
                        "timeout_seconds": timeout_seconds,
                        "error": "backend_busy",
                    }
                )
                continue
            last_attempted_model = candidate.model
            attempt_started = time.perf_counter()
            try:
                if candidate.provider == "pc_native_llamacpp":
                    ok, response = llamacpp_generate(
                        base_url=candidate.base_url,
                        model=candidate.model,
                        prompt=prompt,
                        timeout_seconds=timeout_seconds,
                    )
                else:
                    ok, response = ollama_generate(
                        base_url=candidate.base_url,
                        model=candidate.model,
                        prompt=prompt,
                        timeout_seconds=timeout_seconds,
                    )
            finally:
                backend_semaphore.release()
            latency_ms = (time.perf_counter() - attempt_started) * 1000.0
            stage_ms["provider_ms"] = round((stage_ms["provider_ms"] or 0.0) + latency_ms, 3)
            if ok and response.strip():
                model_name = candidate.model
                selected_candidate = candidate
                break
            backend_errors.append(
                {
                    "provider": candidate.provider,
                    "model": candidate.model,
                    "base_url": candidate.base_url,
                    "timeout_seconds": timeout_seconds,
                    "latency_ms": round(latency_ms, 3),
                    "error": response or "empty_response",
                }
            )

        if not ok:
            response = (
                "Sistemas de inferencia saturados o fuera de SLA. "
                "No se pudo obtener respuesta con el borde recomendado; reintenta en unos segundos o pide /modelos para diagnóstico."
            )

        if profile["request_kind"] == "knowledge" and web_evidence and web_evidence.get("status") == "ok":
            if not ok or not _web_evidence_supports_response(response, web_evidence, argument):
                response = _knowledge_web_fallback_text(argument, web_evidence)
                model_name = f"{model_name or last_attempted_model or 'sin_modelo'}+evidencia_web"
                ok = True

    response_payload = {
        "status": "ok" if ok else "model_error",
        "text": response,
        "model": model_name,
    }
    stage_ms["total_ms"] = _elapsed_ms(started_at)
    store.log_task_outcome(
        task_id=task.task_id,
        domain=task.domain,
        provider=selected_candidate.provider if selected_candidate else decision.provider,
        outcome=str(response_payload["status"]),
        request_kind=str(task.extra_context.get("request_profile", "standard")),
        complexity=str(task.complexity),
        latency_ms=(time.perf_counter() - started_at) * 1000.0,
        error_text="" if ok else str(response or "model_error"),
        payload={
            "model": model_name,
            "provider_mode": decision.mode,
            "decision_provider": decision.provider,
            "trace_id": plan.trace_id,
            "request_kind": plan.request_kind,
            "deadline_seconds": plan.deadline_seconds,
            "prompt_chars": len(prompt),
            "selected_backend": selected_candidate.provider if selected_candidate else "",
            "selected_label": selected_candidate.label if selected_candidate else "",
            "fallback_policy": plan.fallback_policy,
            "web_status": web_status,
            "backend_errors": backend_errors,
            "candidate_models": [f"{item.provider}:{item.model}" for item in plan.candidates],
            "metrics": stage_ms,
            "selected_provider": selected_candidate.provider if selected_candidate else decision.provider,
            "selected_model": model_name,
            "fallback_reason": "" if ok else "all_candidates_failed",
            "semantic_status": profile.get("semantic_status", ""),
        },
    )
    _save_request_trace(
        store=store,
        trace_id=plan.trace_id,
        task_id=task.task_id,
        channel="telegram",
        command="chat",
        request_kind=plan.request_kind,
        complexity=plan.complexity,
        selected_provider=selected_candidate.provider if selected_candidate else decision.provider,
        selected_model=model_name or "",
        fallback_reason="" if ok else "all_candidates_failed",
        stage_ms=stage_ms,
        prompt=prompt,
        payload={
            "web_status": web_status,
            "semantic_status": profile.get("semantic_status", ""),
            "backend_errors": backend_errors,
        },
    )
    return response_payload


def _voice_response(
    *,
    message: dict[str, Any],
    repo_root: Path,
    store: OpenClawStore,
    chat_id: str,
) -> dict[str, Any]:
    state = _load_chat_state(store, chat_id)
    call_mode = dict(state.get("call_mode") or {"enabled": False, "style": "estable"})
    if _voice_requires_call_mode() and not call_mode.get("enabled"):
        response = {
            "status": "call_mode_required",
            "text": "Modo llamada desactivado. Usa /llamada on [estable|rapida] para habilitar voz por turnos.",
        }
        _remember_turn(store, chat_id=chat_id, command="voz", user_text="<voice>", response=response, state_override=state)
        return response

    media = message.get("voice") or message.get("audio") or {}
    file_id = str(media.get("file_id", "")).strip()
    duration_seconds = int(media.get("duration", 0) or 0)
    mime_type = str(media.get("mime_type", "audio/ogg"))
    if not file_id:
        response = {"status": "voice_missing", "text": "No encontré audio válido en el mensaje."}
        _remember_turn(store, chat_id=chat_id, command="voz", user_text="<voice>", response=response, state_override=state)
        return response

    language = os.getenv("OPENCLAW_TELEGRAM_VOICE_LANGUAGE", "es")
    target_dir = Path(os.getenv("OPENCLAW_TELEGRAM_AUDIO_DIR", store.db_path.parent / "telegram_audio"))
    token = os.getenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "")
    downloaded = download_telegram_file(bot_token=token, file_id=file_id, target_dir=target_dir)
    if downloaded.get("status") != "ok":
        response = {
            "status": "voice_download_error",
            "text": f"No pude descargar nota de voz: {downloaded.get('error', 'error_desconocido')}",
        }
        _remember_turn(store, chat_id=chat_id, command="voz", user_text="<voice>", response=response, state_override=state)
        return response

    source_path = Path(str(downloaded.get("path", "")))
    transcript = transcribe_audio(audio_path=source_path, language=language)
    if transcript.get("status") != "ok":
        response = {
            "status": "voice_transcription_error",
            "text": (
                "No pude transcribir audio en este momento. "
                f"detalle={transcript.get('error', 'stt_no_disponible')}. "
                "Puedes reenviar como texto o revisar OPENAI_API_KEY."
            ),
        }
        _remember_turn(store, chat_id=chat_id, command="voz", user_text="<voice>", response=response, state_override=state)
        return response

    transcript_text = str(transcript.get("text", "")).strip()
    style = str(call_mode.get("style", "estable")).strip().lower()
    if style not in CALL_STYLES:
        style = "estable"
    objective = transcript_text
    if style == "rapida":
        objective = f"Responde en maximo 3 frases cortas. Contexto de llamada rapida: {transcript_text}"

    answer = _chat_response(objective, repo_root=repo_root, store=store, chat_id=chat_id, state=state)
    answer_text = str(answer.get("text", "")).strip()
    tts_input = _extract_answer_for_tts(answer_text, style=style)
    synthesized = synthesize_speech(text=tts_input, target_dir=target_dir)

    artifact = VoiceMessageArtifact(
        artifact_id=f"VOC-{uuid4().hex[:12]}",
        chat_id=chat_id,
        source="telegram",
        source_file_id=file_id,
        source_path=str(source_path),
        source_mime_type=mime_type,
        duration_seconds=duration_seconds or None,
        language_code=language,
        transcript_text=transcript_text,
        transcript_provider=str(transcript.get("provider", "openai")),
        transcript_model=str(transcript.get("model", "")),
        transcript_confidence=None,
        tts_provider=str(synthesized.get("provider", "")),
        tts_model=str(synthesized.get("model", "")),
        tts_voice=str(synthesized.get("voice", "")),
        reply_audio_path=str(synthesized.get("path", "")),
        created_at=datetime.now(UTC).isoformat(),
    )
    store.save_telegram_voice_event(
        artifact,
        payload={
            "status": synthesized.get("status", "unknown"),
            "transcript_preview": redact_text(transcript_text),
            "answer_preview": redact_text(tts_input),
            "style": style,
            "telegram_file_path": downloaded.get("telegram_file_path", ""),
        },
    )

    if synthesized.get("status") == "ok":
        response = {
            "status": "ok_voice",
            "text": f"Voz procesada. estilo={style}\ntranscripcion={redact_text(transcript_text)}",
            "audio_path": str(synthesized.get("path", "")),
            "audio_caption": f"OpenClaw voz ({style})",
        }
        _remember_turn(store, chat_id=chat_id, command="voz", user_text=transcript_text, response=response, state_override=state)
        return response

    response = {
        "status": "voice_tts_error",
        "text": (
            "Transcripción disponible, pero no pude sintetizar voz. "
            f"detalle={synthesized.get('error', 'tts_no_disponible')}\n"
            f"{answer_text or tts_input}"
        ),
    }
    _remember_turn(store, chat_id=chat_id, command="voz", user_text=transcript_text, response=response, state_override=state)
    return response


def _call_mode_response(argument: str, *, state: dict[str, Any]) -> dict[str, Any]:
    current = dict(state.get("call_mode") or {"enabled": False, "style": "estable"})
    updated = _parse_call_mode_input(argument, current=current)
    state["call_mode"] = updated
    mode = "on" if updated["enabled"] else "off"
    return {
        "status": "ok",
        "text": (
            "Modo llamada actualizado. "
            f"estado={mode} estilo={updated['style']}. "
            "Envía una nota de voz para usar STT+respuesta en audio."
        ),
    }


def _parse_call_mode_input(argument: str, *, current: dict[str, Any]) -> dict[str, Any]:
    tokens = [token.strip().lower() for token in argument.split() if token.strip()]
    enabled = bool(current.get("enabled", False))
    style = str(current.get("style", "estable")).strip().lower() or "estable"
    for token in tokens:
        if token in {"on", "activar", "activa", "enable", "enabled"}:
            enabled = True
        elif token in {"off", "desactivar", "desactiva", "disable", "disabled"}:
            enabled = False
        elif token in CALL_STYLES:
            style = token
    if style not in CALL_STYLES:
        style = "estable"
    return {"enabled": enabled, "style": style}


def _voice_requires_call_mode() -> bool:
    return os.getenv("OPENCLAW_TELEGRAM_VOICE_REQUIRE_CALL_MODE", "0").strip().lower() in {"1", "true", "yes", "on"}


def _extract_answer_for_tts(text: str, *, style: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if lines and lines[0].startswith("[") and "provider=" in lines[0]:
        lines = lines[1:]
    output = "\n".join(lines).strip() or "No pude generar respuesta"
    if style == "rapida":
        return output[:320]
    return output[:1400]


def _research_response(
    argument: str,
    *,
    repo_root: Path,
    store: OpenClawStore,
    chat_id: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    started_at = time.perf_counter()
    stage_ms: dict[str, float | None] = {
        "parse_ms": 0.0,
        "profile_ms": 0.0,
        "semantic_ms": 0.0,
        "routing_ms": None,
        "web_search_ms": None,
        "provider_ms": None,
        "delivery_ms": None,
        "total_ms": None,
    }
    if not argument.strip():
        return {"status": "missing_argument", "text": "Uso: /investiga <pregunta>"}
    task = TaskEnvelope(
        task_id=f"TGM-INV-{uuid4().hex[:8]}",
        title="Investigación Telegram",
        domain="academico",
        objective=argument,
        complexity="high",
        risk_level="medium",
        requires_citations=True,
        extra_context={"telegram_command": "investiga", "task_type": "comparacion_literatura", "request_profile": "research", "chat_id": chat_id},
    )
    routing_started = time.perf_counter()
    decision = route_task(task, load_domain_policies(repo_root), repo_root=repo_root, store=store)
    stage_ms["routing_ms"] = _elapsed_ms(routing_started)
    store.save_task(task, decision)
    web_started = time.perf_counter()
    web = web_search(argument)
    stage_ms["web_search_ms"] = _elapsed_ms(web_started)
    prompt = _research_prompt(argument, web=web, state=state)
    base_url, model = _select_research_runtime(repo_root, argument)
    
    with TypingHeartbeat(chat_id):
        provider_started = time.perf_counter()
        ok, response = ollama_generate(base_url=base_url, model=model, prompt=prompt, timeout_seconds=180)
        stage_ms["provider_ms"] = _elapsed_ms(provider_started)
        mode = "investigacion_web_read_only" if web["status"] == "ok" else "investigacion_local_sin_web"
        if not ok:
            fallback = os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")
            provider_started = time.perf_counter()
            ok, response = ollama_generate(
                base_url=os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                model=fallback,
                prompt=prompt,
                timeout_seconds=120,
            )
            stage_ms["provider_ms"] = round((stage_ms["provider_ms"] or 0.0) + _elapsed_ms(provider_started), 3)
            response_payload = {
                "status": "degraded" if ok else "model_error",
                "text": f"[degradado a {fallback}] provider={decision.provider} modo={mode}\n{_normalize_research_response(response, web=web) if response else 'No pude completar la investigación local.'}",
            }
        else:
            response_payload = {"status": "ok", "text": f"[{model}] provider={decision.provider} modo={mode}\n{_normalize_research_response(response, web=web)}"}
    used_sources = [str(item.get("url", "")).strip() for item in list(web.get("results", [])) if str(item.get("url", "")).strip()]
    source_kind = "web" if web.get("status") == "ok" else "none"
    support_state = "supported" if used_sources else "partially_supported" if web.get("status") == "ok" else "unsupported"
    stage_ms["total_ms"] = _elapsed_ms(started_at)
    store.log_task_outcome(
        task_id=task.task_id,
        domain=task.domain,
        provider=decision.provider,
        outcome=str(response_payload["status"]),
        request_kind=str(task.extra_context.get("request_profile", "research")),
        complexity=str(task.complexity),
        latency_ms=(time.perf_counter() - started_at) * 1000.0,
        error_text="",
        payload={
            "model": model,
            "provider_mode": decision.mode,
            "mode": mode,
            "web_status": web.get("status", "unknown"),
            "metrics": stage_ms,
            "sources": {
                "kind": source_kind,
                "urls": used_sources,
                "support_state": support_state,
            },
            "claims": {
                "derived_from_sources": bool(used_sources),
                "support_state": support_state,
            },
        },
    )
    _save_request_trace(
        store=store,
        trace_id=f"INV-{uuid4().hex[:10]}",
        task_id=task.task_id,
        channel="telegram",
        command="investiga",
        request_kind="research",
        complexity=str(task.complexity),
        selected_provider=decision.provider,
        selected_model=model,
        fallback_reason="" if response_payload["status"] == "ok" else "research_degraded_or_error",
        stage_ms=stage_ms,
        prompt=prompt,
        payload={
            "mode": mode,
            "web_status": web.get("status", "unknown"),
            "source_kind": source_kind,
            "support_state": support_state,
            "used_sources": used_sources,
        },
    )
    return response_payload


def _tool_response(argument: str, *, repo_root: Path, store: OpenClawStore, state: dict[str, Any], chat_id: str) -> dict[str, Any]:
    action = argument.strip().lower()
    if not action:
        return {
            "status": "missing_argument",
            "text": "Uso: /herramienta <estado|modelos|preflight|doctor|presupuesto|secretos|equipo|logs|eventos|aprobaciones|memoria|accion>",
        }
    if action in {"ayuda", "help", "?", "ejemplos"}:
        return {"status": "ok", "text": _tool_help_text()}
    if any(marker in action for marker in MUTATION_MARKERS):
        return _approval_proposal(argument, repo_root=repo_root, store=store, source_command="herramienta", chat_id=chat_id, mutates_state=True)
    if action not in READ_ONLY_TOOLS:
        return _approval_proposal(argument, repo_root=repo_root, store=store, source_command="herramienta", chat_id=chat_id)
    if action == "estado":
        return {"status": "ok", "text": _status_text(repo_root, store)}
    if action == "modelos":
        return {"status": "ok", "text": _models_text()}
    if action == "equipo":
        return {"status": "ok", "text": _host_summary_text()}
    if action == "logs":
        return {"status": "ok", "text": _logs_text()}
    if action == "eventos":
        return {"status": "ok", "text": _events_text(store)}
    if action == "aprobaciones":
        return {"status": "ok", "text": _approvals_text(store)}
    if action == "memoria":
        return {"status": "ok", "text": _memory_summary_text(state)}
    if action == "preflight":
        return {"status": "ok", "text": json.dumps(build_preflight_report(repo_root), ensure_ascii=False, indent=2)[:3500]}
    if action == "doctor":
        return {"status": "ok", "text": _status_text(repo_root, store)}
    if action == "presupuesto":
        return {"status": "ok", "text": "Consulta presupuesto disponible desde la pasarela web o CLI; ejecución mutante deshabilitada por Telegram."}
    if action == "secretos":
        return {"status": "ok", "text": "Secretos: estado consultable por CLI; valores nunca se exponen por Telegram."}
    return _approval_proposal(argument, repo_root=repo_root, store=store, source_command="herramienta", chat_id=chat_id)


def _safe_prompt(
    text: str,
    *,
    state: dict[str, Any],
    web: dict[str, Any] | None = None,
    profile: dict[str, str] | None = None,
) -> str:
    now = _local_now()
    profile = profile or _chat_request_profile(text, state=state)
    memory = "" if profile["request_kind"] == "standard" and profile["complexity"] == "low" else _memory_prompt(state)
    reasoning_block = ""
    evidence_block = ""
    if web and web.get("status") == "ok":
        evidence_block = f"\nEVIDENCIA WEB DE APOYO (CONTEXTO EXTERNO):\n{_web_evidence_prompt(web)}\n"
        
    if profile["request_kind"] in {"reasoning", "deep", "coding", "knowledge"}:
        reasoning_block = (
            "INSTRUCCIONES DE RAZONAMIENTO AVANZADO:\n"
            "1. Antes de responder, analiza el problema paso a paso internamente.\n"
            "2. Si la pregunta es técnica o factual, verifica cada afirmación contra la evidencia proporcionada o tu conocimiento.\n"
            "3. Clasifica tu confianza: [ALTO] dato verificable con evidencia, [MEDIO] inferencia razonada, [BAJO] hipótesis.\n"
            "4. Si falta información crítica a pesar de la evidencia, indícalo y sugiere una investigación más profunda.\n"
            "5. Prioriza precisión sobre extensión. Si no sabes, dilo claramente.\n"
        )
    brevity = "Responde en máximo 2 frases." if profile["request_kind"] == "standard" and profile["complexity"] == "low" else "Responde en español, de forma concisa, rigurosa y operativa."
    return (
        "Eres OpenClaw, asistente de investigación de posgrado con razonamiento avanzado y uso elevado de herramientas.\n"
        f"{reasoning_block}"
        f"{evidence_block}"
        "Herramientas disponibles: /investiga (búsqueda web completa), /herramienta (estado, modelos, presupuesto), /memoria (contexto).\n"
        "Reglas: no inventes fuentes; no digas que investigaste si no hay evidencia externa; "
        "no afirmes que ejecutaste herramientas si no aparece en la memoria como resultado real; "
        "si falta contexto, dilo y pide el dato mínimo.\n"
        f"{brevity}\n"
        f"Fecha local: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}.\n"
        f"Memoria breve:\n{memory or 'sin memoria inyectada para mantener baja latencia'}\n"
        f"Usuario: {text.strip()}"
    )


def _research_prompt(text: str, *, web: dict[str, Any], state: dict[str, Any]) -> str:
    evidence = _web_evidence_prompt(web)
    return (
        "Eres OpenClaw en modo investigación. Aplica razonamiento científico riguroso.\n"
        "PROTOCOLO DE INVESTIGACIÓN:\n"
        "1. ANALIZA la pregunta: identifica conceptos clave y alcance.\n"
        "2. EVALÚA la evidencia web proporcionada: calidad, relevancia, sesgo potencial.\n"
        "3. SINTETIZA hallazgos contrastando múltiples fuentes cuando sea posible.\n"
        "4. CLASIFICA cada hallazgo: [VERIFICADO] si tiene respaldo directo, "
        "[INFERIDO] si es deducción razonada, [HIPÓTESIS] si requiere validación.\n"
        "5. Identifica CONTRADICCIONES entre fuentes.\n"
        "No inventes citas, URLs ni validación humana.\n"
        "Formato obligatorio:\n"
        "razonamiento:\n- ...\n"
        "hallazgos:\n- [VERIFICADO|INFERIDO|HIPÓTESIS] ...\n"
        "contradicciones:\n- ...\n"
        "supuestos:\n- ...\n"
        "riesgos:\n- ...\n"
        "siguientes pasos:\n- ...\n\n"
        f"Memoria breve:\n{_memory_prompt(state)}\n\n"
        f"Evidencia web read-only:\n{evidence}\n\n"
        f"Pregunta: {text.strip()}"
    )


def _normalize_research_response(text: str, *, web: dict[str, Any] | None = None) -> str:
    normalized = text.strip()
    for heading in ("razonamiento", "hallazgos", "contradicciones", "supuestos", "riesgos", "siguientes pasos"):
        normalized = re.sub(rf"(?im)^\s*{re.escape(heading)}\s*:", f"{heading}:", normalized)
    required = ("hallazgos:", "supuestos:", "riesgos:", "siguientes pasos:")
    if all(item in normalized.lower() for item in required):
        output = normalized
    else:
        output = "\n".join(
            [
                "razonamiento:",
                "- Análisis preliminar sin formato estructurado del modelo.",
                "hallazgos:",
                f"- {normalized or 'No se obtuvo contenido útil del modelo.'}",
                "contradicciones:",
                "- No identificadas en esta iteración.",
                "supuestos:",
                "- Investigación preliminar no validada por humano.",
                "riesgos:",
                "- Requiere contraste con fuentes externas antes de uso académico formal.",
                "siguientes pasos:",
                "- Repetir con fuentes verificadas y registrar evidencia antes de incorporar conclusiones.",
            ]
        )
    if web is None:
        return output
    if web.get("status") == "ok":
        sources = []
        results, trusted_only = _trusted_web_results(list(web.get("results", [])))
        if not trusted_only:
            sources.append("- no hubo fuentes académicas o institucionales suficientes; se muestran fuentes generales.")
        for item in results[:3]:
            label = _web_source_label(str(item.get("url", "")))
            title = str(item.get("title", "")).strip() or "Fuente web"
            url = str(item.get("url", "")).strip()
            snippet = str(item.get("snippet", "")).strip()
            lines = [f"- [{label}] {title}", f"  {url}"]
            if snippet:
                lines.insert(2, f"  {snippet}")
            sources.append("\n".join(lines))
        return output + "\nfuentes priorizadas:\n" + "\n".join(sources)
    return output + f"\nfuentes:\n- sin_web: {web.get('error', 'fuentes externas no disponibles')}"


def _load_chat_state(store: OpenClawStore, chat_id: str) -> dict[str, Any]:
    state = store.get_cached_context(_chat_state_key(chat_id)) or {"turns": []}
    state.setdefault("turns", [])
    state.setdefault("preferences", [])
    state.setdefault("prompt_adjustment_proposals", [])
    state.setdefault("call_mode", {"enabled": False, "style": "estable"})
    return state


def _learn_response(argument: str, *, state: dict[str, Any], auto_proposal: bool = False) -> dict[str, Any]:
    text = redact_text(argument.strip())
    if not text:
        return {
            "status": "missing_argument",
            "text": "Uso: /aprender <preferencia o ajuste>. Ejemplo: /aprender prefiero respuestas breves.",
        }
    item = {"text": text[:500], "created_at": datetime.now(UTC).isoformat()}
    target_key = "prompt_adjustment_proposals" if auto_proposal or _looks_like_prompt_adjustment(text) else "preferences"
    items = list(state.get(target_key, []))
    if not any(existing.get("text") == item["text"] for existing in items):
        items.append(item)
    state[target_key] = items[-MEMORY_ITEM_LIMIT:]
    label = "ajuste_prompt_pendiente" if target_key == "prompt_adjustment_proposals" else "preferencia"
    return {
        "status": "learning_proposed" if target_key == "prompt_adjustment_proposals" else "learned",
        "text": "\n".join(
            [
                "Aprendizaje registrado en memoria de este chat.",
                f"tipo={label}",
                f"valor={item['text']}",
                "Consulta /memoria para revisarlo. No ejecuta herramientas ni valida cambios humanos.",
            ]
        ),
    }


def _forget_response(argument: str, *, chat_id: str, store: OpenClawStore) -> dict[str, Any]:
    target = argument.strip().lower() or "todo"
    state = _load_chat_state(store, chat_id)
    if target in {"todo", "all", "memoria"}:
        new_state: dict[str, Any] = {
            "turns": [],
            "preferences": [],
            "prompt_adjustment_proposals": [],
            "call_mode": {"enabled": False, "style": "estable"},
        }
        label = "memoria completa"
    elif target in {"preferencia", "preferencias", "preferences"}:
        state["preferences"] = []
        new_state = state
        label = "preferencias"
    elif target in {"turno", "turnos", "contexto", "conversacion", "conversación"}:
        state["turns"] = []
        state["rolling_summary"] = ""
        state.pop("last_command", None)
        state.pop("last_result", None)
        new_state = state
        label = "turnos"
    elif target in {"ajustes", "prompt", "propuestas"}:
        state["prompt_adjustment_proposals"] = []
        new_state = state
        label = "ajustes de prompt pendientes"
    else:
        return {
            "status": "missing_argument",
            "text": "Uso: /olvidar [todo|preferencias|turnos|ajustes]",
        }
    store.cache_context(_chat_state_key(chat_id), new_state)
    return {"status": "forgotten", "skip_memory_update": True, "text": f"Memoria limpiada: {label}."}


def _natural_command_response(
    argument: str,
    *,
    repo_root: Path,
    store: OpenClawStore,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    lowered = argument.lower().strip(" ¿?¡!")
    if not lowered:
        return None
    if lowered in {"olvidalo", "olvídalo", "cancela", "cancelar", "dejalo", "déjalo"}:
        state.pop("last_approval", None)
        state["approval_history"] = []
        return {"status": "forgotten", "text": "Entendido. Dejé sin efecto la intención pendiente de este chat."}
    if any(marker in lowered for marker in ("qué hora", "que hora", "hora actual", "día es", "dia es", "fecha actual")):
        return {"status": "ok", "text": _time_text()}
    if lowered in {"estado", "status"} or "estado openclaw" in lowered or "estado de openclaw" in lowered:
        return {"status": "ok", "text": _status_text(repo_root, store)}
    if lowered in {"modelos", "lista modelos"} or ("modelos" in lowered and any(word in lowered for word in ("lista", "cuáles", "cuales", "disponibles"))):
        return {"status": "ok", "text": _models_text()}
    summary_response = _summary_request_response(argument, state=state)
    if summary_response is not None:
        return summary_response
    conversion_response = _unit_conversion_response(argument)
    if conversion_response is not None:
        return conversion_response
    if "aprobaciones" in lowered or "apr pendientes" in lowered:
        return {"status": "ok", "text": _approvals_text(store)}
    if "eventos telegram" in lowered or "últimos eventos" in lowered or "ultimos eventos" in lowered:
        return {"status": "ok", "text": _events_text(store)}
    return None


def _resolve_research_argument(argument: str, state: dict[str, Any]) -> str:
    text = argument.strip()
    lowered = text.lower().strip(" ¿?¡!")
    if text and lowered not in {"investigalo", "investígalo", "investigarla", "investigarlo", "eso", "lo anterior"}:
        return text
    for turn in reversed(list(state.get("turns", []))):
        candidate = str(turn.get("user", "")).strip()
        if candidate and not _is_greeting(candidate) and candidate.lower().strip(" ¿?¡!") not in {"si", "sí", "valido", "válido", "ejecuta", "hazlo"}:
            return candidate
    approval = state.get("last_approval") or {}
    return str(approval.get("intent", "")).strip()


def _approval_response_if_confirmation(
    argument: str,
    *,
    repo_root: Path,
    store: OpenClawStore,
    state: dict[str, Any],
    chat_id: str,
) -> dict[str, Any] | None:
    lowered = argument.lower().strip(" ¿?¡!.")
    has_pending = bool(state.get("last_approval"))
    is_exact_confirmation = lowered in APPROVAL_CONFIRMATIONS
    is_followup_confirmation = has_pending and any(lowered.startswith(f"{item} ") for item in APPROVAL_CONFIRMATIONS)
    if not is_exact_confirmation and not is_followup_confirmation:
        return None
    return _approval_response("", repo_root=repo_root, store=store, state=state, chat_id=chat_id)


def _approval_response(
    argument: str,
    *,
    repo_root: Path,
    store: OpenClawStore,
    state: dict[str, Any],
    chat_id: str,
) -> dict[str, Any]:
    requested_id = _extract_approval_id(argument)
    pending = {item["approval_id"]: item for item in store.list_pending_approvals()}
    history = [item for item in list(state.get("approval_history", [])) if item.get("approval_id") in pending]
    if requested_id:
        if requested_id not in pending:
            return {"status": "approval_not_found", "text": f"No encontré APR pendiente: {requested_id}."}
        approval = dict(history[-1]) if history and history[-1].get("approval_id") == requested_id else {"approval_id": requested_id}
    else:
        if len(history) > 1:
            ids = ", ".join(str(item.get("approval_id")) for item in history)
            return {"status": "approval_ambiguous", "text": f"Hay más de una APR pendiente en este chat: {ids}. Usa /aprobar APR-..."}
        if not history:
            return {"status": "approval_not_found", "text": "No hay una propuesta pendiente reciente en este chat."}
        approval = dict(history[-1])
        if _approval_expired(approval):
            return {"status": "approval_expired", "text": f"La propuesta {approval.get('approval_id')} expiró. Vuelve a pedir la acción para crear una APR nueva."}

    approval_id = str(approval.get("approval_id"))
    draft = str(approval.get("draft_command", ""))
    intent = str(approval.get("intent", ""))
    if _requires_step_id_for_approval(draft, intent) and "VAL-STEP-" not in argument:
        return {
            "status": "step_id_required",
            "text": f"La propuesta {approval_id} requiere Step ID explícito. Usa /aprobar {approval_id} VAL-STEP-XXX.",
        }
    if _is_image_draft(draft):
        return _execute_approved_image(approval_id, intent, repo_root=repo_root, store=store, state=state, chat_id=chat_id)
    store.mark_approval(approval_id, "approved")
    state.pop("last_approval", None)
    state["approval_history"] = [item for item in history if item.get("approval_id") != approval_id]
    return {
        "status": "approved",
        "text": f"Propuesta aprobada: {approval_id}. No se ejecutó automáticamente porque la herramienta no está en la allowlist de Telegram.",
    }


def _extract_approval_id(text: str) -> str:
    match = re.search(r"APR-[A-Z0-9-]+", text, re.I)
    return match.group(0) if match else ""


def _approval_expired(approval: dict[str, Any]) -> bool:
    created = str(approval.get("created_at", "")).strip()
    if not created:
        return False
    try:
        created_at = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except ValueError:
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return (datetime.now(UTC) - created_at).total_seconds() > APPROVAL_TTL_SECONDS


def _requires_step_id_for_approval(draft: str, intent: str) -> bool:
    lowered = f"{draft} {intent}".lower()
    return any(marker in lowered for marker in MUTATION_MARKERS) and not _is_image_draft(draft)


def _is_image_draft(draft: str) -> bool:
    return draft.strip().startswith("openclaw-image-generate")


def _execute_approved_image(
    approval_id: str,
    intent: str,
    *,
    repo_root: Path,
    store: OpenClawStore,
    state: dict[str, Any],
    chat_id: str,
) -> dict[str, Any]:
    del repo_root, chat_id
    prompt = _image_prompt_from_intent(intent, state)
    result = generate_image_from_prompt(prompt)
    if result.get("status") != "ok":
        return {
            "status": "image_backend_unavailable",
            "text": "\n".join(
                [
                    f"Propuesta aprobada: {approval_id}",
                    "No pude generar la imagen con el backend local.",
                    f"backend={result.get('backend', 'desconocido')} error={result.get('error', result.get('status', 'error'))}",
                ]
            ),
        }
    store.mark_approval(approval_id, "approved")
    state.pop("last_approval", None)
    state["approval_history"] = [item for item in list(state.get("approval_history", [])) if item.get("approval_id") != approval_id]
    image_path = str(result.get("path", ""))
    return {
        "status": "ok_image",
        "image_path": image_path,
        "image_caption": "OpenClaw imagen local",
        "text": f"Imagen generada localmente.\nAPR={approval_id}\narchivo={image_path}",
    }


def _image_prompt_from_intent(intent: str, state: dict[str, Any]) -> str:
    base = intent.strip() or "imagen solicitada por el usuario"
    lowered = base.lower()
    if "tezcatlipoca" in lowered or "tezkatlipoca" in lowered:
        return (
            "Dibujo detallado de Tezcatlipoca, deidad mexica, con espejo de obsidiana humeante, "
            "rostro ceremonial, tocado de plumas, motivos negros, rojos y dorados, estilo ilustracion "
            "historica respetuosa inspirada en codices mesoamericanos, fondo neutro, alta nitidez."
        )
    memory = str(state.get("rolling_summary", "")).strip()
    if memory:
        return f"{base}. Contexto reciente: {memory[:300]}"
    return base


def _is_learning_request(text: str) -> bool:
    lowered = text.lower().strip()
    return any(
        marker in lowered
        for marker in (
            "aprende que",
            "recuerda que",
            "prefiero ",
            "mi preferencia",
            "no vuelvas",
            "cuando respondes",
            "responde siempre",
            "corrige tu comportamiento",
            "ajusta tu comportamiento",
        )
    )


def _looks_like_prompt_adjustment(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "no vuelvas",
            "cuando respondes",
            "responde siempre",
            "corrige",
            "ajusta",
            "formato",
            "prompt",
        )
    )


def _build_rolling_summary(state: dict[str, Any]) -> str:
    turns = [turn for turn in list(state.get("turns", [])) if str(turn.get("kind", "normal")) != "greeting"][-6:]
    if not turns:
        return ""
    fragments = []
    for turn in turns:
        user = str(turn.get("user", "")).replace("\n", " ")[:80]
        status = str(turn.get("status", ""))[:40]
        command = str(turn.get("command", "chat"))[:30]
        fragments.append(f"{command}:{user}->{status}")
    return " | ".join(fragments)[-CHAT_SUMMARY_LIMIT:]


def _remember_turn(
    store: OpenClawStore,
    *,
    chat_id: str,
    command: str,
    user_text: str,
    response: dict[str, Any],
    state_override: dict[str, Any] | None = None,
) -> None:
    state = state_override or _load_chat_state(store, chat_id)
    turns = list(state.get("turns", []))
    turns.append(
        {
            "command": command,
            "user": redact_text(user_text),
            "status": response.get("status", ""),
            "assistant": redact_text(str(response.get("text", ""))),
            "kind": "greeting" if _is_greeting(user_text) else "normal",
            "created_at": datetime.now(UTC).isoformat(),
        }
    )
    state["turns"] = turns[-CHAT_MEMORY_LIMIT:]
    state["rolling_summary"] = _build_rolling_summary(state)
    state["last_command"] = command
    state["last_result"] = redact_text(str(response.get("text", "")))
    if response.get("approval_id"):
        approval_state = {
            "approval_id": response.get("approval_id"),
            "intent": response.get("intent", user_text),
            "draft_command": response.get("draft_command", ""),
            "created_at": datetime.now(UTC).isoformat(),
            "chat_id": chat_id,
        }
        state["last_approval"] = approval_state
        history = list(state.get("approval_history", []))
        history.append(approval_state)
        state["approval_history"] = history[-8:]
    store.cache_context(_chat_state_key(chat_id), state)


def _chat_state_key(chat_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.:-]", "_", chat_id or "cli")
    return f"telegram:chat:{safe}:state"


def _memory_prompt(state: dict[str, Any]) -> str:
    turns = [turn for turn in list(state.get("turns", [])) if str(turn.get("kind", "normal")) != "greeting"][-4:]
    preferences = list(state.get("preferences", []))[-6:]
    prompt_adjustments = list(state.get("prompt_adjustment_proposals", []))[-3:]
    summary = str(state.get("rolling_summary", "")).strip()
    lines = []
    call_mode = dict(state.get("call_mode") or {})
    if call_mode:
        lines.append(f"- call_mode: {'on' if call_mode.get('enabled') else 'off'} ({call_mode.get('style', 'estable')})")
    if summary:
        lines.append(f"- resumen: {summary[:CHAT_SUMMARY_LIMIT]}")
    for item in preferences:
        lines.append(f"- preferencia: {item.get('text', '')[:180]}")
    for item in prompt_adjustments:
        lines.append(f"- ajuste_prompt_pendiente: {item.get('text', '')[:180]}")
    if not turns:
        return "\n".join(lines) if lines else "- sin memoria previa"
    for turn in turns:
        lines.append(f"- usuario({turn.get('command', 'chat')}): {turn.get('user', '')[:160]}")
        lines.append(f"  respuesta: {turn.get('assistant', '')[:220]}")
    return "\n".join(lines)


def _local_now() -> datetime:
    try:
        tz = ZoneInfo(MEXICO_TZ)
    except ZoneInfoNotFoundError:
        tz = timezone.utc
    return datetime.now(tz)


def _time_text() -> str:
    ntp = _query_ntp_time(NTP_SERVER)
    source = f"CENAM NTP {NTP_SERVER}" if ntp is not None else "reloj_local_fallback"
    dt_utc = ntp or datetime.now(UTC)
    try:
        local = dt_utc.astimezone(ZoneInfo(MEXICO_TZ))
    except ZoneInfoNotFoundError:
        local = dt_utc
    return "\n".join(
        [
            "Hora OpenClaw:",
            f"fuente={source}",
            f"utc={dt_utc.strftime('%Y-%m-%d %H:%M:%S %Z')}",
            f"pachuca={local.strftime('%Y-%m-%d %H:%M:%S %Z %z')}",
        ]
    )


def _query_ntp_time(server: str, *, timeout_seconds: float = 3.0) -> datetime | None:
    query = b"\x1b" + 47 * b"\0"
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout_seconds)
            sock.sendto(query, (server, 123))
            data, _ = sock.recvfrom(512)
    except OSError:
        return None
    if len(data) < 48:
        return None
    seconds, fraction = struct.unpack("!II", data[40:48])
    unix_time = seconds - 2208988800 + fraction / 2**32
    return datetime.fromtimestamp(unix_time, UTC)


def web_search(query: str, *, timeout_seconds: int = 20, limit: int = 5) -> dict[str, Any]:
    encoded = parse.urlencode({"q": query})
    attempts: list[dict[str, Any]] = []
    timeout_seconds = min(timeout_seconds, 12)
    endpoints = [
        ("html", "https://html.duckduckgo.com/html/?{encoded}"),
        ("lite", "https://duckduckgo.com/lite/?{encoded}"),
        ("html", "http://html.duckduckgo.com/html/?{encoded}"),
        ("lite", "http://duckduckgo.com/lite/?{encoded}"),
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "DNT": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://duckduckgo.com/",
        "Connection": "keep-alive"
    }
    parser_by_kind = {
        "html": _parse_duckduckgo_html,
        "lite": _parse_duckduckgo_lite,
    }
    last_error = ""

    def fetch_endpoint(kind: str, template: str) -> dict[str, Any]:
        url = template.format(encoded=encoded)
        req = request.Request(url, headers=headers)
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
        except error.HTTPError as exc:
            error_code = "web_blocked_by_cloudflare_or_ddg" if exc.code == 403 else f"web_http_error_{exc.code}"
            return {"endpoint": url, "status": "error", "error": error_code}
        except error.URLError as exc:
            reason = exc.reason if hasattr(exc, "reason") else exc
            return {"endpoint": url, "status": "error", "error": f"web_unavailable:{reason}"}
        except OSError as exc:
            return {"endpoint": url, "status": "error", "error": f"web_unavailable:{exc}"}

        parser = parser_by_kind[kind]
        results = parser(raw, limit=max(limit * 3, 10))
        results = _prioritize_web_results([item for item in results if _search_result_relevant(query, item)])[:limit]
        if results:
            return {"endpoint": url, "status": "ok", "results": results, "count": len(results)}
        return {"endpoint": url, "status": "empty", "error": "web_sin_resultados_o_bloqueo"}

    def run_phase(phase_endpoints: list[tuple[str, str]]) -> dict[str, Any] | None:
        if not phase_endpoints:
            return None
        with ThreadPoolExecutor(max_workers=len(phase_endpoints)) as pool:
            futures = [pool.submit(fetch_endpoint, kind, template) for kind, template in phase_endpoints]
            for future in as_completed(futures):
                outcome = future.result()
                attempts.append({key: value for key, value in outcome.items() if key != "results"})
                if outcome.get("status") == "ok":
                    for pending in futures:
                        if pending is not future:
                            pending.cancel()
                    return outcome
        return None

    primary = run_phase(endpoints[:2])
    if primary is not None:
        return {
            "status": "ok",
            "results": primary["results"],
            "endpoint": primary["endpoint"],
            "attempts": attempts,
        }

    secondary = run_phase(endpoints[2:])
    if secondary is not None:
        return {
            "status": "ok",
            "results": secondary["results"],
            "endpoint": secondary["endpoint"],
            "attempts": attempts,
        }

    last_error = next((item.get("error", "") for item in reversed(attempts) if item.get("error")), "")
    return {
        "status": "error",
        "error": last_error or "web_unavailable",
        "attempts": attempts,
    }


def _parse_duckduckgo_lite(raw: str, *, limit: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    # En Lite los resultados están en tablas o celdas específicas
    # Títulos: <a class="result-link" href="...">...</a>
    # Snippets: <td class="result-snippet">...</td>
    pattern = re.compile(r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
    snippets = re.findall(r'<td[^>]+class="result-snippet"[^>]*>(.*?)</td>', raw, re.I | re.S)
    
    for index, match in enumerate(pattern.finditer(raw)):
        if len(items) >= limit:
            break
        href = unescape(match.group(1))
        title = unescape(re.sub(r"<[^>]+>", "", match.group(2))).strip()
        
        snippet = ""
        if index < len(snippets):
            snippet = unescape(re.sub(r"<[^>]+>", "", snippets[index])).strip()
            
        # Limpieza de URL de redirección DDG
        if "/l/?" in href:
            parsed_href = parse.urlparse(href)
            qs = parse.parse_qs(parsed_href.query)
            href = qs.get("uddg", [href])[0]
            
        items.append({
            "title": title,
            "url": href,
            "snippet": snippet
        })
    return items


def _search_result_relevant(query: str, item: dict[str, str]) -> bool:
    parsed = parse.urlparse(item.get("url", ""))
    host = parsed.netloc.lower().removeprefix("www.")
    if _web_source_tier(host) >= 4:
        return False
    haystack = f"{item.get('title', '')} {item.get('snippet', '')}".lower()
    terms = [term for term in re.findall(r"[a-záéíóúñü0-9]{4,}", query.lower()) if term not in {"dame", "para", "sobre", "como", "general"}]
    if not terms:
        return True
    return any(term in haystack for term in terms[:4])


def _web_source_tier(url_or_host: str) -> int:
    host = url_or_host.lower().removeprefix("www.")
    academic_markers = (
        ".edu",
        ".ac.",
        "arxiv.org",
        "pubmed.ncbi.nlm.nih.gov",
        "ncbi.nlm.nih.gov",
        "scielo.org",
        "redalyc.org",
        "dialnet.unirioja.es",
        "ieee.org",
        "acm.org",
        "springer.com",
        "nature.com",
        "sciencedirect.com",
        "frontiersin.org",
        "wiley.com",
        "tandfonline.com",
        "mdpi.com",
        "elsevier.com",
        "semanticscholar.org",
    )
    institutional_markers = (
        ".gov",
        ".gob.",
        "who.int",
        "un.org",
        "oecd.org",
        "unesco.org",
        "imf.org",
        "worldbank.org",
        "nih.gov",
        "cdc.gov",
        "europa.eu",
    )
    if any(marker in host for marker in academic_markers):
        return 0
    if any(marker in host for marker in institutional_markers):
        return 1
    if any(marker in host for marker in ("britannica.com", "encyclopedia.com", "merriam-webster.com", "dictionary.com")):
        return 2
    if any(marker in host for marker in ("psicologiaymente.com", "culturagenial.com", "narrativabreve.com")):
        return 4
    return 3


def _web_source_label(url: str) -> str:
    tier = _web_source_tier(url)
    return {
        0: "académica",
        1: "institucional",
        2: "referencia",
        3: "general",
        4: "desaconsejada",
    }.get(tier, "general")


def _trusted_web_results(items: list[dict[str, str]]) -> tuple[list[dict[str, str]], bool]:
    prioritized = _prioritize_web_results(items)
    trusted = [item for item in prioritized if _web_source_tier(str(item.get("url", ""))) <= 1]
    if trusted:
        return trusted, True
    return prioritized, False


def _prioritize_web_results(items: list[dict[str, str]]) -> list[dict[str, str]]:
    def sort_key(item: dict[str, str]) -> tuple[int, int, int, str]:
        url = str(item.get("url", ""))
        tier = _web_source_tier(parse.urlparse(url).netloc)
        snippet = str(item.get("snippet", ""))
        title = str(item.get("title", ""))
        return (tier, -len(snippet), -len(title), title.lower())

    return sorted(items, key=sort_key)


def _parse_duckduckgo_html(raw: str, *, limit: int) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    pattern = re.compile(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
    snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>|<div[^>]+class="result__snippet"[^>]*>(.*?)</div>', raw, re.I | re.S)
    flat_snippets = [re.sub(r"<[^>]+>", "", "".join(pair)).strip() for pair in snippets]
    for index, match in enumerate(pattern.finditer(raw)):
        href = unescape(match.group(1))
        title = unescape(re.sub(r"<[^>]+>", "", match.group(2))).strip()
        parsed = parse.urlparse(href)
        if parsed.path == "/l/":
            qs = parse.parse_qs(parsed.query)
            href = qs.get("uddg", [href])[0]
        items.append(
            {
                "title": title[:160] or href[:160],
                "url": href,
                "snippet": unescape(flat_snippets[index])[:500] if index < len(flat_snippets) else "",
            }
        )
        if len(items) >= limit:
            break
    return items


def _web_evidence_prompt(web: dict[str, Any]) -> str:
    if web.get("status") != "ok":
        return f"- sin evidencia web: {web.get('error', 'web no disponible')}"
    lines = []
    results, trusted_only = _trusted_web_results(list(web.get("results", [])))
    if not trusted_only:
        lines.append("- no hubo fuentes académicas o institucionales suficientes; se muestran fuentes generales.")
    for item in results[:5]:
        label = _web_source_label(str(item.get("url", "")))
        lines.append(
            f"- [{label}] {item['title']}\n"
            f"  url: {item['url']}\n"
            f"  extracto: {item.get('snippet', '')}"
        )
    return "\n".join(lines)


def _web_evidence_supports_response(response: str, web: dict[str, Any], query: str) -> bool:
    if not response.strip() or web.get("status") != "ok":
        return False
    query_terms = {
        term
        for term in re.findall(r"[a-záéíóúñü0-9]{4,}", query.lower())
        if term not in {"dame", "para", "sobre", "como", "qué", "que", "es", "una", "uno", "unos", "unas"}
    }
    evidence_terms: set[str] = set()
    for item in web.get("results", []):
        evidence_terms.update(
            term
            for term in re.findall(r"[a-záéíóúñü0-9]{4,}", f"{item.get('title', '')} {item.get('snippet', '')}".lower())
            if term not in {"dame", "para", "sobre", "como", "qué", "que", "es", "una", "uno", "unos", "unas"}
        )
    anchors = [term for term in evidence_terms if term not in query_terms]
    if not anchors:
        return False
    response_lower = response.lower()
    return any(anchor in response_lower for anchor in anchors)


def _knowledge_web_fallback_text(query: str, web: dict[str, Any]) -> str:
    subject = _knowledge_subject(query)
    results, trusted_only = _trusted_web_results(list(web.get("results", [])))
    lines = [f"No encontré una definición confiable para “{subject}” con el modelo local."]
    interpretation = _knowledge_interpretation(subject, results)
    if interpretation:
        lines.extend(
            [
                "",
                "Interpretación más probable:",
                f"- {interpretation}",
            ]
        )
    lines.extend(
        [
            "",
            "Contexto de la evidencia:",
            "- Revisé primero fuentes académicas e institucionales y luego completé con fuentes generales solo si fue necesario.",
            "- El texto siguiente resume lo encontrado, sin afirmar más de lo que sostienen las fuentes.",
            "",
            "Fuentes priorizadas:",
        ]
    )
    if not trusted_only:
        lines.append("Nota: no hubo fuentes académicas o institucionales suficientes; se muestran fuentes generales.")
    for item in results[:3]:
        title = str(item.get("title", "")).strip() or "Fuente web"
        snippet = str(item.get("snippet", "")).strip()
        url = str(item.get("url", "")).strip()
        label = _web_source_label(url)
        lines.append(f"1. [{label}] {title}")
        if snippet:
            lines.append(f"   {snippet}")
        lines.append(f"   {url}")
    if len(web.get("results", [])) > 3:
        lines.append("   ...")
    return "\n".join(lines)


def _knowledge_interpretation(subject: str, results: list[dict[str, str]]) -> str:
    if not results:
        return ""
    haystack = " ".join(f"{item.get('title', '')} {item.get('snippet', '')}".lower() for item in results[:3])
    subject_lower = subject.lower()
    if "hidalgo" in subject_lower:
        if "estado" in haystack or "entidad federativa" in haystack:
            return "Se refiere principalmente al estado mexicano de Hidalgo, una entidad federativa de México."
        if "miguel hidalgo" in haystack or "independencia" in haystack:
            return "Puede aludir a Miguel Hidalgo y Costilla, figura central del inicio de la independencia de México."
        return "Es un término ambiguo; en el uso común suele referirse al estado mexicano de Hidalgo o al apellido Hidalgo."
    return ""


def _knowledge_subject(query: str) -> str:
    subject = query.strip().rstrip(" ?¿¡!")
    lowered = subject.lower()
    for prefix in (
        "qué es ",
        "que es ",
        "qué fue ",
        "que fue ",
        "quién es ",
        "quien es ",
        "de qué trata ",
        "de que trata ",
    ):
        if lowered.startswith(prefix):
            return subject[len(prefix):].strip().strip("\"'“”")
    return subject.strip().strip("\"'“”")


def _is_model_request(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in MODEL_REQUEST_MARKERS)


def _is_ambiguous_action(text: str) -> bool:
    lowered = text.lower()
    if _asks_for_previous_scan_result(text, {}):
        return False
    return any(marker in lowered for marker in AMBIGUOUS_ACTION_MARKERS)


def _asks_memory_summary(text: str) -> bool:
    lowered = text.lower()
    return ("memoria" in lowered or "contexto" in lowered or "conversación" in lowered or "conversacion" in lowered) and (
        "tienes" in lowered or "hemos" in lowered or "tratado" in lowered or "puedes" in lowered
    )


def _asks_command_examples(text: str, state: dict[str, Any]) -> bool:
    lowered = text.lower()
    asks_examples = "ejemplo" in lowered or "cómo usar" in lowered or "como usar" in lowered or "ayuda" in lowered
    if not asks_examples:
        return False
    if "/modelos" in lowered or "modelos" in lowered:
        return True
    if "/herramienta" in lowered or "herramienta" in lowered or "acción" in lowered or "accion" in lowered:
        return True
    return state.get("last_command") in {"herramienta", "modelos"}


def _command_examples_text(text: str, state: dict[str, Any]) -> str:
    lowered = text.lower()
    if "/modelos" in lowered or "modelos" in lowered or state.get("last_command") == "modelos":
        return "\n".join(
            [
                "Uso de /modelos:",
                "/modelos - lista modelos visibles en edge y desktop.",
                "La selección manual persistente no está habilitada; OpenClaw usa routing automático.",
                "Para tareas pesadas usa /investiga <pregunta>.",
            ]
        )
    return _tool_help_text()


def _tool_help_text() -> str:
    return "\n".join(
        [
            "Uso de /herramienta:",
            "/herramienta estado - salud del gateway",
            "/herramienta modelos - modelos visibles",
            "/herramienta equipo - resumen local sin datos sensibles",
            "/herramienta logs - últimas líneas de logs OpenClaw si existen",
            "/herramienta eventos - últimos eventos Telegram auditados",
            "/herramienta aprobaciones - APR pendientes",
            "/herramienta memoria - contexto del chat actual",
            "/herramienta preflight - preflight JSON",
            "/herramienta doctor - diagnóstico resumido",
            "/herramienta presupuesto - resumen de presupuesto",
            "/herramienta secretos - estado sin valores sensibles",
            "Otras acciones crean propuesta APR y no se ejecutan por Telegram.",
        ]
    )


def _memory_summary_text(state: dict[str, Any]) -> str:
    turns = list(state.get("turns", []))
    preferences = list(state.get("preferences", []))
    proposals = list(state.get("prompt_adjustment_proposals", []))
    if not turns and not preferences and not proposals:
        return "Memoria de esta sesión: sin turnos previos registrados para este chat."
    lines = ["Memoria de esta sesión:"]
    summary = str(state.get("rolling_summary", "")).strip()
    if summary:
        lines.append(f"Resumen: {summary[:CHAT_SUMMARY_LIMIT]}")
    call_mode = dict(state.get("call_mode") or {})
    if call_mode:
        lines.append(f"Modo llamada: {'on' if call_mode.get('enabled') else 'off'} ({call_mode.get('style', 'estable')})")
    if preferences:
        lines.append("Preferencias:")
        for item in preferences[-6:]:
            lines.append(f"- {item.get('text', '')[:180]}")
    if proposals:
        lines.append("Ajustes de prompt pendientes:")
        for item in proposals[-6:]:
            lines.append(f"- {item.get('text', '')[:180]}")
    for turn in turns[-6:]:
        lines.append(f"- {turn.get('command', 'chat')}: {turn.get('user', '')[:140]} -> {turn.get('status', '')}")
    last_approval = state.get("last_approval")
    if last_approval:
        lines.append(f"Última propuesta: {last_approval.get('approval_id')} ({last_approval.get('intent')})")
    return "\n".join(lines)


def _host_summary_text() -> str:
    disk = shutil.disk_usage("/")
    mem = _read_meminfo()
    load = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
    lines = [
        "Equipo OpenClaw:",
        f"host={platform.node() or 'desconocido'}",
        f"sistema={platform.platform()}",
        f"python={platform.python_version()}",
        f"arquitectura={platform.machine()}",
        f"carga_1m_5m_15m={load[0]:.2f},{load[1]:.2f},{load[2]:.2f}",
        f"disco_root_gb={disk.used // (1024**3)}/{disk.total // (1024**3)} usado",
    ]
    if mem:
        lines.append(f"memoria_mb={mem.get('MemAvailable', 0) // 1024}/{mem.get('MemTotal', 0) // 1024} disponible")
    lines.append("nota=sin exponer secretos ni ejecutar comandos de red")
    return "\n".join(lines)


def _read_meminfo() -> dict[str, int]:
    path = Path("/proc/meminfo")
    if not path.exists():
        return {}
    values: dict[str, int] = {}
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            key, _, rest = line.partition(":")
            if key in {"MemTotal", "MemAvailable"}:
                number = rest.strip().split()[0]
                values[key] = int(number)
    except (OSError, ValueError):
        return {}
    return values


def _logs_text() -> str:
    candidates = [
        Path(os.getenv("OPENCLAW_TELEGRAM_LOG", "")),
        Path(os.getenv("OPENCLAW_LOG_DIR", "/var/log/openclaw")) / "openclaw-telegram-bot.log",
        Path("/var/log/openclaw/openclaw-gateway.log"),
    ]
    for path in candidates:
        if not str(path) or not path.exists() or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-20:]
        except OSError as exc:
            return f"Logs OpenClaw: no pude leer {path}: {exc}"
        redacted = [redact_text(line) for line in lines]
        return "Logs OpenClaw:\n" + "\n".join(redacted)[-3200:]
    return "Logs OpenClaw: sin archivo de log legible en rutas locales conocidas."


def _events_text(store: OpenClawStore) -> str:
    events = store.list_telegram_events(limit=5)
    voice_events = store.list_telegram_voice_events(limit=3)
    if not events and not voice_events:
        return "Eventos Telegram: sin eventos registrados."
    lines = ["Eventos Telegram recientes:"]
    for event in events:
        lines.append(
            f"- update={event.get('update_id')} chat={event.get('chat_id')} comando={event.get('command')} autorizado={event.get('authorized')}"
        )
    for item in voice_events:
        artifact = item.get("artifact", {})
        lines.append(
            f"- voz chat={artifact.get('chat_id')} provider={artifact.get('transcript_provider')} tts={artifact.get('tts_provider')}"
        )
    return "\n".join(lines)


def _approvals_text(store: OpenClawStore) -> str:
    approvals = store.list_pending_approvals()
    if not approvals:
        return "Aprobaciones OpenClaw: no hay APR pendientes."
    lines = ["Aprobaciones OpenClaw pendientes:"]
    for item in approvals[:8]:
        summary = str(item.get("diff_summary", "")).splitlines()
        first = summary[1] if len(summary) > 1 else (summary[0] if summary else "")
        lines.append(f"- {item.get('approval_id')} step={item.get('step_id_expected')} {first[:160]}")
    return "\n".join(lines)


def _asks_for_previous_scan_result(text: str, state: dict[str, Any]) -> bool:
    lowered = text.lower()
    asks_result = "resultado" in lowered and ("escaneo" in lowered or "scan" in lowered)
    return asks_result and bool(state.get("last_approval"))


def _routing_text(argument: str, *, repo_root: Path, store: OpenClawStore) -> dict[str, Any]:
    task = TaskEnvelope(
        task_id=f"TGM-ROUTE-{uuid4().hex[:8]}",
        title="Consulta de routing Telegram",
        domain="academico",
        objective=argument or "Consulta de modelo/routing",
        complexity="medium",
        risk_level="low",
        extra_context={"telegram_command": "modelo", "routing_only": True},
    )
    decision = route_task(task, load_domain_policies(repo_root), repo_root=repo_root, store=store)
    store.save_task(task, decision)
    return {
        "status": "routing_explained",
        "text": "\n".join(
            [
                "Modelo manual no persistente: OpenClaw usa routing automático.",
                f"provider={decision.provider} modo={decision.mode} clase={decision.model_class}",
                "Para tareas pesadas usa /investiga <pregunta>; para chat breve usa /chat <texto>.",
            ]
        ),
    }


def _latency_question_response(argument: str, *, profile: dict[str, str]) -> dict[str, Any] | None:
    normalized = _normalize_greeting_text(argument)
    latency_markers = (
        "tardo",
        "tardaste",
        "tardaron",
        "demora",
        "demoraste",
        "demoro",
        "demoraron",
        "latencia",
        "espera",
        "cola",
        "saturado",
        "saturada",
        "saturados",
        "saturadas",
        "tiempo de respuesta",
        "por que tard",
        "por que tan lento",
        "porque tard",
        "porque tan lento",
    )
    if not any(marker in normalized for marker in latency_markers):
        return None

    desktop_model = os.getenv("OPENCLAW_DESKTOP_COMPUTE_MODEL", "mistral-nemo:12b").strip() or "mistral-nemo:12b"
    lines = [
        "Fue lenta porque esta frase cae en la ruta de razonamiento, no en la ruta determinista.",
        f"Con la regla actual, el texto se parece a una consulta de reasoning y termina en `desktop_heavy` ({desktop_model}).",
        "Ese camino es más costoso y, si el desktop está ocupado o el modelo no está listo, la respuesta espera hasta agotar el SLA.",
        "Para evitar la regresión, las preguntas sobre demora, latencia, colas o saturación deben resolverse como `system_status` o `system_routing` sin invocar el LLM pesado.",
        f"Perfil observado: intent={profile.get('intent', 'desconocido')} request_kind={profile.get('request_kind', 'desconocido')} route_hint={profile.get('route_hint', 'desconocido')}.",
    ]
    return {"status": "ok", "text": "\n".join(lines), "model": "deterministic"}


def _approval_proposal(
    argument: str,
    *,
    repo_root: Path,
    store: OpenClawStore,
    source_command: str,
    chat_id: str,
    mutates_state: bool = False,
) -> dict[str, Any]:
    draft = _draft_command_for(argument)
    task = TaskEnvelope(
        task_id=f"TGM-TOOL-{uuid4().hex[:8]}",
        title="Propuesta Telegram no ejecutada",
        domain="administrativo",
        objective=argument,
        complexity="medium",
        risk_level="high",
        mutates_state=mutates_state,
        extra_context={"telegram_command": source_command, "safe_mode": True, "draft_command": draft, "chat_id": chat_id},
    )
    decision = route_task(task, load_domain_policies(repo_root), repo_root=repo_root, store=store)
    store.save_task(task, decision)
    diff_summary = "\n".join(
        [
            "Solicitud Telegram no ejecutada directamente.",
            f"Intencion: {argument[:200]}",
            "Riesgo: requiere autorizacion humana antes de usar herramientas no expuestas por Telegram.",
            f"Borrador de comando sugerido: {draft}",
        ]
    )
    approval_id = store.create_approval_request(
        task=task,
        decision=decision,
        diff_summary=diff_summary,
        affected_targets=[],
        step_id_expected="VAL-STEP-PENDING",
        evidence_source_required=True,
    )
    approval_hint = "Responde 'sí' para aprobar y ejecutar esta herramienta allowlist." if _is_image_draft(draft) else "Requiere validación humana con Step ID."
    return {
        "status": "approval_required",
        "approval_id": approval_id,
        "intent": argument,
        "draft_command": draft,
        "text": "\n".join(
            [
                "Acción no ejecutada en modo seguro.",
                f"Propuesta creada: {approval_id}",
                approval_hint,
                f"Borrador no ejecutado: {draft}",
            ]
        ),
    }


def _draft_command_for(argument: str) -> str:
    lowered = argument.lower()
    if "scan" in lowered or "escaneo" in lowered:
        return "nmap -sn <CIDR_autorizado>"
    if "imagen" in lowered or "genera" in lowered:
        prompt = _image_prompt_from_intent(argument, {})
        escaped = prompt.replace("'", "'\"'\"'")
        return f"openclaw-image-generate --prompt '{escaped}' --backend comfyui --pending-human-approval"
    if "equipo" in lowered or "caracter" in lowered:
        return "uname -a && lscpu && free -h && df -h"
    if any(marker in lowered for marker in MUTATION_MARKERS):
        return f"# revisar y ejecutar manualmente solo tras VAL-STEP: {argument[:160]}"
    return f"# herramienta no expuesta por Telegram: {argument[:160]}"


def _multipart_for_telegram(*, fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = f"----OpenClawTgBoundary{uuid4().hex}"
    chunks: list[bytes] = []
    for key, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        chunks.append(value.encode("utf-8"))
        chunks.append(b"\r\n")

    suffix = file_path.suffix.lower()
    mime = "application/octet-stream"
    if suffix == ".ogg":
        mime = "audio/ogg"
    elif suffix in {".mp3", ".mpeg"}:
        mime = "audio/mpeg"
    elif suffix == ".png":
        mime = "image/png"
    elif suffix in {".jpg", ".jpeg"}:
        mime = "image/jpeg"
    elif suffix == ".webp":
        mime = "image/webp"
    chunks.append(f"--{boundary}\r\n".encode("utf-8"))
    chunks.append(
        f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode("utf-8")
    )
    chunks.append(f"Content-Type: {mime}\r\n\r\n".encode("utf-8"))
    chunks.append(file_path.read_bytes())
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"
