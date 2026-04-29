from __future__ import annotations

import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "runtime" / "openclaw"

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from openclaw_local.contracts import ClaimRecord, LiteratureRecord, TaskEnvelope, WritingDraft  # noqa: E402
from openclaw_local.budgeting import build_billing_record, simulate_budget_request  # noqa: E402
from openclaw_local.engine import (  # noqa: E402
    build_academic_packet,
    build_evidence_record,
    render_academic_artifacts,
    route_task,
    summarize_host,
)
from openclaw_local.policies import load_budget_policy, load_domain_policies, load_domain_secret_policies, load_provider_registry, load_runtime_contracts  # noqa: E402
from openclaw_local.runtime_status import build_preflight_report, probe_runtime_status, run_runtime_benchmarks  # noqa: E402
from openclaw_local.secret_resolver import build_secret_status, resolve_provider_secret  # noqa: E402
from openclaw_local.storage import OpenClawStore  # noqa: E402


def _write_domain_envs(tmp_path: Path) -> Path:
    domains_dir = tmp_path / "domains"
    domains_dir.mkdir()
    (domains_dir / "personal.env").write_text("", encoding="utf-8")
    (domains_dir / "profesional.env").write_text("GROQ_API_KEY=groq-prof\nOPENAI_API_KEY=openai-prof\n", encoding="utf-8")
    (domains_dir / "academico.env").write_text(
        "GROQ_API_KEY=groq-acad\nGEMINI_API_KEY=gemini-acad\nOPENAI_API_KEY=openai-acad\nOPENCLAW_GEMINI_STUDENT_ENABLED=1\nOPENCLAW_CHATGPT_PLUS_ENABLED=1\n",
        encoding="utf-8",
    )
    (domains_dir / "edge.env").write_text("", encoding="utf-8")
    (domains_dir / "administrativo.env").write_text("", encoding="utf-8")
    return domains_dir


def test_route_task_prefers_local_for_edge_and_requires_gate_on_mutation() -> None:
    policies = load_domain_policies(ROOT)
    task = TaskEnvelope(
        task_id="TASK-EDGE-001",
        title="Revisar servicio edge",
        domain="edge",
        objective="Inspeccionar salud y reinicio de edge_iot",
        complexity="medium",
        risk_level="high",
        mutates_state=True,
        target_paths=["/srv/tesis/workspace/edge"],
    )

    decision = route_task(task, policies)

    assert decision.provider == "local"
    assert decision.model_class == "rules_or_local_model"
    assert decision.requires_human_gate is True
    assert decision.fallback_chain[-1] == "manual"


def test_route_task_uses_cloud_assisted_for_academic_high_complexity(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    policies = load_domain_policies(ROOT)
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(_write_domain_envs(tmp_path)))
    store = OpenClawStore(tmp_path / "openclaw.db")
    task = TaskEnvelope(
        task_id="TASK-ACA-001",
        title="Comparar literatura",
        domain="academico",
        objective="Sintetizar contradicciones entre fuentes primarias",
        complexity="high",
        risk_level="medium",
        requires_citations=True,
        mutates_state=False,
    )

    decision = route_task(task, policies, repo_root=ROOT, store=store)

    assert decision.provider == "gemini_api"
    assert decision.model_class == "cloud_assisted_mid_cost"
    assert decision.requires_human_gate is False
    assert "offline" in decision.fallback_chain
    assert decision.session_mode == "direct_api_call"


def test_build_evidence_record_hashes_payload_stably() -> None:
    policies = load_domain_policies(ROOT)
    task = TaskEnvelope(
        task_id="TASK-EVI-001",
        title="Registrar evidencia",
        domain="academico",
        objective="Producir resumen auditable",
        complexity="low",
        risk_level="low",
    )
    decision = route_task(task, policies)

    record_a = build_evidence_record(
        task=task,
        decision=decision,
        prompt="Resume el documento",
        response="Resumen generado",
        context={"source": "nota.md"},
        estimated_cost=0.0,
        source_links=["nota.md"],
        session_id="SESSION-001",
    )
    record_b = build_evidence_record(
        task=task,
        decision=decision,
        prompt="Resume el documento",
        response="Resumen generado",
        context={"source": "nota.md"},
        estimated_cost=0.0,
        source_links=["nota.md"],
        session_id="SESSION-001",
    )

    assert record_a.payload_hash == record_b.payload_hash
    assert record_a.provider == decision.provider
    assert record_a.task_id == task.task_id


def test_store_persists_tasks_approvals_and_evidence(tmp_path: Path) -> None:
    db_path = tmp_path / "openclaw.db"
    store = OpenClawStore(db_path)
    policies = load_domain_policies(ROOT)
    task = TaskEnvelope(
        task_id="TASK-APP-001",
        title="Preparar cambio documental",
        domain="academico",
        objective="Proponer borrador de decision",
        complexity="medium",
        risk_level="high",
        mutates_state=True,
        target_paths=["docs/02_arquitectura/openclaw-control-plane.md"],
    )
    decision = route_task(task, policies)

    store.save_task(task, decision)
    approval_id = store.create_approval_request(
        task=task,
        decision=decision,
        diff_summary="Agregar documento de arquitectura",
        affected_targets=task.target_paths,
        step_id_expected="VAL-STEP-900",
        evidence_source_required=True,
    )
    evidence = build_evidence_record(
        task=task,
        decision=decision,
        prompt="Redacta el documento",
        response="Borrador listo",
        context={"domain": task.domain},
        estimated_cost=0.12,
        source_links=["docs/02_arquitectura/openclaw-control-plane.md"],
        session_id="SESSION-002",
    )
    store.save_evidence(evidence)

    pending = store.list_pending_approvals()
    saved_task = store.get_task(task.task_id)
    saved_evidence = store.list_evidence_for_task(task.task_id)

    assert pending[0]["approval_id"] == approval_id
    assert saved_task["decision"]["provider"] == decision.provider
    assert saved_evidence[0]["payload_hash"] == evidence.payload_hash


def test_runtime_contract_manifest_declares_required_contracts() -> None:
    contracts = load_runtime_contracts(ROOT)
    contract_ids = {item["id"] for item in contracts["contracts"]}
    assert {
        "TaskEnvelope",
        "ProviderDecision",
        "EvidenceRecord",
        "ApprovalRequest",
        "DomainPolicy",
        "DomainSecretPolicy",
        "AcademicWorkPacket",
        "LiteratureRecord",
        "ClaimRecord",
        "WritingDraft",
        "RuntimeProbe",
        "BenchmarkRecord",
        "SecretResolution",
        "BillingRecord",
        "BudgetSnapshot",
    }.issubset(contract_ids)


def test_summarize_host_reports_core_capabilities() -> None:
    summary = summarize_host()
    assert summary["cpu_count"] >= 1
    assert "disk" in summary
    assert "memory" in summary


def test_academic_literature_packet_requires_contradictions_and_writes_matrices() -> None:
    task = TaskEnvelope(
        task_id="TASK-LIT-001",
        title="Estado del arte",
        domain="academico",
        objective="Comparar literatura",
        extra_context={"academic_mode": "estado_del_arte"},
        target_paths=[
            "docs/05_reproducibilidad/matriz-de-literatura.md",
            "docs/05_reproducibilidad/matriz-de-afirmaciones-y-evidencia.md",
        ],
    )
    claims = [
        ClaimRecord(
            claim_id="CLM-001",
            claim_text="La arquitectura requiere tolerancia a intermitencia.",
            classification="inferencia_razonada",
            source_refs=["doi:10.1000/test"],
            confidence="alto",
            verification_status="fuente_primaria",
            impact_on_thesis="Impacta la selección de arquitectura.",
        )
    ]
    literature = [
        LiteratureRecord(
            record_id="LIT-001",
            tema="Intermitencia urbana",
            pregunta="¿Cómo afecta la conectividad intermitente?",
            fuente="Fuente primaria A",
            anio="2025",
            doi="10.1000/test",
            nivel_evidencia="alto",
            hallazgos_clave=["La intermitencia cambia la latencia."],
            contradicciones=["No hay consenso sobre la estrategia de buffering."],
            relacion_con_hipotesis="Soporta la necesidad de resiliencia.",
            estado_verificacion="verificado",
        )
    ]

    packet = build_academic_packet(
        task=task,
        question="¿Qué contradicciones importan para la tesis?",
        scope="Fuentes primarias 2020-2026",
        sources=["doi:10.1000/test"],
        claims=claims,
        literature_records=literature,
        traceability_links=["[DEC-0014]"],
    )
    artifacts = render_academic_artifacts(packet)

    assert packet.mode == "estado_del_arte"
    assert "docs/05_reproducibilidad/matriz-de-literatura.md" in artifacts
    assert "contradicciones" in artifacts["docs/05_reproducibilidad/matriz-de-literatura.md"].lower()


def test_writing_packet_generates_consistent_markdown_and_latex() -> None:
    task = TaskEnvelope(
        task_id="TASK-WRI-001",
        title="Redacción introducción",
        domain="academico",
        objective="Borrador de introducción",
        extra_context={"academic_mode": "redaccion_tesis"},
        target_paths=[
            "runtime/openclaw/state/academico/drafts/introduccion.md",
            "05_tesis_latex/sections/introduccion.tex",
        ],
    )
    draft = WritingDraft(
        section_id="introduccion",
        purpose="Abrir la tesis",
        source_refs=["doi:10.1000/test"],
        open_questions=["Precisar variable dependiente"],
        markdown_body="Primer párrafo.\n\nFuentes: doi:10.1000/test",
        latex_body="Primer párrafo.\\\\\n\\\\textit{Fuentes: doi:10.1000/test}.",
    )
    claims = [
        ClaimRecord(
            claim_id="CLM-002",
            claim_text="La tesis estudia resiliencia.",
            classification="pendiente_de_validacion",
            source_refs=["doi:10.1000/test"],
            confidence="medio",
            verification_status="pendiente_de_validacion",
            impact_on_thesis="Define el planteamiento.",
        )
    ]

    packet = build_academic_packet(
        task=task,
        question="¿Cómo introducir el problema?",
        scope="Introducción",
        sources=["doi:10.1000/test"],
        claims=claims,
        literature_records=[],
        traceability_links=["[DEC-0020]"],
        writing_draft=draft,
    )
    artifacts = render_academic_artifacts(packet)

    assert artifacts["runtime/openclaw/state/academico/drafts/introduccion.md"] == draft.markdown_body + "\n"
    assert artifacts["05_tesis_latex/sections/introduccion.tex"] == draft.latex_body + "\n"


def test_store_persists_academic_packets_and_context_cache(tmp_path: Path) -> None:
    store = OpenClawStore(tmp_path / "openclaw.db")
    task = TaskEnvelope(
        task_id="TASK-ACA-STORE-001",
        title="Metodología",
        domain="academico",
        objective="Comparar enfoques",
        extra_context={"academic_mode": "metodologia"},
    )
    packet = build_academic_packet(
        task=task,
        question="¿Qué enfoque metodológico conviene?",
        scope="Comparación inicial",
        sources=["nota-a.md"],
        claims=[
            ClaimRecord(
                claim_id="CLM-003",
                claim_text="El enfoque A reduce ambigüedad.",
                classification="recomendacion_tentativa",
                source_refs=["nota-a.md"],
                confidence="medio",
                verification_status="pendiente_de_validacion",
                impact_on_thesis="Ayuda a decidir método.",
            )
        ],
        literature_records=[],
        traceability_links=["[DEC-0014]"],
    )

    store.save_academic_packet(packet, "hash-123")
    store.cache_context("cache-1", {"result": "ok"})

    saved = store.get_latest_academic_packet_for_task(task.task_id)
    cached = store.get_cached_context("cache-1")

    assert saved["mode"] == "metodologia"
    assert saved["_payload_hash"] == "hash-123"
    assert cached == {"result": "ok"}


def test_probe_runtime_status_uses_force_flags_for_orange_pi(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("OPENCLAW_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("OPENCLAW_LOG_DIR", str(tmp_path / "log"))
    monkeypatch.setenv("OPENCLAW_DB_PATH", str(tmp_path / "data" / "openclaw.db"))
    monkeypatch.setenv("OPENCLAW_ENV_FILE", str(tmp_path / "openclaw.env"))
    monkeypatch.setenv("OPENCLAW_FORCE_ORANGE_PI_MODEL", "Orange Pi 5 Plus")
    monkeypatch.setenv("OPENCLAW_FORCE_MEMORY_BYTES", str(8 * 1024 * 1024 * 1024))
    monkeypatch.setenv("OPENCLAW_FORCE_ROOT_DEVICE", "/dev/nvme0n1p1")
    monkeypatch.setenv("OPENCLAW_FORCE_ROOTFS_TYPE", "ext4")
    monkeypatch.setenv("OPENCLAW_FORCE_EMMC_PRESENT", "1")
    monkeypatch.setenv("OPENCLAW_FORCE_OLLAMA_READY", "1")
    monkeypatch.setenv("OPENCLAW_FORCE_NPU_READY", "1")
    (tmp_path / "data").mkdir()
    (tmp_path / "cache").mkdir()
    (tmp_path / "log").mkdir()
    (tmp_path / "openclaw.env").write_text("OPENCLAW_PORT=18789\n", encoding="utf-8")

    status = probe_runtime_status(ROOT)

    assert status["state"] == "npu_experimental_ready"
    assert status["host"]["orange_pi_model"] == "Orange Pi 5 Plus"
    assert status["host"]["disk"]["rootfs_on_nvme"] is True
    assert status["ollama"]["ready"] is True
    assert status["npu"]["ready"] is True


def test_runtime_benchmarks_are_persistable_without_auto_switch(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_BENCHMARK_SIMULATION", "1")
    monkeypatch.setenv("OPENCLAW_FORCE_OLLAMA_READY", "1")
    monkeypatch.setenv("OPENCLAW_FORCE_NPU_READY", "1")
    store = OpenClawStore(tmp_path / "openclaw.db")

    payload = run_runtime_benchmarks(ROOT)
    for item in payload["results"]:
        from openclaw_local.contracts import BenchmarkRecord  # noqa: WPS433,E402

        store.save_benchmark_record(
            BenchmarkRecord(
                benchmark_id=item["benchmark_id"],
                provider=item["provider"],
                status=item["status"],
                latency_ms=item.get("latency_ms"),
                details=item["details"],
                created_at=item["created_at"],
            )
        )

    saved = store.list_benchmark_runs(limit=5)

    assert payload["active_runtime"] == "ollama_local"
    assert payload["recommended_runtime"] == "rknn_llm_experimental"
    assert len(saved) == 2
    assert all(item["provider"] in {"ollama_local", "rknn_llm_experimental"} for item in saved)


def test_preflight_report_fails_when_env_is_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("OPENCLAW_DB_PATH", str(tmp_path / "data" / "openclaw.db"))
    monkeypatch.setenv("OPENCLAW_ENV_FILE", str(tmp_path / "missing.env"))
    (tmp_path / "data").mkdir()

    report = build_preflight_report(ROOT)

    assert report["status"] == "fail"
    assert any(item["name"] == "env_file" and item["status"] == "fail" for item in report["checks"])


def test_secret_resolver_loads_environment_file_by_domain(tmp_path: Path, monkeypatch) -> None:
    domains_dir = _write_domain_envs(tmp_path)
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(domains_dir))

    resolution = resolve_provider_secret("academico", "gemini_api", secret_policies=load_domain_secret_policies(ROOT))

    assert resolution.status == "ready"
    assert resolution.credential_scope == "academico.env"
    assert resolution.missing_variables == []


def test_secret_status_does_not_expose_secret_values(tmp_path: Path, monkeypatch) -> None:
    domains_dir = _write_domain_envs(tmp_path)
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(domains_dir))
    from openclaw_local.policies import load_domain_secret_policies, load_provider_registry  # noqa: E402

    payload = build_secret_status(
        secret_policies=load_domain_secret_policies(ROOT),
        provider_registry=load_provider_registry(ROOT),
    )

    serialized = str(payload)
    assert "groq-acad" not in serialized
    assert "openai-acad" not in serialized
    assert payload["domains"]["academico"]["providers"]["gemini_api"]["status"] == "ready"


def test_route_task_prefers_groq_for_professional_medium_when_secret_exists(tmp_path: Path, monkeypatch) -> None:
    domains_dir = _write_domain_envs(tmp_path)
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(domains_dir))
    store = OpenClawStore(tmp_path / "openclaw.db")
    task = TaskEnvelope(
        task_id="TASK-PRO-001",
        title="Resumen técnico",
        domain="profesional",
        objective="Sintetizar incidentes de bajo costo",
        complexity="medium",
        risk_level="medium",
    )

    decision = route_task(task, load_domain_policies(ROOT), repo_root=ROOT, store=store)

    assert decision.provider == "groq_api"
    assert decision.session_mode == "direct_api_call"


def test_route_task_blocks_cloud_for_edge_even_if_secrets_exist(tmp_path: Path, monkeypatch) -> None:
    domains_dir = _write_domain_envs(tmp_path)
    monkeypatch.setenv("OPENCLAW_DOMAINS_ENV_DIR", str(domains_dir))
    store = OpenClawStore(tmp_path / "openclaw.db")
    task = TaskEnvelope(
        task_id="TASK-EDGE-002",
        title="Inspección edge",
        domain="edge",
        objective="Evaluar estado de nube no permitido",
        complexity="high",
        risk_level="medium",
    )

    decision = route_task(task, load_domain_policies(ROOT), repo_root=ROOT, store=store)

    assert decision.provider == "local"
    assert decision.session_mode == "local_runtime"


def test_budget_simulation_blocks_domain_when_local_ledger_exhausts_limit(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "00_sistema_tesis" / "config").mkdir(parents=True)
    (repo_root / "00_sistema_tesis" / "config" / "token_budget.json").write_text(
        '{"daily":{"tokens":1000,"usd":1.0},"weekly":{"tokens":5000,"usd":5.0},"alerts":{"warning_ratio":0.75,"critical_ratio":0.9}}',
        encoding="utf-8",
    )
    (repo_root / "00_sistema_tesis" / "config" / "token_usage_snapshot.json").write_text(
        '{"windows":{"daily":{"tokens_used":0,"usd_used":0.0},"weekly":{"tokens_used":0,"usd_used":0.0}},"status":"ok","message":""}',
        encoding="utf-8",
    )
    store = OpenClawStore(tmp_path / "billing.db")
    store.save_billing_record(
        build_billing_record(
            task_id="TASK-BGT-001",
            session_id="SESSION-BGT-001",
            domain="academico",
            provider="gemini_api",
            billing_mode="api_measured",
            estimated_tokens=540,
            estimated_cost_usd=0.55,
        )
    )

    payload = simulate_budget_request(
        store=store,
        repo_root=repo_root,
        budget_policy=load_budget_policy(ROOT),
        domain="academico",
        provider="gemini_api",
        estimated_cost_usd=0.10,
        estimated_tokens=50,
    )

    assert payload["allowed"] is False
    assert payload["resulting_action"] == "degradar_local_offline_manual"
