from __future__ import annotations

import json
from pathlib import Path

from build_wiki import SECTION_IDS, build_wiki
from common import ROOT
from validate_wiki import validate_wiki


def test_build_wiki_generates_expected_pages_and_manifest() -> None:
    result = build_wiki()

    assert result["verification_status"] == "ok"
    assert set(result["pages"]) == SECTION_IDS | {"index"}

    index_path = ROOT / "06_dashboard" / "wiki" / "index.md"
    content = index_path.read_text(encoding="utf-8")
    assert "Fecha de generación" in content
    assert "Estado de verificación: `ok`" in content
    assert "Fuentes canónicas" in content

    manifest = json.loads((ROOT / "06_dashboard" / "generado" / "wiki_manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["pages"]) == set(result["pages"])
    assert manifest["verification"]["status"] == "ok"


def test_validate_wiki_accepts_generated_outputs() -> None:
    build_wiki()
    errors = validate_wiki()
    assert errors == []


def test_wiki_exposes_human_operation_and_public_private_boundary() -> None:
    build_wiki()

    index_page = (ROOT / "06_dashboard" / "wiki" / "index.md").read_text(encoding="utf-8")
    sistema_page = (ROOT / "06_dashboard" / "wiki" / "sistema.md").read_text(encoding="utf-8")
    gobernanza_page = (ROOT / "06_dashboard" / "wiki" / "gobernanza.md").read_text(encoding="utf-8")

    assert "Operación humana y frontera público/privado" in index_page
    assert "Operación humana y superficies" in sistema_page
    assert "IA opcional" in sistema_page
    assert "La IA es opcional" in gobernanza_page


def test_empty_scope_sections_are_marked_as_pending_coverage() -> None:
    build_wiki()

    experiments_page = (ROOT / "06_dashboard" / "wiki" / "experimentos.md").read_text(encoding="utf-8")
    implementation_page = (ROOT / "06_dashboard" / "wiki" / "implementacion.md").read_text(encoding="utf-8")
    thesis_page = (ROOT / "06_dashboard" / "wiki" / "tesis.md").read_text(encoding="utf-8")

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
