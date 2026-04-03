from __future__ import annotations

import shutil
from pathlib import Path

import build_dashboard as build_dashboard_module
import build_wiki as build_wiki_module
import common
import publication as publication_module
import pytest
import validate_links as validate_links_module
from build_dashboard import main as build_dashboard_main
from build_wiki import build_wiki
from publication import publication_bundle_status
from validate_links import validate_links

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
    monkeypatch.setattr(validate_links_module, "ROOT", repo)
    return repo


def test_validate_links_accepts_generated_internal_and_public_surfaces(isolated_repo: Path) -> None:
    repo = isolated_repo
    build_wiki()
    build_dashboard_main()
    publication_bundle_status(build=True)

    errors = validate_links(repo)

    assert errors == []


def test_internal_and_public_outputs_use_surface_specific_links(isolated_repo: Path) -> None:
    repo = isolated_repo
    build_wiki()
    build_dashboard_main()
    publication_bundle_status(build=True)

    bitacora_page = (repo / "06_dashboard" / "wiki" / "bitacora.md").read_text(encoding="utf-8")
    public_dashboard = (repo / "06_dashboard" / "publico" / "dashboard" / "index.html").read_text(encoding="utf-8")
    public_readme = (repo / "06_dashboard" / "publico" / "README_publico.md").read_text(encoding="utf-8")

    assert "(../../00_sistema_tesis/bitacora/matriz_trazabilidad.md)" in bitacora_page
    assert 'href="../wiki_html/index.html"' in public_dashboard
    assert 'href="../index.md"' in public_dashboard
    assert "NOTA_SEGURIDAD_Y_ACCESO.md" in public_dashboard
    assert "(wiki/index.md)" in public_readme
    assert "(wiki_html/index.html)" in public_readme
    assert "(NOTA_SEGURIDAD_Y_ACCESO.md)" in public_readme
    assert "]([reporte_interno_redactado])" not in public_readme


def test_validate_links_reports_missing_target_and_anchor(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "06_dashboard" / "wiki").mkdir(parents=True)
    (repo / "06_dashboard" / "generado").mkdir(parents=True)
    (repo / "06_dashboard" / "publico").mkdir(parents=True)
    (repo / "README.md").write_text("[rota](06_dashboard/wiki/faltante.md)\n", encoding="utf-8")
    (repo / "README_INICIO.md").write_text("[ancla](README.md#sin-ancla)\n", encoding="utf-8")

    errors = validate_links(repo)

    assert any("destino inexistente" in error for error in errors)
    assert any("ancla inexistente" in error for error in errors)


def test_validate_links_reports_placeholder_href_in_wiki_surface(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / "06_dashboard" / "wiki").mkdir(parents=True)
    (repo / "06_dashboard" / "generado").mkdir(parents=True)
    (repo / "06_dashboard" / "publico").mkdir(parents=True)
    (repo / "README.md").write_text("# Root\n", encoding="utf-8")
    (repo / "README_INICIO.md").write_text("# Inicio\n", encoding="utf-8")
    (repo / "06_dashboard" / "wiki" / "bitacora.md").write_text(
        "[privado](../../[bitacora_privada]/2026-04-02_bitacora_sesion.md)\n",
        encoding="utf-8",
    )

    errors = validate_links(repo)

    assert any("placeholder redactado" in error for error in errors)
