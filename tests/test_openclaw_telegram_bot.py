from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "runtime" / "openclaw"

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from openclaw_local.storage import OpenClawStore  # noqa: E402
from openclaw_local.telegram_bot import _chat_request_profile, _chat_state_key, _is_greeting, _normalize_research_response, _process_update_safe, dispatch_command, handle_update, parse_command, web_search  # noqa: E402


def _write_domain_envs(tmp_path: Path) -> Path:
    domains_dir = tmp_path / "domains"
    domains_dir.mkdir()
    (domains_dir / "personal.env").write_text("", encoding="utf-8")
    (domains_dir / "profesional.env").write_text("", encoding="utf-8")
    (domains_dir / "academico.env").write_text("", encoding="utf-8")
    (domains_dir / "edge.env").write_text("", encoding="utf-8")
    (domains_dir / "administrativo.env").write_text("", encoding="utf-8")
    return domains_dir


def test_parse_command_defaults_to_chat() -> None:
    assert parse_command("hola") == ("chat", "hola")
    assert parse_command("/estado") == ("estado", "")
    assert parse_command("/chat@OpenClawBot hola") == ("chat", "hola")


def test_is_greeting_detects_mexican_variants() -> None:
    assert _is_greeting("qué onda")
    assert _is_greeting("que onda compa")
    assert _is_greeting("órale pues")
    assert _is_greeting("buenas tardes, banda")
    assert _is_greeting("quiubo")
    assert not _is_greeting("qué onda con el servicio")


def test_unauthorized_chat_is_ignored_and_audited(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_ID", "6866872051")
    store = OpenClawStore(tmp_path / "openclaw.db")
    payload = handle_update(
        {
            "update_id": 10,
            "message": {"chat": {"id": 1}, "text": "/estado"},
        },
        repo_root=ROOT,
        store=store,
    )

    assert payload["status"] == "ignored"
    assert payload["reply_sent"] is False
    events = store.list_telegram_events()
    assert events[0]["authorized"] is False
    assert events[0]["command"] == "estado"


def test_status_command_reports_chat_provider_and_model(tmp_path: Path, monkeypatch) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")

    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4")
    monkeypatch.setattr("openclaw_local.telegram_bot.probe_runtime_status", lambda repo_root: {"active_runtime": "ollama_local", "state": "npu_experimental_ready"})
    monkeypatch.setattr("openclaw_local.telegram_bot.build_preflight_report", lambda repo_root: {"status": "ok"})
    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", lambda base_url: (True, ["mistral-nemo:12b"]))

    payload = dispatch_command("estado", "", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert "runtime=ollama_local state=npu_experimental_ready" in payload["text"]
    assert "chat_provider=web_session chat_model=gpt-5.4" in payload["text"]


def test_status_command_reports_last_fallback_reason(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    monkeypatch.setattr("openclaw_local.telegram_bot.probe_runtime_status", lambda repo_root: {"active_runtime": "ollama_local", "state": "ready"})
    monkeypatch.setattr("openclaw_local.telegram_bot.build_preflight_report", lambda repo_root: {"status": "ok"})
    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", lambda base_url: (True, ["qwen3:4b"]))

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        return False, "modelo_no_disponible:http_500:timeout upstream"

    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)

    chat_payload = dispatch_command("chat", "dame una respuesta breve", repo_root=ROOT, store=store)
    status_payload = dispatch_command("estado", "", repo_root=ROOT, store=store)

    assert chat_payload["status"] == "model_error"
    assert "request_traces=1" in status_payload["text"]
    assert "last_fallback_reason=all_candidates_failed" in status_payload["text"]
    assert "last_trace_model=none" in status_payload["text"] or "last_trace_model=qwen3:4b" in status_payload["text"]


def test_status_command_reports_last_backend_busy(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_DESKTOP_COMPUTE_ENABLED", "1")
    store = OpenClawStore(tmp_path / "openclaw.db")

    class _BusySemaphore:
        def acquire(self, blocking: bool = False) -> bool:
            return False

        def release(self) -> None:
            return None

    def fake_backend_semaphore(candidate):
        return _BusySemaphore()

    def fake_list_ollama_models(base_url: str):
        if "21434" in base_url:
            return True, ["mistral-nemo:12b"]
        return False, []

    def fail_generate(**_: object):
        raise AssertionError("backend_busy should skip Ollama execution")

    monkeypatch.setattr("openclaw_local.telegram_bot._backend_semaphore", fake_backend_semaphore)
    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", fake_list_ollama_models)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fail_generate)
    monkeypatch.setattr("openclaw_local.telegram_bot.probe_runtime_status", lambda repo_root: {"active_runtime": "ollama_local", "state": "ready"})
    monkeypatch.setattr("openclaw_local.telegram_bot.build_preflight_report", lambda repo_root: {"status": "ok"})

    chat_payload = dispatch_command("chat", "dame una respuesta breve", repo_root=ROOT, store=store)
    status_payload = dispatch_command("estado", "", repo_root=ROOT, store=store)

    assert chat_payload["status"] == "model_error"
    assert "last_backend_busy=desktop_compute:mistral-nemo:12b" in status_payload["text"]
    assert "count=1" in status_payload["text"]


def test_tool_mutation_creates_approval_without_execution(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    payload = dispatch_command("herramienta", "reinicia openclaw-gateway", repo_root=ROOT, store=store)

    assert payload["status"] == "approval_required"
    assert "APR-TGM-TOOL" in payload["text"]
    approvals = store.list_pending_approvals()
    assert len(approvals) == 1
    assert "reinicia openclaw-gateway" in approvals[0]["diff_summary"]


def test_research_uses_desktop_and_degrades_to_edge(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_DESKTOP_COMPUTE_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")
    store = OpenClawStore(tmp_path / "openclaw.db")
    calls: list[tuple[str, str]] = []

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        calls.append((base_url, model))
        assert "Evidencia web read-only" in prompt
        if "21434" in base_url:
            return False, "desktop caido"
        return True, "respuesta edge"

    def fake_list_ollama_models(base_url: str):
        if "21434" in base_url:
            return True, ["qwen3:14b", "mistral-nemo:12b"]
        return True, ["qwen3:4b", "gemma3:4b"]

    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", fake_list_ollama_models)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)
    monkeypatch.setattr(
        "openclaw_local.telegram_bot.web_search",
        lambda query: {"status": "ok", "results": [{"title": "Fuente A", "url": "https://example.test/a", "snippet": "Dato"}]},
    )

    payload = dispatch_command("investiga", "comparar modelos locales", repo_root=ROOT, store=store)

    assert payload["status"] == "degraded"
    assert "respuesta edge" in payload["text"]
    assert "https://example.test/a" in payload["text"]
    assert calls[0][0].endswith(":21434")
    assert calls[1][1] == "qwen3:4b"
    assert store.audit_summary()["tasks"] == 1


def test_knowledge_chat_falls_back_to_web_evidence_when_model_is_unsupported(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_DESKTOP_COMPUTE_ENABLED", "0")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")
    store = OpenClawStore(tmp_path / "openclaw.db")

    monkeypatch.setattr(
        "openclaw_local.telegram_bot.web_search",
        lambda query, **kwargs: {
            "status": "ok",
            "endpoint": "https://html.duckduckgo.com/html/?q=hidalgo",
            "results": [
                {
                    "title": "PDF Descripción General Del Estado De Hidalgo",
                    "url": "https://www.cambioclimatico.semarnath.gob.mx/webFiles/pagesFiles/13DescripcionEH.pdf",
                    "snippet": "El Estado de Hidalgo forma parte de la región centro-oriental de México.",
                },
                {"title": "Hidalgo, el estado", "url": "https://example.test/hidalgo-2", "snippet": "Capital: Pachuca"},
            ],
        },
    )
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", lambda **kwargs: (True, "el hidalgo es un género de árboles y plantas"))

    payload = dispatch_command("chat", "qué es hidalgo?", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert "unknown" not in payload["model"]
    assert "web_evidence" not in payload["model"]
    assert "evidencia_web" in payload["model"]
    assert "No encontré una definición confiable" in payload["text"]
    assert "Interpretación más probable" in payload["text"]
    assert "Contexto de la evidencia" in payload["text"]
    assert "[institucional]" in payload["text"]
    assert "semarnath.gob.mx" in payload["text"]


def test_chat_resumelo_uses_local_memory_without_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")
    store.cache_context(
        _chat_state_key("demo-state"),
        {
            "turns": [
                {"command": "chat", "user": "Primera consulta", "status": "ok"},
                {"command": "chat", "user": "Segunda consulta", "status": "ok"},
            ],
            "rolling_summary": "Se habló de OpenClaw, resumen y conversiones.",
            "call_mode": {"enabled": False, "style": "estable"},
        },
    )
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", lambda **kwargs: (_ for _ in ()).throw(AssertionError("no debe llamar al modelo")))

    payload = dispatch_command("chat", "Resumelo", repo_root=ROOT, store=store, chat_id="demo-state")

    assert payload["status"] == "context_recalled"
    assert "Memoria de esta sesión" in payload["text"]
    assert "Se habló de OpenClaw" in payload["text"]


def test_chat_converts_pounds_to_kg_without_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", lambda **kwargs: (_ for _ in ()).throw(AssertionError("no debe llamar al modelo")))

    payload = dispatch_command("chat", "Convierte 25 libras a kg", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert "Conversión directa" in payload["text"]
    assert "25.00 libras equivalen a 11.34 kg" in payload["text"]
    assert "0.45359237" in payload["text"]


def test_research_response_normalizes_required_headings() -> None:
    payload = _normalize_research_response("Hallazgos:\n- A\nSupuestos:\n- B\nRiesgos:\n- C\nSiguientes pasos:\n- D")

    assert "hallazgos:" in payload
    assert "supuestos:" in payload
    assert "riesgos:" in payload
    assert "siguientes pasos:" in payload


def test_chat_uses_edge_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")
    store = OpenClawStore(tmp_path / "openclaw.db")
    model_calls: list[tuple[str, str]] = []

    def fake_list_ollama_models(base_url: str):
        if "21434" in base_url:
            return True, ["qwen3:14b", "mistral-nemo:12b"]
        return True, ["qwen3:4b", "gemma3:4b"]

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        model_calls.append((base_url, model))
        return True, f"ok {model}"

    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", fake_list_ollama_models)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)

    payload = dispatch_command("chat", "dame una respuesta breve", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert model_calls[0][0].endswith(":11434")
    assert model_calls[0][1] == "qwen3:4b"
    assert "ok qwen3:4b" in payload["text"]


def test_chat_uses_chatgpt_plus_only_when_explicitly_requested(tmp_path: Path, monkeypatch) -> None:
    domains_dir = _write_domain_envs(tmp_path)
    (domains_dir / "academico.env").write_text("OPENCLAW_CHATGPT_PLUS_ENABLED=1\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(domains_dir))
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "openai")
    store = OpenClawStore(tmp_path / "openclaw.db")
    openai_calls: list[str] = []

    def fake_openai_chat_generate(prompt: str, *, timeout_seconds: int = 120):
        openai_calls.append(prompt)
        return True, "respuesta chatgpt", "gpt-5.4"

    def fail_ollama_generate(**_: object):
        raise AssertionError("OpenClaw no debe caer a Ollama cuando ChatGPT Plus responde")

    monkeypatch.setattr("openclaw_local.telegram_bot._openai_chat_generate", fake_openai_chat_generate)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fail_ollama_generate)

    payload = dispatch_command("chat", "usa ChatGPT Plus para responder hola", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert openai_calls
    assert "respuesta chatgpt" in payload["text"]


def test_chat_greeting_uses_deterministic_sla_response(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    monkeypatch.setattr(
        "openclaw_local.telegram_bot._chat_request_profile",
        lambda argument, **kwargs: {
            "intent": "greeting",
            "request_kind": "standard",
            "complexity": "low",
            "confidence": "0.99",
            "route_hint": "deterministic_local",
            "semantic_status": "ok",
        },
    )

    payload = dispatch_command("chat", "hola", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert payload["model"] == "deterministic"
    assert "OpenClaw Edge" in payload["text"]


def test_chat_request_profile_uses_semantic_classifier(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_CHAT_FORCE_SEMANTIC", "1")
    calls: list[tuple[str, str]] = []

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        calls.append((base_url, model))
        payload = {
            "intent": "system_status",
            "request_kind": "system",
            "complexity": "low",
            "confidence": 0.98,
            "route_hint": "deterministic_local",
            "rationale": "consulta de estado operativo",
        }
        return True, json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", lambda base_url: (True, ["qwen3:4b"]))
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)

    profile = _chat_request_profile("dame datos del sistema", repo_root=ROOT)

    assert calls
    assert calls[0][1] == "qwen3:4b"
    assert profile["intent"] == "system_status"
    assert profile["request_kind"] == "system"
    assert profile["semantic_status"] == "ok"


def test_chat_request_profile_uses_cached_semantic_result(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_CHAT_FORCE_SEMANTIC", "1")
    store = OpenClawStore(tmp_path / "openclaw.db")
    calls = {"count": 0}

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        calls["count"] += 1
        payload = {
            "intent": "system_status",
            "request_kind": "system",
            "complexity": "low",
            "confidence": 0.98,
            "route_hint": "deterministic_local",
            "rationale": "consulta de estado operativo",
        }
        return True, json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", lambda base_url: (True, ["qwen3:4b"]))
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)

    first = _chat_request_profile("dame datos del sistema", repo_root=ROOT, store=store, chat_id="123")
    second = _chat_request_profile("dame datos del sistema", repo_root=ROOT, store=store, chat_id="123")

    assert first["intent"] == "system_status"
    assert second["intent"] == "system_status"
    assert second["semantic_status"] == "cached"
    assert calls["count"] == 1


def test_chat_system_data_uses_semantic_deterministic_status(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    monkeypatch.setattr(
        "openclaw_local.telegram_bot._chat_request_profile",
        lambda argument, **kwargs: {
            "intent": "system_status",
            "request_kind": "system",
            "complexity": "low",
            "confidence": "0.98",
            "route_hint": "deterministic_local",
            "semantic_status": "ok",
        },
    )

    def fail_generate(**_: object):
        raise AssertionError("datos del sistema no debe cargar modelos")

    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fail_generate)

    payload = dispatch_command("chat", "dame datos del sistema", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert payload["model"] == "deterministic"
    assert "Estado OpenClaw:" in payload["text"]


def test_chat_uses_web_session_when_configured(tmp_path: Path, monkeypatch) -> None:
    domains_dir = _write_domain_envs(tmp_path)
    (domains_dir / "academico.env").write_text("OPENCLAW_CHATGPT_PLUS_ENABLED=1\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(domains_dir))
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4")
    store = OpenClawStore(tmp_path / "openclaw.db")
    web_calls: list[str] = []

    def fake_web_session(prompt: str, *, timeout_seconds: int = 180):
        web_calls.append(prompt)
        return True, "respuesta desde sesion web", "gpt-5.4"

    def fail_ollama_generate(**_: object):
        raise AssertionError("no debe caer a Ollama cuando la sesión web funciona")

    monkeypatch.setattr("openclaw_local.telegram_bot.generate_web_session_response", fake_web_session)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fail_ollama_generate)

    payload = dispatch_command("chat", "usa ChatGPT en la nube para responder hola", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert web_calls
    assert "respuesta desde sesion web" in payload["text"]


def test_chat_falls_back_from_web_session_to_api_direct(tmp_path: Path, monkeypatch) -> None:
    domains_dir = _write_domain_envs(tmp_path)
    (domains_dir / "academico.env").write_text("OPENCLAW_CHATGPT_PLUS_ENABLED=1\nOPENAI_API_KEY=openai-acad\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(domains_dir))
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_MODEL", "gpt-5.4")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    store = OpenClawStore(tmp_path / "openclaw.db")
    web_calls: list[str] = []
    openai_calls: list[str] = []

    def fake_web_session(prompt: str, *, timeout_seconds: int = 180):
        web_calls.append(prompt)
        return False, "web_session_timeout:test", ""

    def fake_openai_chat_generate(prompt: str, *, timeout_seconds: int = 120):
        openai_calls.append(prompt)
        return True, "respuesta API directa", "gpt-5.4"

    def fail_ollama_generate(**_: object):
        raise AssertionError("no debe caer a Ollama si la API directa resuelve el fallback")

    monkeypatch.setattr("openclaw_local.telegram_bot.generate_web_session_response", fake_web_session)
    monkeypatch.setattr("openclaw_local.telegram_bot._openai_chat_generate", fake_openai_chat_generate)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fail_ollama_generate)

    payload = dispatch_command("chat", "usa ChatGPT para responder hola", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert web_calls
    assert openai_calls
    assert "respuesta API directa" in payload["text"]


def test_chat_does_not_auto_promote_to_chatgpt_plus_when_enabled(tmp_path: Path, monkeypatch) -> None:
    domains_dir = _write_domain_envs(tmp_path)
    (domains_dir / "academico.env").write_text("OPENCLAW_CHATGPT_PLUS_ENABLED=1\nOPENAI_API_KEY=openai-acad\n", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(domains_dir))
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_PROVIDER", "web_session")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")
    store = OpenClawStore(tmp_path / "openclaw.db")
    model_calls: list[tuple[str, str]] = []

    def fail_web_session(*args, **kwargs):
        raise AssertionError("ChatGPT Plus no debe usarse sin solicitud explícita")

    def fake_list_ollama_models(base_url: str):
        return True, ["qwen3:4b", "gemma3:4b"]

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        model_calls.append((base_url, model))
        return True, f"respuesta local {model}"

    monkeypatch.setattr("openclaw_local.telegram_bot.generate_web_session_response", fail_web_session)
    monkeypatch.setattr("openclaw_local.telegram_bot._openai_chat_generate", fail_web_session)
    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", fake_list_ollama_models)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)

    payload = dispatch_command("chat", "dame una respuesta breve", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert model_calls
    assert model_calls[-1] == ("http://127.0.0.1:11434", "qwen3:4b")
    assert "respuesta local qwen3:4b" in payload["text"]


def test_chat_semantic_fallback_excludes_qwen2_5_half_b(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")
    monkeypatch.setenv("OPENCLAW_DESKTOP_COMPUTE_ENABLED", "0")
    store = OpenClawStore(tmp_path / "openclaw.db")
    model_calls: list[str] = []

    def fake_list_ollama_models(base_url: str):
        return True, ["qwen3:4b", "gemma3:4b", "qwen2.5:0.5b"]

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        model_calls.append(model)
        return False, "modelo_no_disponible:http_500:timeout upstream"

    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", fake_list_ollama_models)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)

    payload = dispatch_command("chat", "dame una respuesta breve", repo_root=ROOT, store=store)

    assert payload["status"] == "model_error"
    assert "qwen2.5:0.5b" not in model_calls
    assert "Sistemas de inferencia saturados" in payload["text"]
    assert "borde recomendado" in payload["text"]


def test_web_search_falls_back_to_http_endpoint(monkeypatch) -> None:
    class _FakeResponse:
        def __init__(self, body: str):
            self._body = body.encode("utf-8")

        def read(self):
            return self._body

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    calls: list[str] = []

    def fake_urlopen(req, timeout=0):
        url = req.full_url
        calls.append(url)
        if url.startswith("https://"):
            raise OSError("https blocked")
        html = (
            '<a class="result__a" href="https://example.test/nota">Definicion teocalli</a>'
            '<div class="result__snippet">Templo ceremonial mexica</div>'
        )
        return _FakeResponse(html)

    monkeypatch.setattr("openclaw_local.telegram_bot.request.urlopen", fake_urlopen)

    result = web_search("que es un teocalli", timeout_seconds=2, limit=3)

    assert result["status"] == "ok"
    assert result["endpoint"].startswith("http://")
    assert result["results"]
    assert any(item["endpoint"].startswith("https://html.duckduckgo.com/html/") for item in result["attempts"])
    assert any(item["endpoint"].startswith("https://duckduckgo.com/lite/") for item in result["attempts"])
    assert any(item["endpoint"].startswith("http://html.duckduckgo.com/html/") for item in result["attempts"])
    assert any(url.startswith("https://") for url in calls)


def test_web_search_returns_error_when_all_endpoints_fail(monkeypatch) -> None:
    def fake_urlopen(req, timeout=0):
        raise OSError("network down")

    monkeypatch.setattr("openclaw_local.telegram_bot.request.urlopen", fake_urlopen)

    result = web_search("teocalli", timeout_seconds=1, limit=2)

    assert result["status"] == "error"
    assert "web_unavailable" in result["error"]
    assert result["attempts"]


def test_chat_outcome_records_structured_trace_fields(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")
    store = OpenClawStore(tmp_path / "openclaw.db")

    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", lambda base_url: (True, ["qwen3:4b"]))
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", lambda **kwargs: (True, "ok estructurado"))

    payload = dispatch_command("chat", "dame una respuesta breve", repo_root=ROOT, store=store)
    outcomes = store.list_task_outcomes(limit=1)
    outcome_payload = outcomes[0]["payload"]
    traces = store.list_request_traces(limit=1)

    assert payload["status"] == "ok"
    assert outcome_payload["request_kind"] == "standard"
    assert outcome_payload["trace_id"].startswith("CHAT-")
    assert outcome_payload["fallback_policy"] == "semantic_fallback_edge_recommended"
    assert outcome_payload["candidate_models"]
    assert traces
    assert traces[0]["trace_id"].startswith("CHAT-")
    assert traces[0]["prompt_tokens_est"] >= 1


def test_process_update_serializes_updates_per_chat(tmp_path: Path, monkeypatch) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")
    sequence: list[tuple[str, int, float]] = []
    guard = threading.Lock()

    def fake_handle_update(update, *, repo_root, store):
        update_id = int(update["update_id"])
        with guard:
            sequence.append(("start", update_id, time.perf_counter()))
        time.sleep(0.05)
        with guard:
            sequence.append(("end", update_id, time.perf_counter()))
        return {"status": "ok"}

    monkeypatch.setattr("openclaw_local.telegram_bot.handle_update", fake_handle_update)

    updates = [
        {"update_id": 1, "message": {"chat": {"id": 42}, "text": "hola"}},
        {"update_id": 2, "message": {"chat": {"id": 42}, "text": "hola 2"}},
    ]
    threads = [threading.Thread(target=_process_update_safe, args=(update, ROOT, store)) for update in updates]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=2)

    assert [item[0] for item in sequence] == ["start", "end", "start", "end"]


def test_chat_falls_back_to_edge_when_desktop_models_are_unavailable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")
    store = OpenClawStore(tmp_path / "openclaw.db")

    def fake_list_ollama_models(base_url: str):
        if "21434" in base_url:
            return False, []
        return True, ["qwen3:4b", "gemma3:4b"]

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        return True, f"ok {model}"

    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", fake_list_ollama_models)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)

    payload = dispatch_command("chat", "dame una respuesta breve", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert "ok qwen3:4b" in payload["text"]


def test_chat_escalates_to_desktop_for_heavy_requests_and_sends_typing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_DESKTOP_COMPUTE_ENABLED", "1")
    store = OpenClawStore(tmp_path / "openclaw.db")
    typing_calls: list[tuple[str, str]] = []
    model_calls: list[tuple[str, str]] = []

    def fake_send_chat_action(chat_id: str, action: str = "typing"):
        typing_calls.append((chat_id, action))
        return {"status": "sent", "detail": "ok"}

    def fake_list_ollama_models(base_url: str):
        if "21434" in base_url:
            return True, ["qwen2.5-coder:14b", "mistral-nemo:12b", "phi4:14b"]
        return True, ["qwen3:4b", "gemma3:4b"]

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        model_calls.append((base_url, model))
        return True, f"ok {model}"

    monkeypatch.setattr("openclaw_local.telegram_bot.send_chat_action", fake_send_chat_action)
    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", fake_list_ollama_models)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)

    payload = dispatch_command("chat", "revisa este bug en el script de Python y corrige el error", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert typing_calls
    assert typing_calls[0] == ("cli", "typing")
    assert model_calls[-1][0].endswith(":21434")
    assert model_calls[-1][1] == "qwen2.5-coder:14b"
    assert "qwen2.5-coder:14b" in payload["text"]


def test_chat_latency_question_is_answered_deterministically_without_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    def fail_generate(**_: object):
        raise AssertionError("latency questions should not call Ollama")

    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fail_generate)

    payload = dispatch_command("chat", "¿por qué tardaste tanto en esa respuesta?", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert payload["model"] == "deterministic"
    assert "desktop_heavy" in payload["text"]
    assert "SLA" in payload["text"]


def test_chat_skips_busy_desktop_backend_and_uses_edge_fallback(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    monkeypatch.setenv("OPENCLAW_DESKTOP_COMPUTE_ENABLED", "1")
    store = OpenClawStore(tmp_path / "openclaw.db")
    model_calls: list[tuple[str, str]] = []

    class _FakeSemaphore:
        def __init__(self, allow: bool):
            self.allow = allow

        def acquire(self, blocking: bool = False) -> bool:
            return self.allow

        def release(self) -> None:
            return None

    def fake_backend_semaphore(candidate):
        return _FakeSemaphore(candidate.provider != "desktop_compute")

    def fake_list_ollama_models(base_url: str):
        if "21434" in base_url:
            return True, ["qwen2.5-coder:14b", "mistral-nemo:12b", "phi4:14b"]
        return True, ["qwen3:4b", "gemma3:4b"]

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        model_calls.append((base_url, model))
        return True, f"ok {model}"

    monkeypatch.setattr("openclaw_local.telegram_bot._backend_semaphore", fake_backend_semaphore)
    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", fake_list_ollama_models)
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)

    payload = dispatch_command("chat", "revisa este bug en el script de Python y corrige el error", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert model_calls == [("http://127.0.0.1:11434", "qwen3:4b")]
    assert "ok qwen3:4b" in payload["text"]


def test_chat_memory_recalls_scan_proposal_without_execution(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    scan = dispatch_command("chat", "Scan", repo_root=ROOT, store=store, chat_id="123")
    followup = dispatch_command("chat", "Resultado del escaneo?", repo_root=ROOT, store=store, chat_id="123")

    assert scan["status"] == "approval_required"
    assert "Borrador no ejecutado: nmap -sn <CIDR_autorizado>" in scan["text"]
    assert followup["status"] == "context_recalled"
    assert "no se ejecutó ningún escaneo" in followup["text"]
    assert scan["approval_id"] in followup["text"]


def test_time_command_uses_ntp_without_ollama(tmp_path: Path, monkeypatch) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")

    def fail_generate(**_: object):
        raise AssertionError("hora no debe llamar a Ollama")

    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fail_generate)
    monkeypatch.setattr("openclaw_local.telegram_bot._query_ntp_time", lambda server: None)

    payload = dispatch_command("hora", "", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert "fuente=reloj_local_fallback" in payload["text"]
    assert "pachuca=" in payload["text"]


def test_research_declares_local_without_web_when_search_fails(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        return True, "hallazgos:\n- análisis local\nsupuestos:\n- sin web\nriesgos:\n- limitado\nsiguientes pasos:\n- verificar"

    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)
    monkeypatch.setattr("openclaw_local.telegram_bot.web_search", lambda query: {"status": "error", "error": "web_unavailable:test"})

    payload = dispatch_command("investiga", "hora actual en Pachuca", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert "modo=investigacion_local_sin_web" in payload["text"]
    assert "sin_web: web_unavailable:test" in payload["text"]


def test_model_request_uses_routing_explanation_without_persistent_switch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    monkeypatch.setattr(
        "openclaw_local.telegram_bot._chat_request_profile",
        lambda argument, **kwargs: {
            "intent": "general_chat",
            "request_kind": "standard",
            "complexity": "low",
            "confidence": "0.60",
            "route_hint": "model_local",
            "semantic_status": "ok",
        },
    )

    payload = dispatch_command("chat", "Ejecuta con mistral nemo", repo_root=ROOT, store=store)

    assert payload["status"] == "routing_explained"
    assert "routing automático" in payload["text"]
    assert "provider=" in payload["text"]


def test_modelos_with_argument_is_treated_as_routing_request(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    def fail_generate(**_: object):
        raise AssertionError("/modelos con argumento no debe llamar a Ollama")

    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fail_generate)

    payload = dispatch_command("modelos", "implementa solo qwen3 para chat breve", repo_root=ROOT, store=store)

    assert payload["status"] == "routing_explained"
    assert "routing automático" in payload["text"]


def test_research_followup_reuses_previous_topic(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")
    prompts: list[str] = []

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        prompts.append(prompt)
        return True, "hallazgos:\n- ok\nsupuestos:\n- ninguno\nriesgos:\n- bajo\nsiguientes pasos:\n- verificar"

    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)
    monkeypatch.setattr("openclaw_local.telegram_bot.web_search", lambda query: {"status": "ok", "results": [{"title": "Tezcatlipoca", "url": "https://example.test/t", "snippet": "Tezcatlipoca"}]})

    dispatch_command("chat", "Quiero saber de Tezcatlipoca", repo_root=ROOT, store=store, chat_id="42")
    payload = dispatch_command("investiga", "investígalo", repo_root=ROOT, store=store, chat_id="42")

    assert payload["status"] == "ok"
    assert "Tezcatlipoca" in prompts[-1]


def test_research_followup_ignores_mexican_greeting_as_prior_context(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")
    prompts: list[str] = []

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        prompts.append(prompt)
        return True, "hallazgos:\n- ok\nsupuestos:\n- ninguno\nriesgos:\n- bajo\nsiguientes pasos:\n- verificar"

    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)
    monkeypatch.setattr("openclaw_local.telegram_bot.web_search", lambda query: {"status": "ok", "results": [{"title": "Fuente A", "url": "https://example.test/a", "snippet": "Dato"}]})

    dispatch_command("chat", "Tezcatlipoca y su simbolismo", repo_root=ROOT, store=store, chat_id="42")
    dispatch_command("chat", "qué onda compa", repo_root=ROOT, store=store, chat_id="42")
    payload = dispatch_command("investiga", "investígalo", repo_root=ROOT, store=store, chat_id="42")

    assert payload["status"] == "ok"
    assert "qué onda compa" not in prompts[-1]


def test_ambiguous_tools_create_approval_with_draft(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    image = dispatch_command("herramienta", "genera una imagen", repo_root=ROOT, store=store)
    scan = dispatch_command("herramienta", "scan red local", repo_root=ROOT, store=store)

    assert image["status"] == "approval_required"
    assert "openclaw-image-generate" in image["text"]
    assert scan["status"] == "approval_required"
    assert "nmap -sn <CIDR_autorizado>" in scan["text"]
    approvals = store.list_pending_approvals()
    assert len(approvals) == 2
    assert all("Borrador de comando sugerido" in item["diff_summary"] for item in approvals)


def test_yes_approves_latest_image_apr_and_executes_allowlisted_tool(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    image_path = tmp_path / "tezcatlipoca.png"
    image_path.write_bytes(b"png")
    store = OpenClawStore(tmp_path / "openclaw.db")
    prompts: list[str] = []

    def fake_image(prompt: str, *, timeout_seconds: int = 120):
        prompts.append(prompt)
        return {"status": "ok", "backend": "comfyui", "path": str(image_path)}

    monkeypatch.setattr("openclaw_local.telegram_bot.generate_image_from_prompt", fake_image)

    proposal = dispatch_command("chat", "Genera una imagen de Tezcatlipoca, un dibujo", repo_root=ROOT, store=store, chat_id="42")
    approved = dispatch_command("chat", "sí", repo_root=ROOT, store=store, chat_id="42")

    assert proposal["status"] == "approval_required"
    assert approved["status"] == "ok_image"
    assert approved["image_path"] == str(image_path)
    assert "Tezcatlipoca" in prompts[-1]
    assert store.list_pending_approvals() == []


def test_image_backend_unavailable_is_clear_and_keeps_apr_pending(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    monkeypatch.setattr(
        "openclaw_local.telegram_bot.generate_image_from_prompt",
        lambda prompt: {"status": "unavailable", "backend": "comfyui", "error": "comfyui_unreachable"},
    )

    proposal = dispatch_command("chat", "genera una imagen de Tezcatlipoca", repo_root=ROOT, store=store, chat_id="42")
    approved = dispatch_command("chat", "valido", repo_root=ROOT, store=store, chat_id="42")

    assert proposal["status"] == "approval_required"
    assert approved["status"] == "image_backend_unavailable"
    assert "comfyui_unreachable" in approved["text"]
    assert len(store.list_pending_approvals()) == 1


def test_forget_natural_clears_pending_intention(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    dispatch_command("chat", "genera una imagen de Tezcatlipoca", repo_root=ROOT, store=store, chat_id="42")
    forgotten = dispatch_command("chat", "olvídalo", repo_root=ROOT, store=store, chat_id="42")
    approved = dispatch_command("chat", "sí", repo_root=ROOT, store=store, chat_id="42")

    assert forgotten["status"] == "forgotten"
    assert approved["status"] == "approval_not_found"


def test_memory_and_command_help_are_deterministic(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    dispatch_command("herramienta", "modelos", repo_root=ROOT, store=store, chat_id="123")
    examples = dispatch_command("chat", "Ejemplos con acción?", repo_root=ROOT, store=store, chat_id="123")
    memory = dispatch_command("chat", "Que hemos tratado en esta conversación?", repo_root=ROOT, store=store, chat_id="123")

    assert examples["status"] == "ok"
    assert "/herramienta estado" in examples["text"]
    assert memory["status"] == "context_recalled"
    assert "herramienta" in memory["text"]


def test_learning_preferences_are_injected_into_chat_prompt(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")
    prompts: list[str] = []

    learned = dispatch_command("aprender", "prefiero respuestas breves", repo_root=ROOT, store=store, chat_id="42")

    def fake_generate(*, base_url: str, model: str, prompt: str, timeout_seconds: int = 120):
        prompts.append(prompt)
        return True, "ok"

    monkeypatch.setattr("openclaw_local.telegram_bot.list_ollama_models", lambda base_url: (True, ["qwen3:4b"]))

    monkeypatch.setattr(
        "openclaw_local.telegram_bot._chat_request_profile",
        lambda argument, **kwargs: {
            "intent": "reasoning",
            "request_kind": "reasoning",
            "complexity": "high",
            "confidence": "0.91",
            "route_hint": "model_desktop",
            "semantic_status": "ok",
        },
    )
    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fake_generate)
    chat = dispatch_command("chat", "explica estado", repo_root=ROOT, store=store, chat_id="42")
    memory = dispatch_command("memoria", "", repo_root=ROOT, store=store, chat_id="42")

    assert learned["status"] == "learned"
    assert chat["status"] == "ok"
    assert "prefiero respuestas breves" in prompts[-1]
    assert "prefiero respuestas breves" in memory["text"]


def test_natural_time_question_is_deterministic_and_skips_ollama(tmp_path: Path, monkeypatch) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")
    monkeypatch.setattr(
        "openclaw_local.telegram_bot._chat_request_profile",
        lambda argument, **kwargs: {
            "intent": "time",
            "request_kind": "system",
            "complexity": "low",
            "confidence": "0.99",
            "route_hint": "deterministic_local",
            "semantic_status": "ok",
        },
    )
    monkeypatch.setattr("openclaw_local.telegram_bot._query_ntp_time", lambda server: None)

    payload = dispatch_command("chat", "¿Qué hora es en Pachuca?", repo_root=ROOT, store=store, chat_id="42")

    assert payload["status"] == "ok"
    assert "Hora OpenClaw:" in payload["text"]
    assert "pachuca=" in payload["text"]


def test_read_only_tool_memory_uses_current_chat_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    dispatch_command("aprender", "prefiero contexto acumulado", repo_root=ROOT, store=store, chat_id="real-chat")
    cli_memory = dispatch_command("herramienta", "memoria", repo_root=ROOT, store=store, chat_id="cli")
    real_memory = dispatch_command("herramienta", "memoria", repo_root=ROOT, store=store, chat_id="real-chat")

    assert "prefiero contexto acumulado" not in cli_memory["text"]
    assert "prefiero contexto acumulado" in real_memory["text"]


def test_read_only_equipo_tool_does_not_call_ollama(tmp_path: Path, monkeypatch) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")

    def fail_generate(**_: object):
        raise AssertionError("herramienta equipo no debe llamar a Ollama")

    monkeypatch.setattr("openclaw_local.telegram_bot.ollama_generate", fail_generate)

    payload = dispatch_command("herramienta", "equipo", repo_root=ROOT, store=store)

    assert payload["status"] == "ok"
    assert "Equipo OpenClaw:" in payload["text"]
    assert "nota=sin exponer secretos" in payload["text"]


def test_approvals_tool_lists_pending_apr(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")

    proposal = dispatch_command("chat", "scan red local", repo_root=ROOT, store=store, chat_id="42")
    approvals = dispatch_command("herramienta", "aprobaciones", repo_root=ROOT, store=store, chat_id="42")

    assert proposal["status"] == "approval_required"
    assert proposal["approval_id"] in approvals["text"]


def test_forget_clears_preferences_without_readding_turn(tmp_path: Path) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")

    dispatch_command("aprender", "prefiero respuestas breves", repo_root=ROOT, store=store, chat_id="42")
    forgotten = dispatch_command("olvidar", "preferencias", repo_root=ROOT, store=store, chat_id="42")
    state = store.get_cached_context(_chat_state_key("42")) or {}

    assert forgotten["status"] == "forgotten"
    assert state.get("preferences") == []


def test_prompt_adjustment_is_stored_as_pending_learning(tmp_path: Path) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")

    payload = dispatch_command(
        "chat",
        "No vuelvas a decir que investigaste si no hay fuentes",
        repo_root=ROOT,
        store=store,
        chat_id="42",
    )
    memory = dispatch_command("memoria", "", repo_root=ROOT, store=store, chat_id="42")

    assert payload["status"] == "learning_proposed"
    assert "ajuste_prompt_pendiente" in payload["text"]
    assert "No vuelvas a decir que investigaste" in memory["text"]


def test_voice_message_uses_stt_and_tts_with_audio_reply(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_ID", "42")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_BOT_TOKEN", "token-test")
    store = OpenClawStore(tmp_path / "openclaw.db")
    source_audio = tmp_path / "input.ogg"
    source_audio.write_bytes(b"audio")
    output_audio = tmp_path / "output.mp3"
    output_audio.write_bytes(b"audio-tts")

    monkeypatch.setattr(
        "openclaw_local.telegram_bot.download_telegram_file",
        lambda **kwargs: {"status": "ok", "path": str(source_audio), "telegram_file_path": "voice/file.ogg"},
    )
    monkeypatch.setattr(
        "openclaw_local.telegram_bot.transcribe_audio",
        lambda **kwargs: {"status": "ok", "provider": "openai", "model": "gpt-4o-mini-transcribe", "text": "hola desde voz"},
    )
    monkeypatch.setattr(
        "openclaw_local.telegram_bot._chat_response",
        lambda *args, **kwargs: {"status": "ok", "text": "[qwen3:4b] provider=ollama_local modo=chat_local\nrespuesta corta"},
    )
    monkeypatch.setattr(
        "openclaw_local.telegram_bot.synthesize_speech",
        lambda **kwargs: {
            "status": "ok",
            "provider": "openai",
            "model": "gpt-4o-mini-tts",
            "voice": "alloy",
            "path": str(output_audio),
        },
    )
    monkeypatch.setattr("openclaw_local.telegram_bot.send_voice_message", lambda *args, **kwargs: {"status": "sent", "detail": "ok"})

    def fail_text(*args, **kwargs):
        raise AssertionError("No debe mandar texto cuando voz fue enviada")

    monkeypatch.setattr("openclaw_local.telegram_bot.send_message", fail_text)

    payload = handle_update(
        {
            "update_id": 99,
            "message": {
                "chat": {"id": 42},
                "voice": {"file_id": "file-1", "duration": 4, "mime_type": "audio/ogg"},
            },
        },
        repo_root=ROOT,
        store=store,
    )

    assert payload["status"] == "ok_voice"
    assert payload["reply_sent"] is True
    assert payload["telegram"]["voice"]["status"] == "sent"
    events = store.list_telegram_voice_events(limit=1)
    assert len(events) == 1
    assert events[0]["artifact"]["transcript_text"] == "hola desde voz"


def test_call_mode_command_updates_state(tmp_path: Path) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")

    payload = dispatch_command("llamada", "on rapida", repo_root=ROOT, store=store, chat_id="42")
    state = store.get_cached_context(_chat_state_key("42")) or {}

    assert payload["status"] == "ok"
    assert "estilo=rapida" in payload["text"]
    assert state.get("call_mode", {}).get("enabled") is True
    assert state.get("call_mode", {}).get("style") == "rapida"


def test_voice_requires_call_mode_when_enabled(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_TELEGRAM_CHAT_ID", "42")
    monkeypatch.setenv("OPENCLAW_TELEGRAM_VOICE_REQUIRE_CALL_MODE", "1")
    store = OpenClawStore(tmp_path / "openclaw.db")
    monkeypatch.setattr("openclaw_local.telegram_bot.send_message", lambda *args, **kwargs: {"status": "sent", "detail": "ok"})

    payload = handle_update(
        {
            "update_id": 100,
            "message": {
                "chat": {"id": 42},
                "voice": {"file_id": "file-2", "duration": 5, "mime_type": "audio/ogg"},
            },
        },
        repo_root=ROOT,
        store=store,
    )

    assert payload["status"] == "call_mode_required"
    assert payload["reply_sent"] is True
    assert "Modo llamada desactivado" in payload["text"]
