from __future__ import annotations

import json
from pathlib import Path

from common import ROOT
from validate_b0_architecture import validate


def _load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def test_b0_architecture_validator_passes_for_current_repo() -> None:
    assert validate() == []


def test_domain_runtime_and_network_contracts_are_consistent() -> None:
    runtime = _load_json("manifests/domain_runtime_isolation.yaml")
    network = _load_json("manifests/domain_network_policy.yaml")
    services = _load_json("manifests/service_matrix.yaml")

    network_profiles = set(network["profiles"].keys())
    assert runtime["dominios"]["sistema_tesis"]["secretos"] == []
    assert runtime["dominios"]["edge_iot"]["secretos"] == ["/etc/tesis-os/edge-iot.env"]
    assert network["default_policy"]["allow_interdomain_http"] is False
    assert network["default_policy"]["allow_cross_domain_secret_reads"] is False
    assert "salida_publicacion" in network_profiles
    assert "solo_localhost" in network_profiles
    assert all(item["network_profile"] in network_profiles for item in services["servicios"])


def test_b0_contract_manifests_and_docs_expose_desktop_first_closure() -> None:
    architecture = _load_json("manifests/system_tesis_architecture_contract.yaml")
    schema = _load_json("manifests/system_tesis_canonical_schema.yaml")
    cli = _load_json("manifests/system_tesis_cli_contracts.yaml")
    dependency_map = _load_json("manifests/system_tesis_dependency_map.yaml")
    gates = _load_json("manifests/b0_external_gates.yaml")
    objective = (ROOT / "docs/02_arquitectura/arquitectura-objetivo-b0-desktop-first.md").read_text(
        encoding="utf-8"
    )

    assert architecture["desktop_first"] is True
    assert [layer["id"] for layer in architecture["layers"]] == [
        "canon",
        "proyecciones",
        "auditoria_guardrails",
        "publicacion",
        "memoria_derivada",
    ]
    assert {item["id"] for item in architecture["surface_ownership"]} == {
        "canon",
        "proyecciones",
        "auditoria_guardrails",
        "publicacion",
        "memoria_derivada",
    }
    assert schema["schema_version"] == "1.0.0"
    assert schema["compatibility"]["breaking_change_requires_major_bump"] is True
    assert set(schema["entities"].keys()) == {
        "events",
        "state",
        "derived_artifacts",
        "traceability_views",
        "memory_summary",
    }
    assert {item["id"] for item in cli["commands"]} == {
        "status",
        "next",
        "doctor_check",
        "audit_check",
        "materialize",
        "publish_build",
        "publish_check",
        "source_status_check",
        "sync",
    }
    assert dependency_map["dependency_direction"] == "canon_hacia_derivados"
    assert "memory_projection" in {item["id"] for item in dependency_map["critical_modules"]}
    assert all(item["status"] == "pendiente_host_real" for item in gates["gates"])
    assert "ENT-013" in objective
    assert "Gates externos" in objective
