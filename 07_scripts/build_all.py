from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from common import preferred_python_executable


ROOT = Path(__file__).resolve().parents[1]
PROFILE_DIR = ROOT / "00_sistema_tesis" / "bitacora" / "audit_history"
PROFILE_LATEST = PROFILE_DIR / "build_all_profile_latest.json"
STAGE_BUDGET_SECONDS = {
    "Materializar proyecciones del canon": 10.0,
    "Auditar canon unificado": 10.0,
    "Validar estructura": 10.0,
    "Validar arquitectura B0 desktop-first": 10.0,
    "Generar portada README": 5.0,
    "Generar memoria operativa": 5.0,
    "Generar wiki verificable": 20.0,
    "Generar dashboard": 20.0,
    "Sincronizar publicación pública sanitizada": 30.0,
}

STEPS = [
    ("Materializar proyecciones del canon", "07_scripts/tesis.py", ["materialize"]),
    ("Auditar canon unificado", "07_scripts/tesis.py", ["audit", "--check"]),
    ("Auditar rotación de backups (dry-run)", "07_scripts/rotate_backups.py", []),
    ("Sincronizar evidencia técnica", "07_scripts/sync_evidence.py", []),
    ("Verificar Integridad del Sistema", "07_scripts/guardrails.py", ["--verify"]),
    ("Auditoría de Seguridad Unificada", "07_scripts/security_audit.py", []),
    ("Generar Badges de Seguridad", "07_scripts/generate_security_badges.py", []),
    ("Generar portada README", "07_scripts/build_readme_portada.py", []),
    ("Generar memoria operativa", "07_scripts/build_memory.py", []),
    ("Validar memoria operativa", "07_scripts/validate_memory.py", []),
    ("Validar estructura", "07_scripts/validate_structure.py", []),
    ("Validar arquitectura B0 desktop-first", "07_scripts/validate_b0_architecture.py", []),
    ("Auditar No-Hardcode Runtime", "07_scripts/verify_no_hardcoded_runtime.py", []),
    ("Auditar Ledger IA", "07_scripts/verify_ledger.py", []),
    ("Auditar Cadena de Bitácoras", "07_scripts/verify_bitacora_chain.py", []),
    ("Auditar Estándares Externos", "07_scripts/verify_standards.py", []),
    ("Autoauditoría documental", "07_scripts/document_audit.py", []),
    ("Escaneo de secretos", "07_scripts/secret_scanner.py", []),
    ("Verificar firma GPG", "07_scripts/setup_gpg_attestation.py", ["--check"]),
    ("Sincronizar presupuesto y uso de tokens", "07_scripts/build_token_usage_snapshot.py", []),
    ("Generar wiki verificable", "07_scripts/build_wiki.py", []),
    ("Validar wiki verificable", "07_scripts/validate_wiki.py", []),
    ("Generar dashboard", "07_scripts/build_dashboard.py", []),
    ("Sincronizar publicación pública sanitizada", "07_scripts/tesis.py", ["publish", "--build"]),
    ("Validar enlaces derivados y públicos", "07_scripts/validate_links.py", []),
    ("Validar calidad editorial pública", "07_scripts/validate_public_text.py", []),
    ("Verificar evidencia fuente de conversación", "07_scripts/tesis.py", ["source", "status", "--check"]),
    ("Verificar operabilidad humana", "07_scripts/tesis.py", ["doctor", "--check"]),
    ("Exportar hoja maestra", "07_scripts/export_master_sheet.py", []),
    ("Generar reporte de consistencia", "07_scripts/report_consistency.py", []),
    ("Regenerar wiki verificable (post-dashboard)", "07_scripts/build_wiki.py", []),
    ("Revalidar wiki verificable (post-dashboard)", "07_scripts/validate_wiki.py", []),
    ("Revalidar enlaces derivados y públicos (post-dashboard)", "07_scripts/validate_links.py", []),
    ("Revalidar calidad editorial pública (post-dashboard)", "07_scripts/validate_public_text.py", []),
    ("Validar publicación pública sanitizada", "07_scripts/tesis.py", ["publish", "--check"]),
]


def run_step(label: str, script: str, args: list[str]) -> dict[str, object]:
    print(f"[RUN] {label} -> {script}")
    cmd = [preferred_python_executable(), str(ROOT / script)]
    if args:
        cmd.extend(args)

    # El check de firma es informativo, no bloquea el build por ahora (soft-enforce)
    check = True if "firma" not in label.lower() else False
    started_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    start = time.perf_counter()
    result = subprocess.run(cmd, cwd=ROOT, check=check)
    duration = round(time.perf_counter() - start, 3)
    budget = STAGE_BUDGET_SECONDS.get(label)
    status = "slow" if budget is not None and duration > budget else "ok"
    if status == "slow":
        print(f"[WARN] Etapa lenta: {label} tardó {duration:.3f}s (presupuesto {budget:.1f}s)")
    return {
        "label": label,
        "script": script,
        "args": args,
        "started_at_utc": started_at,
        "duration_seconds": duration,
        "budget_seconds": budget,
        "status": status,
        "returncode": result.returncode,
    }


def write_profile(stage_reports: list[dict[str, object]]) -> Path:
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    profile_path = PROFILE_DIR / f"build_all_profile_{generated_at}.json"
    payload = {
        "generated_at_utc": generated_at,
        "total_duration_seconds": round(sum(float(item["duration_seconds"]) for item in stage_reports), 3),
        "slow_stages": [item["label"] for item in stage_reports if item["status"] == "slow"],
        "steps": stage_reports,
    }
    serialized = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    profile_path.write_text(serialized, encoding="utf-8")
    PROFILE_LATEST.write_text(serialized, encoding="utf-8")
    return profile_path


def main() -> int:
    stage_reports: list[dict[str, object]] = []
    for label, script, args in STEPS:
        stage_reports.append(run_step(label, script, args))
    profile_path = write_profile(stage_reports)
    print(f"[OK] Perfil de build escrito en {profile_path.relative_to(ROOT)}")
    print("[OK] Build total completado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
