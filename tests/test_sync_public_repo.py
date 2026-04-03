from __future__ import annotations

import re
import tempfile
from pathlib import Path

from common import ROOT
from sync_public_repo import (
    _render_payloads,
    _source_map_mirror,
    bundle_fingerprint,
    sync_target,
    validate_sync_payloads,
)


def test_mirror_source_map_excludes_private_surfaces() -> None:
    source_map = _source_map_mirror(ROOT)
    assert "00_sistema_tesis/canon/events.jsonl" in source_map
    assert "00_sistema_tesis/bitacora/log_conversaciones_ia.md" in source_map
    assert "00_sistema_tesis/config/sign_offs.json" not in source_map


def test_public_sync_payloads_pass_current_policy() -> None:
    payloads = _render_payloads(_source_map_mirror(ROOT), sanitize=True)
    assert validate_sync_payloads(payloads) == []


def test_public_sync_rewrites_links_to_public_targets() -> None:
    payloads = _render_payloads(_source_map_mirror(ROOT), sanitize=True)
    bitacora_text = payloads["06_dashboard/wiki/bitacora.md"].decode("utf-8")
    pages_note_text = payloads["06_dashboard/wiki/nota_seguridad_y_acceso.md"].decode("utf-8")
    assert "[bitacora_privada]" not in bitacora_text
    assert "[reportes_privados]" not in bitacora_text
    assert "https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico/blob/main/00_sistema_tesis/bitacora/" in bitacora_text
    assert "Nota de seguridad y acceso" in pages_note_text


def test_validate_sync_payloads_rejects_placeholder_hrefs() -> None:
    errors = validate_sync_payloads({"README.md": b"[enlace](./[bitacora_privada]/archivo.md)\n"})
    assert any("href inválido" in error for error in errors)


def test_public_sync_payloads_keep_pages_guarded_to_public_repo() -> None:
    payloads = _render_payloads(_source_map_mirror(ROOT), sanitize=True)
    pages_text = payloads[".github/workflows/pages.yml"].decode("utf-8")
    assert "Dtcsrni/Sistema_Operativo_Tesis_Publico" in pages_text
    assert "refs/heads/main" in pages_text


def test_public_sync_payloads_preserve_operational_publication_regexes() -> None:
    payloads = _render_payloads(_source_map_mirror(ROOT), sanitize=True)
    publication_text = payloads["00_sistema_tesis/config/publicacion.yaml"].decode("utf-8")
    assert "[ruta_local_redactada])" not in publication_text
    assert "CUR[ruta_local_redactada]" not in publication_text
    assert "file:///[^\\\\s)\\\\]>`\\\\\\\"']+" in publication_text
    assert "CURP:\\\\s*`?[A-Z0-9]{18}`?" in publication_text
    for pattern in (
        r"file:///[^\\s)\\]>`\\\"']+",
        r"[A-Za-z]:\\\\[^\\s)\\]>`\\\"']+",
        r"VAL-STEP-[A-Za-z0-9_-]+",
        r"sha256:[0-9a-fA-F]{8,64}",
        r"CURP:\\s*`?[A-Z0-9]{18}`?",
    ):
        re.compile(pattern, re.IGNORECASE)


def test_sync_public_workflow_only_publishes_from_main() -> None:
    workflow_text = (ROOT / ".github" / "workflows" / "sync-public.yml").read_text(encoding="utf-8")
    assert "- main" in workflow_text
    assert "codex/bootstrap" not in workflow_text
    assert "github.event.workflow_run.head_branch == 'main'" in workflow_text


def test_bundle_fingerprint_is_stable_for_same_payloads() -> None:
    payloads = _render_payloads(_source_map_mirror(ROOT), sanitize=True)
    assert bundle_fingerprint(payloads) == bundle_fingerprint(payloads)


def test_sync_target_writes_matching_provenance_fingerprint() -> None:
    payloads = {"README.md": b"hola\n"}
    expected_fingerprint = bundle_fingerprint(payloads)
    with tempfile.TemporaryDirectory() as tmp_dir:
        result = sync_target(
            target_dir=Path(tmp_dir) / "publico",
            branch="main",
            repo_url="",
            payloads=payloads,
            mode="mirror",
            bundle_hash=expected_fingerprint,
            contact_email="demo@example.com",
            check=True,
            push=False,
            destination_label="public_local_mirror",
            commit_message="chore: sync test",
        )
        provenance = Path(tmp_dir, "publico", "_sync_provenance.json").read_text(encoding="utf-8")
        assert expected_fingerprint in provenance
        assert "public_local_mirror" in provenance
        assert result["bundle_fingerprint"] == expected_fingerprint
