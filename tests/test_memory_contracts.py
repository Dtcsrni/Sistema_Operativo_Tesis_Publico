from __future__ import annotations

from build_memory import render_memory
from validate_memory import validate
from common import ROOT, load_yaml_json


def test_memory_builder_exposes_required_sections() -> None:
    content = render_memory()
    assert "Este `MEMORY.md` es un artefacto derivado" in content
    assert "Últimos cambios validados" in content
    assert "Próximos pendientes críticos" in content
    assert "Referencias base" in content


def test_memory_validator_accepts_current_repository() -> None:
    assert validate() == []


def test_publication_contract_includes_memory() -> None:
    publication = load_yaml_json("00_sistema_tesis/config/publicacion.yaml")
    assert any(item["source"] == "MEMORY.md" for item in publication["artefactos"])
    assert (ROOT / "MEMORY.md").exists()
