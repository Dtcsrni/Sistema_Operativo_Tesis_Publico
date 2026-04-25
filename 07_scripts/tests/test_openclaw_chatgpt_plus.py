from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
RUNTIME_ROOT = ROOT / "runtime" / "openclaw"

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from openclaw_local.contracts import TaskEnvelope  # noqa: E402
from openclaw_local.engine import route_task  # noqa: E402
from openclaw_local.policies import load_domain_policies  # noqa: E402
from openclaw_local.storage import OpenClawStore  # noqa: E402


def test_route_task_prefers_chatgpt_plus_when_explicitly_requested(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    domains_dir = tmp_path / "domains"
    domains_dir.mkdir()
    (domains_dir / "academico.env").write_text("OPENCLAW_CHATGPT_PLUS_ENABLED=1\nOPENAI_API_KEY=openai-acad\n", encoding="utf-8")
    (domains_dir / "personal.env").write_text("", encoding="utf-8")
    (domains_dir / "profesional.env").write_text("OPENAI_API_KEY=openai-prof\n", encoding="utf-8")
    (domains_dir / "edge.env").write_text("", encoding="utf-8")
    (domains_dir / "administrativo.env").write_text("", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(domains_dir))
    monkeypatch.setenv("OPENCLAW_WEB_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_CLOUD_ENABLED", "0")
    monkeypatch.setenv("OPENCLAW_DESKTOP_COMPUTE_ENABLED", "0")

    task = TaskEnvelope(
        task_id="TASK-ACA-PLUS-001",
        title="Usar ChatGPT Plus con OpenClaw",
        domain="academico",
        objective="Priorizar ChatGPT Plus como web asistida supervisada",
        complexity="medium",
        risk_level="medium",
        mutates_state=False,
        requires_citations=True,
        extra_context={"prefer_chatgpt_plus": True, "preferred_web_assisted": "chatgpt_plus_web_assisted"},
    )

    decision = route_task(task, load_domain_policies(ROOT), repo_root=ROOT, store=OpenClawStore(tmp_path / "openclaw.db"))

    assert decision.provider == "chatgpt_plus_web_assisted"
    assert decision.mode == "cloud_web_assisted"
    assert decision.requires_human_gate is True
    assert decision.session_mode == "human_supervised_web_session"


def test_route_task_does_not_default_to_chatgpt_plus_for_academic_web_tasks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    domains_dir = tmp_path / "domains"
    domains_dir.mkdir()
    (domains_dir / "academico.env").write_text("OPENCLAW_CHATGPT_PLUS_ENABLED=1\nOPENAI_API_KEY=openai-acad\n", encoding="utf-8")
    (domains_dir / "personal.env").write_text("", encoding="utf-8")
    (domains_dir / "profesional.env").write_text("OPENAI_API_KEY=openai-prof\n", encoding="utf-8")
    (domains_dir / "edge.env").write_text("", encoding="utf-8")
    (domains_dir / "administrativo.env").write_text("", encoding="utf-8")
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(domains_dir))
    monkeypatch.setenv("OPENCLAW_WEB_ENABLED", "1")
    monkeypatch.setenv("OPENCLAW_CLOUD_ENABLED", "0")
    monkeypatch.setenv("OPENCLAW_DESKTOP_COMPUTE_ENABLED", "0")

    task = TaskEnvelope(
        task_id="TASK-ACA-PLUS-002",
        title="Default ChatGPT Plus",
        domain="academico",
        objective="Tarea academica sin solicitud explicita de ChatGPT Plus",
        complexity="medium",
        risk_level="medium",
        mutates_state=False,
        requires_citations=True,
    )

    decision = route_task(task, load_domain_policies(ROOT), repo_root=ROOT, store=OpenClawStore(tmp_path / "openclaw.db"))

    assert decision.provider != "chatgpt_plus_web_assisted"
    assert decision.mode != "cloud_web_assisted"
    assert decision.session_mode != "human_supervised_web_session"
