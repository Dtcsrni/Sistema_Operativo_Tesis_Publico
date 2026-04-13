from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_domain_backup_policy_declares_expected_domains_and_artifacts() -> None:
    policy = _load_json("manifests/domain_backup_policy.yaml")

    assert policy["format"] == "mixed_tar_snapshot"
    assert policy["encryption"] == "none_permissions_only"
    assert {"sistema_tesis", "openclaw", "edge_iot"} == set(policy["domains"].keys())
    assert policy["domains"]["openclaw"]["snapshot_dir"] == "/mnt/emmc/snapshots/openclaw"


def test_backup_service_and_storage_layout_include_domain_backup_contracts() -> None:
    service = (ROOT / "config/systemd/tesis-backup.service").read_text(encoding="utf-8")
    storage = _load_json("manifests/storage_layout.yaml")
    matrix = _load_json("manifests/service_matrix.yaml")
    services = {item["id"]: item for item in matrix["servicios"]}

    assert "EnvironmentFile=/etc/tesis-os/backup.env" in service
    assert "/mnt/emmc/snapshots" in service
    assert storage["politicas"]["backups_por_dominio"] is True
    assert storage["respaldo"]["policy"] == "/etc/tesis-os/policies/domain_backup_policy.yaml"
    assert "/mnt/emmc/snapshots" in services["tesis-backup"]["read_write_paths"]


def test_backup_and_restore_scripts_distinguish_verify_sandbox_and_in_place() -> None:
    backup = (ROOT / "ops/respaldo/ejecutar_respaldo.sh").read_text(encoding="utf-8")
    verify = (ROOT / "ops/respaldo/verificar_respaldos.sh").read_text(encoding="utf-8")
    restore = (ROOT / "ops/recuperacion/restaurar_desde_emmc.sh").read_text(encoding="utf-8")
    report = (ROOT / "ops/recuperacion/reporte_restauracion.sh").read_text(encoding="utf-8")

    assert "domain_backup_policy.yaml" in backup or "TESIS_BACKUP_POLICY" in backup
    assert "VERIFY_OK:" in verify
    assert "--mode sandbox|in_place" in restore
    assert "RESTORE_FAIL:in_place_requires_allow_flag" in restore
    assert "RESTORE_FAIL:domain_manifest_mismatch" in restore
    assert "restore_" in report


def test_docs_and_postcheck_include_domain_backup_flow() -> None:
    flow = (ROOT / "00_sistema_tesis/documentacion_sistema/flujos_operativos.md").read_text(encoding="utf-8")
    doc = (ROOT / "docs/03_operacion/respaldo-y-restauracion-por-dominio.md").read_text(encoding="utf-8")
    postcheck = (ROOT / "bootstrap/orangepi/90_postcheck.sh").read_text(encoding="utf-8")
    smoke = (ROOT / "tests/smoke/test_domain_backup.sh").read_text(encoding="utf-8")

    assert "Flujo 9. Respaldar y restaurar por dominio" in flow
    assert "restore in-place controlado" in doc.lower()
    assert "test_domain_backup.sh" in postcheck
    assert "domain_backup_policy.yaml" in smoke
