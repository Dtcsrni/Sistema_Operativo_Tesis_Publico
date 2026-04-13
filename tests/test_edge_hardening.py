from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_edge_hardening_policy_declares_expected_controls() -> None:
    payload = _load_json("manifests/edge_iot_hardening_policy.yaml")
    baseline = payload["baseline"]

    assert payload["domain"] == "edge_iot"
    assert baseline["firewall_enabled"] is True
    assert baseline["fail2ban_enabled"] is True
    assert baseline["allow_root_login"] is False
    assert baseline["password_authentication"] is False
    assert baseline["edge_runtime_user"] == "edgeiot"


def test_edge_hardening_bootstrap_installs_policy_and_ssh_dropin() -> None:
    script = (ROOT / "bootstrap/orangepi/51_hardening-edge-iot.sh").read_text(encoding="utf-8")

    assert "edge_iot_hardening_policy.yaml" in script
    assert "ufw default deny incoming" in script
    assert "ufw allow ssh" in script
    assert "fail2ban" in script
    assert "PermitRootLogin no" in script
    assert "PasswordAuthentication no" in script


def test_postcheck_runs_edge_hardening_smoke() -> None:
    script = (ROOT / "bootstrap/orangepi/90_postcheck.sh").read_text(encoding="utf-8")
    smoke = (ROOT / "tests/smoke/test_edge_hardening.sh").read_text(encoding="utf-8")

    assert "test_edge_hardening.sh" in script
    assert "ufw status" in smoke
    assert "systemctl is-enabled fail2ban" in smoke


def test_edge_hardening_documentation_matches_policy() -> None:
    doc = (ROOT / "docs/04_seguridad/hardening-edge-iot.md").read_text(encoding="utf-8")

    assert "ufw" in doc
    assert "fail2ban" in doc
    assert "ssh" in doc
    assert "T-032" in doc
