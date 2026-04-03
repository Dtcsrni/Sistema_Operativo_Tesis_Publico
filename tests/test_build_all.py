from __future__ import annotations

from build_all import STEPS


def test_build_all_includes_wiki_step() -> None:
    scripts = [step[1] for step in STEPS]
    assert "07_scripts/build_wiki.py" in scripts
    assert "07_scripts/validate_links.py" in scripts
    assert ("Sincronizar publicación pública sanitizada", "07_scripts/tesis.py", ["publish", "--build"]) in STEPS
    assert ("Verificar evidencia fuente de conversación", "07_scripts/tesis.py", ["source", "status", "--check"]) in STEPS
    assert ("Verificar operabilidad humana", "07_scripts/tesis.py", ["doctor", "--check"]) in STEPS
    assert ("Validar publicación pública sanitizada", "07_scripts/tesis.py", ["publish", "--check"]) in STEPS
