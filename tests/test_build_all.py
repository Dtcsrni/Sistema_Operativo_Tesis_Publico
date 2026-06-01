from __future__ import annotations

from build_runner.registry import STEPS

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
