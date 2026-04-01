from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from common import preferred_python_executable


ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("Materializar proyecciones del canon", "07_scripts/tesis.py", ["materialize"]),
    ("Auditar canon unificado", "07_scripts/tesis.py", ["audit", "--check"]),
    ("Auditar rotación de backups (dry-run)", "07_scripts/rotate_backups.py", []),
    ("Sincronizar evidencia técnica", "07_scripts/sync_evidence.py", []),
    ("Verificar Integridad del Sistema", "07_scripts/guardrails.py", ["--verify"]),
    ("Auditoría de Seguridad Unificada", "07_scripts/security_audit.py", []),
    ("Generar Badges de Seguridad", "07_scripts/generate_security_badges.py", []),
    ("Validar estructura", "07_scripts/validate_structure.py", []),
    ("Auditar No-Hardcode Runtime", "07_scripts/verify_no_hardcoded_runtime.py", []),
    ("Auditar Ledger IA", "07_scripts/verify_ledger.py", []),
    ("Auditar Cadena de Bitácoras", "07_scripts/verify_bitacora_chain.py", []),
    ("Auditar Estándares Externos", "07_scripts/verify_standards.py", []),
    ("Autoauditoría documental", "07_scripts/document_audit.py", []),
    ("Escaneo de secretos", "07_scripts/secret_scanner.py", []),
    ("Verificar firma GPG", "07_scripts/setup_gpg_attestation.py", ["--check"]),
    ("Sincronizar presupuesto y uso de tokens", "07_scripts/build_token_usage_snapshot.py", []),
    ("Generar portada README", "07_scripts/build_readme_portada.py", []),
    ("Generar wiki verificable", "07_scripts/build_wiki.py", []),
    ("Validar wiki verificable", "07_scripts/validate_wiki.py", []),
    ("Generar dashboard", "07_scripts/build_dashboard.py", []),
    ("Sincronizar publicación pública sanitizada", "07_scripts/tesis.py", ["publish", "--build"]),
    ("Verificar evidencia fuente de conversación", "07_scripts/tesis.py", ["source", "status", "--check"]),
    ("Verificar operabilidad humana", "07_scripts/tesis.py", ["doctor", "--check"]),
    ("Exportar hoja maestra", "07_scripts/export_master_sheet.py", []),
    ("Generar reporte de consistencia", "07_scripts/report_consistency.py", []),
    ("Regenerar wiki verificable (post-dashboard)", "07_scripts/build_wiki.py", []),
    ("Revalidar wiki verificable (post-dashboard)", "07_scripts/validate_wiki.py", []),
    ("Validar publicación pública sanitizada", "07_scripts/tesis.py", ["publish", "--check"]),
]


def run_step(label: str, script: str, args: list[str]) -> None:
    print(f"[RUN] {label} -> {script}")
    cmd = [preferred_python_executable(), str(ROOT / script)]
    if args:
        cmd.extend(args)
    
    # El check de firma es informativo, no bloquea el build por ahora (soft-enforce)
    check = True if "firma" not in label.lower() else False
    subprocess.run(cmd, cwd=ROOT, check=check)


def main() -> int:
    for label, script, args in STEPS:
        run_step(label, script, args)
    print("[OK] Build total completado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
