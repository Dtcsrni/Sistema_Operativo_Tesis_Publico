from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_desktop_edge_sync_contract_declares_expected_nodes_and_strategy() -> None:
    payload = _load_json("manifests/desktop_edge_sync_contract.yaml")

    assert payload["source_node"] == "desktop_vscode"
    assert payload["target_node"] == "orange_pi"
    assert payload["sync_strategy"] == "git_pull_ff_only_plus_explicit_artifacts"
    assert payload["repo_target_on_edge"] == "/srv/tesis/repo"
    assert {profile["id"] for profile in payload["sync_profiles"]} == {
        "repo-only",
        "repo+postcheck",
        "repo+restart-edge",
    }
    assert "edge_cleanup_paths" in payload
    assert "00_sistema_tesis/evidencia_privada/staging_ingestion" in payload["edge_cleanup_paths"]
    assert "edicion_primaria_en_orange_pi" in payload["forbidden_flows"]
    assert "git_pull_no_fast_forward_en_edge" in payload["forbidden_flows"]


def test_desktop_edge_flow_doc_describes_sequence_and_paths() -> None:
    doc = (ROOT / "docs/03_operacion/flujo-escritorio-orange-pi.md").read_text(encoding="utf-8")

    assert "desktop_workspace" in doc
    assert "Orange Pi" in doc
    assert "sync_repo_desde_desktop.sh" in doc
    assert "pull --ff-only" in doc
    assert "/srv/tesis/repo" in doc
    assert "/srv/tesis/intercambio/edge/spool" in doc
    assert "repo+postcheck" in doc
    assert "repo+restart-edge" in doc
    assert "ruido edge-volatil" in doc


def test_orangepi_sync_helper_uses_profiles_fast_forward_audit_and_restart() -> None:
    script = (ROOT / "ops/actualizacion/sync_repo_desde_desktop.sh").read_text(encoding="utf-8")

    assert "git -C \"${REPO_ROOT}\" fetch \"${SYNC_REMOTE}\" \"${SYNC_BRANCH}\" --prune" in script
    assert "git -C \"${REPO_ROOT}\" pull --ff-only \"${SYNC_REMOTE}\" \"${SYNC_BRANCH}\"" in script
    assert "\"${PYTHON_BIN}\" \"${REPO_ROOT}/07_scripts/tesis.py\" audit --check" in script
    assert "bash \"${REPO_ROOT}/bootstrap/orangepi/90_postcheck.sh\"" in script
    assert "cleanup_edge_noise" in script
    assert "EDGE_NOISE_PATTERNS" in script
    assert "repo-only)" in script
    assert "repo+postcheck)" in script
    assert "repo+restart-edge)" in script
    assert "systemctl restart \"${EDGE_SERVICE_NAME}\"" in script


def test_manual_and_interconnections_reference_desktop_edge_flow() -> None:
    manual = (ROOT / "00_sistema_tesis/manual_operacion_humana.md").read_text(encoding="utf-8")
    interconnections = (ROOT / "docs/02_arquitectura/mapa-de-interconexiones.md").read_text(encoding="utf-8")

    assert "flujo-escritorio-orange-pi.md" in manual
    assert "sync_repo_desde_desktop.sh" in manual
    assert "repo+restart-edge" in manual
    assert "desktop_workspace" in interconnections
    assert "/srv/tesis/repo" in interconnections
    assert "/srv/tesis/intercambio/edge" in interconnections
    assert "repo+postcheck" in interconnections
