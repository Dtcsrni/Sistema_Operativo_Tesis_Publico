from __future__ import annotations

import sys

import build_all
from build_runner.registry import BuildStep
from build_runner.registry import STEPS
from build_runner.runner import StepReport, run_step

def test_build_all_includes_wiki_step() -> None:
    scripts = [step.script for step in STEPS]
    assert "07_scripts/ops/build_wiki.py" in scripts
    assert "07_scripts/ops/build_memory.py" in scripts
    assert "07_scripts/audit/validate_memory.py" in scripts
    assert "07_scripts/audit/validate_b0_architecture.py" in scripts
    assert "07_scripts/audit/validate_links.py" in scripts
    assert "07_scripts/audit/validate_public_text.py" in scripts

    step_tuples = [(step.label, step.script, step.args) for step in STEPS]
    assert ("Sincronizar publicación pública sanitizada", "07_scripts/tesis.py", ["publish", "--build"]) in step_tuples
    assert ("Verificar evidencia fuente de conversación", "07_scripts/tesis.py", ["source", "status", "--check"]) in step_tuples
    assert ("Verificar operabilidad humana", "07_scripts/tesis.py", ["doctor", "--check"]) in step_tuples
    assert ("Validar publicación pública sanitizada", "07_scripts/tesis.py", ["publish", "--check"]) in step_tuples
    assert ("Auditar calidad de trazabilidad", "07_scripts/audit/verify_traceability_quality.py", ["--strict"]) in step_tuples

def test_build_all_profiles_build_execution() -> None:
    # Ahora build_all delega en build_runner, verificamos que los presupuestos existan
    budgets = {step.label: step.budget_s for step in STEPS if step.budget_s is not None}
    assert "Sincronizar publicación pública sanitizada" in budgets
    assert "Generar memoria operativa" in budgets


def test_build_all_default_profile_keeps_full_incremental_contract() -> None:
    args = build_all._build_parser().parse_args([])
    selected = build_all._select_steps(args)
    assert args.profile == "full"
    assert len(selected) == len(STEPS)


def test_build_all_smoke_profile_selects_minimal_agile_gate() -> None:
    args = build_all._build_parser().parse_args(["--profile", "smoke"])
    selected = build_all._select_steps(args)
    labels = [step.label for step in selected]
    assert labels == list(build_all.SMOKE_LABELS)
    test_step = next(step for step in selected if step.label == build_all.TEST_STEP_LABEL)
    assert test_step.args == ["--profile", "smoke", "--fast"]


def test_step_report_serializes_extended_evidence_fields() -> None:
    report = StepReport(
        label="Demo",
        script="demo.py",
        args=[],
        group="demo",
        started_at_utc="2026-06-02 00:00:00",
        duration_seconds=1.0,
        budget_seconds=None,
        status="ok",
        returncode=0,
        cache_hit=False,
        profile="dev",
        selected_reason="profile:dev",
        timeout_seconds=5.0,
        timed_out=False,
        command=["python", "demo.py"],
        last_status="completed",
    )
    payload = report.to_dict()
    assert payload["profile"] == "dev"
    assert payload["selected_reason"] == "profile:dev"
    assert payload["timeout_seconds"] == 5.0
    assert payload["timed_out"] is False
    assert payload["command"] == ["python", "demo.py"]
    assert payload["last_status"] == "completed"


def test_run_step_timeout_reports_actionable_failure(tmp_path) -> None:
    script = tmp_path / "sleepy.py"
    script.write_text("import time\ntime.sleep(2)\n", encoding="utf-8")
    step = BuildStep(label="Sleepy", script="sleepy.py", group="test")

    report = run_step(
        step=step,
        root=tmp_path,
        python_exe=sys.executable,
        timeout_seconds=0.1,
        profile="dev",
        selected_reason="unit-test",
    )

    assert report.status == "failed"
    assert report.timed_out is True
    assert report.timeout_seconds == 0.1
    assert report.last_status == "timeout"
