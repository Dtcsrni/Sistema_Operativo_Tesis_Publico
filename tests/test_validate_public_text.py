from __future__ import annotations

import shutil
from pathlib import Path

import build_dashboard as build_dashboard_module
import build_wiki as build_wiki_module
import common
import publication as publication_module
import pytest
import validate_public_text as validate_public_text_module
from build_dashboard import main as build_dashboard_main
from build_wiki import build_wiki
from publication import publication_bundle_status
from validate_public_text import validate_public_text, validate_public_text_payloads

from common import ROOT


@pytest.fixture
def isolated_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        repo,
        ignore=shutil.ignore_patterns(".git", ".venv", ".pytest_cache", "__pycache__"),
    )
    monkeypatch.setattr(common, "ROOT", repo)
    monkeypatch.setattr(build_wiki_module, "ROOT", repo)
    monkeypatch.setattr(build_dashboard_module, "ROOT", repo)
    monkeypatch.setattr(publication_module, "ROOT", repo)
    monkeypatch.setattr(validate_public_text_module, "ROOT", repo)
    return repo


def test_validate_public_text_accepts_generated_public_surface(isolated_repo: Path) -> None:
    repo = isolated_repo
    build_wiki()
    build_dashboard_main()
    publication_bundle_status(build=True)

    errors = validate_public_text(repo)

    assert errors == []


def test_generated_public_surface_is_editorially_clean(isolated_repo: Path) -> None:
    repo = isolated_repo
    build_wiki()
    build_dashboard_main()
    publication_bundle_status(build=True)

    public_readme = (repo / "06_dashboard" / "publico" / "README_publico.md").read_text(encoding="utf-8")
    public_bitacora = (repo / "06_dashboard" / "publico" / "wiki" / "bitacora.md").read_text(encoding="utf-8")
    public_dashboard = (repo / "06_dashboard" / "publico" / "dashboard" / "index.html").read_text(encoding="utf-8")

    assert "repositorio privado" not in public_readme.lower()
    assert "[validacion_humana_interna]" not in public_bitacora
    assert "[hash_redactado]" not in public_bitacora
    assert "VAL-STEP-" not in public_bitacora
    assert "### Sin fecha" not in public_bitacora
    assert "### Índices maestros" in public_bitacora
    assert "### Qué es este bloque" in public_bitacora
    assert "### Para qué sirve" in public_bitacora
    assert "### Qué representa" in public_bitacora
    assert "### Enlaces de navegación" in public_bitacora
    assert "## Bitácora de sesiones de trabajo registradas" in public_bitacora
    assert "??? \"2026-" in public_bitacora
    assert "validación(es)\"" in public_bitacora
    assert "https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/decisiones/" in public_bitacora
    assert "[identidad_agente_privada]" not in public_dashboard
    assert "[fecha_hora_redactada]" not in public_dashboard
    assert "Última actualización:" in public_readme
    assert "Última actualización:" in public_bitacora
    assert "Última actualización:" in public_dashboard


def test_validate_public_text_reports_placeholder_and_missing_footer() -> None:
    payloads = {
        "README.md": b"# Demo\n\nEste repositorio privado sigue visible.\n",
        "06_dashboard/publico/README_publico.md": b"# Demo\n\n[fecha_hora_redactada]\n",
        "06_dashboard/publico/dashboard/index.html": b"<html><body>sha256:abcdef</body></html>",
    }

    errors = validate_public_text_payloads(payloads)

    assert any("frase privada impropia" in error for error in errors)
    assert any("placeholder redactado" in error for error in errors)
    assert any("hash sha256 visible" in error for error in errors)
    assert any("Última actualización" in error for error in errors)
