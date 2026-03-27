from __future__ import annotations

import json
import shutil
from pathlib import Path

import build_wiki as build_wiki_module
import common
import pytest
import validate_wiki as validate_wiki_module
from build_wiki import SECTION_IDS, build_wiki
from common import ROOT
from validate_wiki import validate_wiki


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
    monkeypatch.setattr(validate_wiki_module, "ROOT", repo)
    return repo


def test_build_wiki_generates_expected_pages_and_manifest(isolated_repo: Path) -> None:
    repo = isolated_repo
    result = build_wiki()

    assert result["verification_status"] == "ok"
    assert set(result["pages"]) == SECTION_IDS | {"index"}

    index_path = repo / "06_dashboard" / "wiki" / "index.md"
    content = index_path.read_text(encoding="utf-8")
    assert "Fecha de generación" in content
    assert "Estado de verificación: `ok`" in content
    assert "Fuentes canónicas" in content
    assert "Mapa de navegación por intención" in content
    assert "Cómo rastrear un artefacto derivado hasta su origen canónico" in content

    manifest = json.loads((repo / "06_dashboard" / "generado" / "wiki_manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["pages"]) == set(result["pages"])
    assert manifest["verification"]["status"] == "ok"


def test_validate_wiki_accepts_generated_outputs(isolated_repo: Path) -> None:
    repo = isolated_repo
    build_wiki()
    errors = validate_wiki(repo)
    assert errors == []


def test_wiki_exposes_human_operation_and_public_private_boundary(isolated_repo: Path) -> None:
    repo = isolated_repo
    build_wiki()

    index_page = (repo / "06_dashboard" / "wiki" / "index.md").read_text(encoding="utf-8")
    sistema_page = (repo / "06_dashboard" / "wiki" / "sistema.md").read_text(encoding="utf-8")
    gobernanza_page = (repo / "06_dashboard" / "wiki" / "gobernanza.md").read_text(encoding="utf-8")
    terminologia_page = (repo / "06_dashboard" / "wiki" / "terminologia.md").read_text(encoding="utf-8")

    assert "Operación humana y frontera público/privado" in index_page
    assert "Módulos del sistema" in index_page
    assert "Cómo rastrear un artefacto derivado hasta su origen canónico" in index_page
    assert "Operación humana y superficies" in sistema_page
    assert "Navegación de esta página" in sistema_page
    assert "Origen canónico y artefactos relacionados" in sistema_page
    assert "Mapa rápido de términos e IDs" in sistema_page
    assert "Mapa de modulos del sistema" in sistema_page
    assert "Flujos operativos" in sistema_page
    assert "Interaccion por actor" in sistema_page
    assert "IA opcional" in sistema_page
    assert "La IA es opcional" in gobernanza_page
    assert "Origen canónico y artefactos relacionados" in gobernanza_page
    assert "Vocabulario de gobernanza y trazabilidad" in gobernanza_page
    assert "Límites de la capa pública" in gobernanza_page
    assert "Glosario canónico" in terminologia_page
    assert "Origen canónico y artefactos relacionados" in terminologia_page
    assert "VAL-STEP-530" in terminologia_page
    assert "EVT-0053" in terminologia_page
    assert "Qué resuelve este subsistema" in (repo / "06_dashboard" / "wiki" / "planeacion.md").read_text(encoding="utf-8")
    assert "Convenciones de planeación" in (repo / "06_dashboard" / "wiki" / "planeacion.md").read_text(encoding="utf-8")
    assert "Origen canónico y artefactos relacionados" in (repo / "06_dashboard" / "wiki" / "planeacion.md").read_text(encoding="utf-8")
    assert "Qué resuelve este subsistema" in (repo / "06_dashboard" / "wiki" / "hipotesis.md").read_text(encoding="utf-8")
    assert "Qué resuelve este subsistema" in (repo / "06_dashboard" / "wiki" / "bloques.md").read_text(encoding="utf-8")
    assert "Cómo leer esta cobertura" in (repo / "06_dashboard" / "wiki" / "experimentos.md").read_text(encoding="utf-8")


def test_empty_scope_sections_are_marked_as_pending_coverage(isolated_repo: Path) -> None:
    repo = isolated_repo
    build_wiki()

    experiments_page = (repo / "06_dashboard" / "wiki" / "experimentos.md").read_text(encoding="utf-8")
    implementation_page = (repo / "06_dashboard" / "wiki" / "implementacion.md").read_text(encoding="utf-8")
    thesis_page = (repo / "06_dashboard" / "wiki" / "tesis.md").read_text(encoding="utf-8")

    assert "Sin contenido operativo aún" in experiments_page
    assert "Sin contenido operativo aún" in implementation_page
    assert "Sin contenido operativo aún" in thesis_page


def test_validate_wiki_reports_missing_source_with_clear_error(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "00_sistema_tesis" / "config").mkdir(parents=True)
    (repo / "06_dashboard" / "wiki").mkdir(parents=True)
    (repo / "06_dashboard" / "generado").mkdir(parents=True)
    wiki_config = {
        "politica": {"editable_directamente": False},
        "salida": {
            "markdown_dir": "06_dashboard/wiki",
            "html_dir": "06_dashboard/generado/wiki",
            "manifest": "06_dashboard/generado/wiki_manifest.json",
        },
        "secciones": [
            {
                "id": "sistema",
                "titulo": "Sistema",
                "descripcion": "desc",
                "fuentes": ["README_INEXISTENTE.md"],
            }
        ],
    }
    (repo / "00_sistema_tesis" / "config" / "wiki.yaml").write_text(json.dumps(wiki_config), encoding="utf-8")
    (repo / "06_dashboard" / "wiki" / "sistema.md").write_text(
        "# Sistema\n\n- Estado de verificación: `ok`\n- Fuentes canónicas: `README_INEXISTENTE.md`\n",
        encoding="utf-8",
    )
    (repo / "06_dashboard" / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
    (repo / "06_dashboard" / "generado" / "wiki_manifest.json").write_text(
        json.dumps({"pages": ["index", "sistema"], "verification": {"status": "ok"}}),
        encoding="utf-8",
    )

    errors = validate_wiki(repo)

    assert any("README_INEXISTENTE.md" in error for error in errors)


def test_validate_wiki_reports_missing_required_section(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "00_sistema_tesis" / "config").mkdir(parents=True)
    (repo / "06_dashboard" / "wiki").mkdir(parents=True)
    (repo / "06_dashboard" / "generado").mkdir(parents=True)
    wiki_config = {
        "politica": {"editable_directamente": False},
        "salida": {
            "markdown_dir": "06_dashboard/wiki",
            "html_dir": "06_dashboard/generado/wiki",
            "manifest": "06_dashboard/generado/wiki_manifest.json",
        },
        "secciones": [],
    }
    (repo / "00_sistema_tesis" / "config" / "wiki.yaml").write_text(json.dumps(wiki_config), encoding="utf-8")
    (repo / "06_dashboard" / "wiki" / "index.md").write_text("# Index\n", encoding="utf-8")
    (repo / "06_dashboard" / "generado" / "wiki_manifest.json").write_text(
        json.dumps({"pages": ["index"], "verification": {"status": "ok"}}),
        encoding="utf-8",
    )

    errors = validate_wiki(repo)

    assert any("sección requerida" in error.lower() for error in errors)
