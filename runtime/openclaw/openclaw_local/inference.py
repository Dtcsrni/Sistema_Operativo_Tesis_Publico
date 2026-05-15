from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any
from urllib import error, request

def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in {"1", "true", "yes", "on", "si", "sí"}

def _env_int(name: str, default: int, minimum: int = 1, maximum: int = 65535) -> int:
    try:
        val = int(os.getenv(name, str(default)))
        return max(minimum, min(val, maximum))
    except ValueError:
        return default

def _csv_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default).strip()
    return [item.strip() for item in raw.split(",") if item.strip()]

_WARMUP_DONE = False
_WARMUP_GUARD = threading.Lock()

def llamacpp_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120) -> tuple[bool, str]:
    # Usamos la API de chat/completions por defecto para maxima compatibilidad
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/v1/chat/completions"):
        if endpoint.endswith("/v1"):
            endpoint += "/chat/completions"
        else:
            endpoint += "/v1/chat/completions"

    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": _env_int("OPENCLAW_CHAT_HEAVY_MAX_TOKENS", 1024, minimum=64, maximum=4096),
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
    return (True, content) if content else (False, "llamacpp_empty_text")

def openai_compatible_generate(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: int = 120,
    api_key: str = "",
    provider_label: str = "openai_compatible",
) -> tuple[bool, str]:
    endpoint = base_url.rstrip("/")
    if not endpoint.endswith("/chat/completions"):
        if endpoint.endswith("/v1"):
            endpoint = endpoint + "/chat/completions"
        else:
            endpoint = endpoint + "/v1/chat/completions"
            
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
    if api_key:
        req.add_header("Authorization", f"Bearer {api_key}")
        
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            data = json.loads(response.read().decode("utf-8", errors="replace"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if hasattr(exc, "read") else str(exc)
        return False, f"{provider_label}_http_error:{detail[:220]}"
    except Exception as exc:
        return False, f"{provider_label}_unavailable:{type(exc).__name__}:{exc}"
        
    choices = data.get("choices") or []
    if not choices:
        return False, f"{provider_label}_empty_choices"
    message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
    content = str(message.get("content", "")).strip()
    return (True, content) if content else (False, f"{provider_label}_empty_text")

def gemini_api_generate(
    *,
    api_key: str,
    prompt: str,
    timeout_seconds: int = 60,
    model: str = "gemini-1.5-pro",
) -> tuple[bool, str]:
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = json.dumps(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": 2048,
            },
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
        return False, f"gemini_api_http_error:{detail[:220]}"
    except Exception as exc:
        return False, f"gemini_api_unavailable:{type(exc).__name__}:{exc}"

    candidates = data.get("candidates", [])
    if not candidates:
        return False, f"gemini_api_empty_candidates:{data.get('promptFeedback', 'no_feedback')}"
    
    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts:
        return False, "gemini_api_empty_parts"
    text = "\n".join(
        str(part.get("text", ""))
        for part in parts
        if isinstance(part, dict) and str(part.get("text", "")).strip()
    ).strip()
    if not text:
        return False, "gemini_api_empty_text"
    return True, text
    
def warmup_chat_models(repo_root: Path) -> dict[str, Any]:
    if not _env_flag("OPENCLAW_MODEL_WARMUP_ON_START", default=True):
        return {"status": "skipped", "reason": "disabled"}
    global _WARMUP_DONE
    with _WARMUP_GUARD:
        if _WARMUP_DONE:
            return {"status": "skipped", "reason": "already_done"}
        _WARMUP_DONE = True

    desktop_base = os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434")
    desktop_models = _csv_env("OPENCLAW_DESKTOP_WARMUP_MODELS", os.getenv("OPENCLAW_DESKTOP_COMPUTE_MODEL", "deepseek-r1:7b"))
    timeout_seconds = _env_int("OPENCLAW_MODEL_WARMUP_TIMEOUT", 45, minimum=5, maximum=180)
    results: list[dict[str, Any]] = []

    def warm(base_url: str, provider: str, model: str) -> None:
        if not model:
            return
        if "gemini" in model.lower():
            results.append({"provider": provider, "model": model, "status": "skipped", "detail": "cloud_provider_no_warmup_needed"})
            return
        
        # En el nuevo setup Docker con llama.cpp, el warmup es un simple ping a /health o un prompt vacio
        endpoint = base_url.rstrip("/") + "/health"
        try:
            with request.urlopen(endpoint, timeout=5) as response:
                if response.status == 200:
                    results.append({"provider": provider, "model": model, "status": "ok", "detail": "container_ready"})
                    return
        except Exception:
            pass
            
        # Fallback a un prompt minimo si /health no esta
        ok, detail = llamacpp_generate(base_url=base_url, model=model, prompt="ping", timeout_seconds=timeout_seconds)
        results.append({"provider": provider, "model": model, "status": "ok" if ok else "error", "detail": detail})

    if _env_flag("OPENCLAW_EDGE_WARMUP_ON_START", default=False) or _env_flag("OPENCLAW_EXPOSE_EDGE_AGENTS", default=False):
        edge_base = os.getenv("OPENCLAW_EDGE_INFERENCE_BASE_URL", os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
        edge_models = _csv_env("OPENCLAW_WARMUP_MODELS", os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b"))
        for model in edge_models:
            warm(edge_base, "edge_inference", model)
    if _env_flag("OPENCLAW_DESKTOP_COMPUTE_ENABLED", default=True):
        for model in desktop_models:
            warm(desktop_base, "desktop_compute", model)
    return {"status": "ok", "results": results}
