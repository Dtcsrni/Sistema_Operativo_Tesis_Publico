from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_RUNS = ROOT / "00_sistema_tesis" / "bitacora" / "audit_history" / "harness_runs.jsonl"
PRIVATE_READINESS = ROOT / "00_sistema_tesis" / "config" / "harness_readiness.json"
PUBLIC_READINESS = ROOT / "06_dashboard" / "generado" / "harness_readiness_public.json"

PRIVATE_PREFIXES = (
    "00_sistema_tesis/evidencia_privada/",
    "config/env/",
    ".env",
)

SUBSYSTEMS = {
    "canon": ["00_sistema_tesis/canon/events.jsonl", "00_sistema_tesis/bitacora/matriz_trazabilidad.md"],
    "documentacion": ["docs/02_arquitectura/arquitectura-general.md", "06_dashboard/wiki/index.md"],
    "openclaw": ["runtime/openclaw", "00_sistema_tesis/config/openclaw_status.json"],
    "mission_control": ["04_implementacion/control_mission/package.json"],
    "toltecayotl": ["07_scripts/toltecayotl", "00_sistema_tesis/config/toltecayotl_status.json"],
    "publicacion": ["06_dashboard/generado/harness_readiness_public.json"],
    "ci_cd": [".github/workflows"],
    "git": [".git"],
}


@dataclass(frozen=True)
class HarnessManifest:
    schema_version: str = "siot-harness-v1"
    harness_id: str = "siot-agentic-harness"
    scope: str = "whole_siot"
    provider_agnostic: bool = True
    privacy_default: str = "canonical_private"
    telemetry_mode: str = "local_sanitized"
    dimensions: list[str] = field(default_factory=lambda: [
        "workflow_success",
        "policy_compliance",
        "traceability",
        "reproducibility",
        "security",
        "epistemic_quality",
        "cost_latency",
    ])
    subsystems: dict[str, list[str]] = field(default_factory=lambda: SUBSYSTEMS)
    required_gates: list[str] = field(default_factory=lambda: [
        "secret_scanner",
        "build_all",
        "publish_check",
        "harness_verify",
    ])


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sanitize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if any(normalized == prefix.rstrip("/") or normalized.startswith(prefix) for prefix in PRIVATE_PREFIXES):
        return "[redacted]"
    return normalized


def manifest() -> dict[str, Any]:
    payload = asdict(HarnessManifest())
    payload["created_at"] = utc_now()
    payload["agent"] = {
        "role": os.getenv("SISTEMA_TESIS_AGENT_ROLE", "agnostic_agent"),
        "provider": os.getenv("SISTEMA_TESIS_AGENT_PROVIDER", "unspecified"),
        "model": os.getenv("SISTEMA_TESIS_AGENT_MODEL_VERSION", "unspecified"),
        "runtime": os.getenv("SISTEMA_TESIS_AGENT_RUNTIME", "local_cli"),
    }
    return payload


def git_snapshot() -> dict[str, Any]:
    def run(args: list[str]) -> str:
        result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
        return result.stdout.strip()

    return {
        "branch": run(["branch", "--show-current"]),
        "head": run(["rev-parse", "--short=12", "HEAD"]),
        "status_short": run(["status", "--short", "--branch"]),
        "remote": run(["remote", "-v"]),
    }


def record(source: str, profile: str | None = None, status: str = "observed") -> dict[str, Any]:
    artifacts = []
    if profile:
        profile_path = (ROOT / profile).resolve() if not Path(profile).is_absolute() else Path(profile)
        artifacts.append({
            "path": sanitize_path(rel(profile_path)),
            "sha256": sha256_file(profile_path),
        })
    run_id = f"HARNESS-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{hashlib.sha256((source + utc_now()).encode()).hexdigest()[:8]}"
    payload = {
        "schema_version": "siot-harness-run-v1",
        "run_id": run_id,
        "harness_id": "siot-agentic-harness",
        "created_at": utc_now(),
        "source": source,
        "status": status,
        "git": git_snapshot(),
        "artifacts": artifacts,
    }
    PRIVATE_RUNS.parent.mkdir(parents=True, exist_ok=True)
    with PRIVATE_RUNS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload


def _latest_build_profile() -> Path | None:
    path = ROOT / "00_sistema_tesis" / "bitacora" / "audit_history" / "build_all_profile_latest.json"
    return path if path.exists() else None


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def score() -> dict[str, Any]:
    findings: list[str] = []
    dimensions = {
        "workflow_success": 0,
        "policy_compliance": 100,
        "traceability": 100,
        "reproducibility": 100,
        "security": 100,
        "epistemic_quality": 80,
        "cost_latency": 80,
    }
    profile = _latest_build_profile()
    if profile:
        data = _load_json(profile)
        summary = data.get("summary", {})
        failed = int(summary.get("failed", 0) or 0)
        total = max(int(summary.get("total", 1) or 1), 1)
        dimensions["workflow_success"] = max(0, round(100 * (total - failed) / total))
        if failed:
            findings.append("build_all_profile_latest contiene pasos fallidos")
        if data.get("slow_stages"):
            dimensions["cost_latency"] = 70
    else:
        findings.append("no existe build_all_profile_latest.json")

    required = [
        ROOT / "07_scripts" / "ops" / "run_tests_smart.py",
        ROOT / "07_scripts" / "build_all.py",
        ROOT / "00_sistema_tesis" / "bitacora" / "matriz_trazabilidad.md",
        ROOT / "00_sistema_tesis" / "config" / "security_report.json",
    ]
    missing = [rel(path) for path in required if not path.exists()]
    if missing:
        dimensions["reproducibility"] = 60
        findings.extend(f"artefacto requerido ausente: {item}" for item in missing)

    readiness_score = round(sum(dimensions.values()) / len(dimensions))
    status = "ok" if readiness_score >= 85 and not findings else ("degraded" if readiness_score >= 70 else "failed")
    payload = {
        "schema_version": "siot-harness-readiness-v1",
        "generated_at": utc_now(),
        "status": status,
        "readiness_score": readiness_score,
        "dimensions": dimensions,
        "policy_findings": findings,
        "evidence": {
            "latest_build_profile": rel(profile) if profile else None,
            "harness_runs": rel(PRIVATE_RUNS),
        },
    }
    PRIVATE_READINESS.parent.mkdir(parents=True, exist_ok=True)
    PRIVATE_READINESS.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    public_payload = dict(payload)
    public_payload["evidence"] = {key: sanitize_path(str(value)) for key, value in payload["evidence"].items()}
    PUBLIC_READINESS.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_READINESS.write_text(json.dumps(public_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def verify() -> dict[str, Any]:
    m = manifest()
    readiness = score()
    checks = {
        "manifest_has_subsystems": bool(m.get("subsystems")),
        "readiness_json_exists": PRIVATE_READINESS.exists(),
        "public_json_exists": PUBLIC_READINESS.exists(),
        "no_private_public_paths": "[redacted]" not in PUBLIC_READINESS.read_text(encoding="utf-8"),
    }
    ok = all(checks.values()) and readiness["status"] in {"ok", "degraded"}
    payload = {"ok": ok, "checks": checks, "readiness": readiness}
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Harness engineering agnostico de SIOT.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("manifest", "score", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--json", action="store_true")
    p_record = sub.add_parser("record")
    p_record.add_argument("--source", required=True)
    p_record.add_argument("--profile")
    p_record.add_argument("--status", default="observed")
    p_record.add_argument("--json", action="store_true")
    p_report = sub.add_parser("report")
    p_report.add_argument("--public-json", action="store_true")
    p_report.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.cmd == "manifest":
        payload = manifest()
    elif args.cmd == "record":
        payload = record(args.source, args.profile, args.status)
    elif args.cmd == "score":
        payload = score()
    elif args.cmd == "verify":
        payload = verify()
    elif args.cmd == "report":
        payload = json.loads(PUBLIC_READINESS.read_text(encoding="utf-8")) if args.public_json and PUBLIC_READINESS.exists() else score()
    else:
        raise AssertionError(args.cmd)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if payload.get("ok", True) is not False else 1


if __name__ == "__main__":
    raise SystemExit(main())
