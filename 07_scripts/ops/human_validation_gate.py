from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "07_scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from serena.serena_policy import (  # noqa: E402
    SOURCE_EVENT_PATTERN,
    STEP_ID_PATTERN,
    normalize_rel_path,
    source_evidence_required,
    validate_step_and_source,
)

SIGN_OFFS_PATH = ROOT / "00_sistema_tesis" / "config" / "sign_offs.json"


@dataclass(frozen=True)
class Probe:
    available: bool
    recommended: bool
    reason: str
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "recommended": self.recommended,
            "reason": self.reason,
            "details": self.details,
        }


def sha256_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_probe(command: list[str], *, timeout: int = 8) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def load_signoffs(path: Path = SIGN_OFFS_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    items = payload.get("sign_offs", [])
    return list(items) if isinstance(items, list) else []


def signoff_status(paths: list[str], *, root: Path = ROOT, signoffs_path: Path = SIGN_OFFS_PATH) -> list[dict[str, Any]]:
    index: dict[str, str] = {}
    for record in load_signoffs(signoffs_path):
        rel = normalize_rel_path(str(record.get("archivo", "")))
        expected = str(record.get("hash_verificado", "")).strip()
        if rel and expected:
            index[rel] = expected

    statuses: list[dict[str, Any]] = []
    for raw_path in paths:
        rel = normalize_rel_path(raw_path)
        target = root / rel
        current_hash = sha256_file(target) if target.exists() and target.is_file() else ""
        expected_hash = index.get(rel, "")
        if not target.exists():
            state = "missing"
        elif not expected_hash:
            state = "unsigned"
        elif current_hash == expected_hash:
            state = "current"
        else:
            state = "drift"
        statuses.append(
            {
                "path": rel,
                "state": state,
                "current_hash": current_hash,
                "signed_hash": expected_hash,
            }
        )
    return statuses


def gpg_probe() -> Probe:
    gpg = shutil.which("gpg")
    if not gpg:
        return Probe(False, False, "gpg_not_in_path", {})
    version = run_probe([gpg, "--version"])
    keys = run_probe([gpg, "--list-secret-keys", "--with-colons"])
    secret_key_count = 0
    if keys and keys.returncode == 0:
        secret_key_count = sum(1 for line in keys.stdout.splitlines() if line.startswith("sec"))
    git_sign = run_probe(["git", "config", "--get", "commit.gpgsign"])
    signing_key = run_probe(["git", "config", "--get", "user.signingkey"])
    configured = bool(git_sign and git_sign.stdout.strip().lower() == "true")
    has_key = secret_key_count > 0
    return Probe(
        available=has_key,
        recommended=has_key and configured,
        reason="ok" if has_key and configured else ("gpg_secret_key_missing" if not has_key else "git_gpgsign_not_enabled"),
        details={
            "program": gpg,
            "version": (version.stdout.splitlines()[0] if version and version.stdout else ""),
            "secret_key_count": secret_key_count,
            "git_commit_gpgsign": git_sign.stdout.strip() if git_sign else "",
            "git_user_signingkey": signing_key.stdout.strip() if signing_key else "",
        },
    )


def windows_hello_probe() -> Probe:
    powershell = shutil.which("powershell.exe") or shutil.which("pwsh.exe")
    if not powershell:
        return Probe(
            False,
            False,
            "windows_shell_not_visible_from_host",
            {"integration_mode": "not_directly_available_from_this_runtime"},
        )
    command = [
        powershell,
        "-NoProfile",
        "-NonInteractive",
        "-Command",
        (
            "$certs = @(Get-ChildItem Cert:\\CurrentUser\\My -ErrorAction SilentlyContinue "
            "| Where-Object { $_.HasPrivateKey -and $_.EnhancedKeyUsageList.FriendlyName -contains 'Code Signing' }); "
            "[Console]::Out.Write($certs.Count)"
        ),
    ]
    result = run_probe(command)
    count = 0
    if result and result.returncode == 0 and result.stdout.strip().isdigit():
        count = int(result.stdout.strip())
    available = count > 0
    return Probe(
        available=available,
        recommended=False,
        reason="code_signing_certificate_visible" if available else "no_windows_hello_backed_signing_contract_detected",
        details={
            "windows_shell": powershell,
            "code_signing_cert_count": count,
            "integration_mode": "candidate_attestation_only",
            "recommendation": (
                "Use Windows Hello only to unlock a Windows-held key that signs an approval attestation; "
                "Step ID and source evidence remain canonical."
            ),
        },
    )


def validate_human_inputs(*, step_id: str, source_event_id: str, confirmation_text: str, root: Path = ROOT) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    normalized_step = step_id.strip()
    normalized_source = source_event_id.strip()

    if not normalized_step:
        errors.append("missing_step_id")
    elif not STEP_ID_PATTERN.match(normalized_step):
        errors.append("invalid_step_id_format")
    else:
        errors.extend(validate_step_and_source(step_id=normalized_step, source_event_id=normalized_source, root=root))

    if normalized_source and not SOURCE_EVENT_PATTERN.match(normalized_source):
        errors.append("invalid_source_event_id_format")

    requires_source = bool(normalized_step) and source_evidence_required(normalized_step, root)
    if requires_source and not normalized_source:
        errors.append("missing_source_event_id")

    if not confirmation_text.strip():
        warnings.append("confirmation_text_missing")

    return {
        "step_id": normalized_step,
        "source_event_id": normalized_source,
        "requires_source_event_id": requires_source,
        "confirmation_text_hash": sha256_text(confirmation_text) if confirmation_text.strip() else "",
        "errors": sorted(set(errors)),
        "warnings": warnings,
    }


def build_report(
    *,
    step_id: str = "",
    source_event_id: str = "",
    confirmation_text: str = "",
    paths: list[str] | None = None,
    root: Path = ROOT,
    signoffs_path: Path = SIGN_OFFS_PATH,
) -> dict[str, Any]:
    target_paths = [normalize_rel_path(path) for path in (paths or []) if path.strip()]
    validation = validate_human_inputs(
        step_id=step_id,
        source_event_id=source_event_id,
        confirmation_text=confirmation_text,
        root=root,
    )
    signoffs = signoff_status(target_paths, root=root, signoffs_path=signoffs_path) if target_paths else []
    gpg = gpg_probe().to_dict()
    hello = windows_hello_probe().to_dict()

    blocking = list(validation["errors"])
    drift = [item["path"] for item in signoffs if item["state"] in {"unsigned", "drift", "missing"}]
    if drift:
        blocking.append("signoff_drift_or_missing")

    status = "blocked" if blocking else ("degraded" if validation["warnings"] or not gpg["recommended"] else "ok")
    next_action = "none"
    if "missing_step_id" in blocking:
        next_action = "request_human_step_id"
    elif "missing_source_event_id" in blocking:
        next_action = "register_or_link_conversation_source_event"
    elif "signoff_drift_or_missing" in blocking:
        next_action = "run_controlled_signoff_after_human_approval"
    elif not gpg["recommended"]:
        next_action = "repair_gpg_or_use_attestation_fallback"

    return {
        "status": status,
        "available": status != "blocked",
        "recommended": status == "ok",
        "blocking_reason": ",".join(blocking),
        "affected_paths": target_paths,
        "required_step_id": validation["step_id"] or "PENDIENTE",
        "next_action": next_action,
        "details": {
            "mode": "dry_run_no_canon_mutation",
            "validation": validation,
            "signoffs": signoffs,
            "auth_methods": {
                "gpg": gpg,
                "windows_hello": hello,
            },
            "windows_hello_decision": {
                "possible": bool(hello["available"]),
                "recommended_now": False,
                "reason": (
                    "Windows Hello can make the local approval smoother only as an unlock factor for a "
                    "Windows-held signing key. It should not replace Step ID, source evidence, or canonical "
                    "human_validation events."
                ),
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate dry-run para preparar validacion humana sin mutar canon.")
    parser.add_argument("--json", action="store_true", help="Emitir JSON.")
    parser.add_argument("--step-id", default="", help="Step ID humano VAL-STEP-XXX.")
    parser.add_argument("--source-event-id", default="", help="EVT-XXX de fuente conversacional.")
    parser.add_argument("--confirmation-text", default="", help="Texto exacto de confirmacion humana.")
    parser.add_argument("--path", action="append", default=[], help="Ruta a evaluar. Repetible.")
    args = parser.parse_args()

    report = build_report(
        step_id=args.step_id,
        source_event_id=args.source_event_id,
        confirmation_text=args.confirmation_text,
        paths=args.path,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"HUMAN VALIDATION: {report['status']} next={report['next_action']}")
        if report["blocking_reason"]:
            print(f"blocking_reason={report['blocking_reason']}")
    return 0 if report["status"] in {"ok", "degraded"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
