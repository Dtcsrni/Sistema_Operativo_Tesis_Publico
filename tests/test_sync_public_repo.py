from __future__ import annotations

import re

from common import ROOT
from sync_public_repo import _render_payloads, _source_map_mirror, validate_sync_payloads


def test_mirror_source_map_excludes_private_surfaces() -> None:
    source_map = _source_map_mirror(ROOT)
    assert "00_sistema_tesis/canon/events.jsonl" not in source_map
    assert "00_sistema_tesis/bitacora/log_conversaciones_ia.md" not in source_map
    assert "00_sistema_tesis/config/sign_offs.json" not in source_map


def test_public_sync_payloads_pass_current_policy() -> None:
    payloads = _render_payloads(_source_map_mirror(ROOT), sanitize=True)
    assert validate_sync_payloads(payloads) == []


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
