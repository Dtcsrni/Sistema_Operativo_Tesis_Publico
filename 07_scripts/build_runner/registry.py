"""build_runner/registry.py — Catálogo centralizado de pasos del build.

Cada paso declara:
  - label:      Nombre legible (usado en logs y perfiles)
  - script:     Ruta relativa al script desde ROOT
  - args:       Argumentos extra al script
  - group:      Grupo lógico al que pertenece el paso
  - tags:       Etiquetas para filtrado (ej. --only audit)
  - watch:      Rutas/globs que, al cambiar, invalidan el caché de este paso
  - soft_fail:  Si True, un fallo no detiene el build
  - budget_s:   Tiempo máximo esperado en segundos (para advertencia de lentitud)
  - skip_if:    Callable opcional que retorna True si el paso debe omitirse
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class BuildStep:
    label: str
    script: str
    args: list[str] = field(default_factory=list)
    group: str = "misc"
    tags: list[str] = field(default_factory=list)
    watch: list[str] = field(default_factory=list)
    soft_fail: bool = False
    budget_s: float | None = None
    skip_if: Callable[[], bool] | None = None


# ── Registro completo de pasos ─────────────────────────────────────────────────
# Orden es el orden de ejecución por defecto.
# Las dependencias implícitas se garantizan por orden (ej. canon antes de audit).

STEPS: list[BuildStep] = [

    # ── Grupo: canon ──────────────────────────────────────────────────────────
    BuildStep(
        label="Materializar proyecciones del canon",
        script="07_scripts/tesis.py",
        args=["materialize"],
        group="canon",
        tags=["canon", "core"],
        watch=["00_sistema_tesis/canon/**", "00_sistema_tesis/config/**"],
        budget_s=10.0,
    ),
    BuildStep(
        label="Auditar canon unificado",
        script="07_scripts/tesis.py",
        args=["audit", "--check"],
        group="canon",
        tags=["canon", "audit", "core"],
        watch=["00_sistema_tesis/canon/**"],
        budget_s=10.0,
    ),

    # ── Grupo: integridad ─────────────────────────────────────────────────────
    BuildStep(
        label="Verificar Integridad del Sistema",
        script="07_scripts/audit/guardrails.py",
        args=["--verify"],
        group="integridad",
        tags=["integrity", "security"],
        watch=["00_sistema_tesis/**", "runtime/**"],
    ),
    BuildStep(
        label="Auditar bypass de rutas públicas",
        script="07_scripts/audit/audit_public_paths.py",
        group="integridad",
        tags=["integrity", "security", "code"],
        watch=["07_scripts/**/*.py"],
    ),
    BuildStep(
        label="Auditar integridad de bases SQLite",
        script="07_scripts/audit/audit_sqlite_integrity.py",
        group="integridad",
        tags=["integrity", "db"],
        watch=["**/*.db", "**/*.sqlite"],
    ),
    BuildStep(
        label="Auditar No-Hardcode Runtime",
        script="07_scripts/audit/verify_no_hardcoded_runtime.py",
        group="integridad",
        tags=["integrity", "code"],
        watch=["runtime/**"],
    ),
    BuildStep(
        label="Auditar Ledger IA",
        script="07_scripts/audit/verify_ledger.py",
        group="integridad",
        tags=["integrity", "ledger", "audit"],
        watch=["00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md"],
    ),
    BuildStep(
        label="Auditar integridad DEC/VAL",
        script="07_scripts/audit/verify_decisions_val_integrity.py",
        group="integridad",
        tags=["integrity", "decisions", "ledger", "audit"],
        watch=[
            "00_sistema_tesis/decisiones/**",
            "00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md",
            "00_sistema_tesis/bitacora/matriz_trazabilidad.md",
            "00_sistema_tesis/canon/events.jsonl",
        ],
    ),
    BuildStep(
        label="Auditar Cadena de Bitácoras",
        script="07_scripts/audit/verify_bitacora_chain.py",
        group="integridad",
        tags=["integrity", "ledger"],
        watch=["00_sistema_tesis/bitacora/**"],
    ),
    BuildStep(
        label="Auditar calidad de trazabilidad",
        script="07_scripts/audit/verify_traceability_quality.py",
        args=["--strict"],
        group="integridad",
        tags=["integrity", "audit"],
        watch=["00_sistema_tesis/bitacora/**", "00_sistema_tesis/decisiones/**"],
    ),
    BuildStep(
        label="Autoauditoría documental",
        script="07_scripts/audit/document_audit.py",
        group="integridad",
        tags=["audit", "docs"],
        watch=["00_sistema_tesis/**", "01_planeacion/**"],
    ),

    # ── Grupo: seguridad ──────────────────────────────────────────────────────
    BuildStep(
        label="Auditoría de Seguridad Unificada",
        script="07_scripts/audit/security_audit.py",
        group="seguridad",
        tags=["security"],
        watch=["runtime/**", "07_scripts/**"],
    ),
    BuildStep(
        label="Generar Badges de Seguridad",
        script="07_scripts/utils/generate_security_badges.py",
        group="seguridad",
        tags=["security", "generate"],
        watch=["07_scripts/audit/security_audit.py"],
    ),
    BuildStep(
        label="Escaneo de secretos",
        script="07_scripts/audit/secret_scanner.py",
        group="seguridad",
        tags=["security"],
        watch=["**/*.py", "**/*.json", "**/*.env*"],
    ),
    BuildStep(
        label="Verificar firma GPG",
        script="07_scripts/utils/setup_gpg_attestation.py",
        args=["--check"],
        group="seguridad",
        tags=["security"],
        soft_fail=True,
    ),

    # ── Grupo: estructura ─────────────────────────────────────────────────────
    BuildStep(
        label="Validar estructura",
        script="07_scripts/audit/validate_structure.py",
        group="estructura",
        tags=["validate", "structure"],
        watch=["00_sistema_tesis/**"],
        budget_s=10.0,
    ),
    BuildStep(
        label="Validar arquitectura B0 desktop-first",
        script="07_scripts/audit/validate_b0_architecture.py",
        group="estructura",
        tags=["validate", "structure"],
        watch=["00_sistema_tesis/decisiones/**", "runtime/**"],
        budget_s=10.0,
    ),
    BuildStep(
        label="Auditar Estándares Externos",
        script="07_scripts/audit/verify_standards.py",
        group="estructura",
        tags=["validate", "standards"],
        watch=["00_sistema_tesis/**"],
    ),
    BuildStep(
        label="Validar specs SDD",
        script="07_scripts/audit/validate_sdd_specs.py",
        group="estructura",
        tags=["validate", "sdd", "agents"],
        watch=["00_sistema_tesis/pendientes/**"],
        budget_s=5.0,
    ),

    # ── Grupo: evidencia ──────────────────────────────────────────────────────
    BuildStep(
        label="Sincronizar evidencia técnica",
        script="07_scripts/ops/sync_evidence.py",
        group="evidencia",
        tags=["evidence", "sync"],
        watch=["runtime/**", "07_scripts/**"],
    ),
    BuildStep(
        label="Verificar artefactos de benchmark científico",
        script="07_scripts/audit/verify_benchmark_artifacts.py",
        group="evidencia",
        tags=["evidence", "benchmark"],
        watch=["runtime/edge_iot/benchmarks/**", "runtime/pc_control/benchmarks/**"],
    ),
    BuildStep(
        label="Verificar evidencia fuente de conversación",
        script="07_scripts/tesis.py",
        args=["source", "status", "--check"],
        group="evidencia",
        tags=["evidence", "ledger"],
        watch=["00_sistema_tesis/canon/events.jsonl"],
    ),

    # ── Grupo: generacion ─────────────────────────────────────────────────────
    BuildStep(
        label="Generar portada README",
        script="07_scripts/ops/build_readme_portada.py",
        group="generacion",
        tags=["generate", "docs"],
        watch=["00_sistema_tesis/**", "01_planeacion/**"],
        budget_s=5.0,
    ),
    BuildStep(
        label="Generar memoria operativa",
        script="07_scripts/ops/build_memory.py",
        group="generacion",
        tags=["generate", "docs"],
        watch=["00_sistema_tesis/**"],
        budget_s=5.0,
    ),
    BuildStep(
        label="Validar memoria operativa",
        script="07_scripts/audit/validate_memory.py",
        group="generacion",
        tags=["validate", "docs"],
        watch=["00_sistema_tesis/bitacora/**"],
    ),
    BuildStep(
        label="Generar wiki verificable",
        script="07_scripts/ops/build_wiki.py",
        group="generacion",
        tags=["generate", "docs"],
        watch=["00_sistema_tesis/**", "01_planeacion/**"],
        budget_s=20.0,
    ),
    BuildStep(
        label="Generar snapshot de observabilidad distribuida",
        script="07_scripts/ops/build_observability_snapshot.py",
        group="generacion",
        tags=["generate", "docs", "observability", "openclaw"],
        watch=[
            "docker-compose.yml",
            "manifests/service_matrix.yaml",
            "manifests/operational_topology.yaml",
            "manifests/observability_policy.yaml",
            "00_sistema_tesis/config/openclaw_status.json",
            "runtime/pc_control/benchmarks/index.json",
            "runtime/edge_iot/benchmarks/index.json",
            "06_dashboard/publico/manifest_publico.json",
        ],
        budget_s=5.0,
    ),
    BuildStep(
        label="Generar dashboard",
        script="07_scripts/ops/build_dashboard.py",
        group="generacion",
        tags=["generate", "docs"],
        watch=["00_sistema_tesis/**", "runtime/**"],
        budget_s=20.0,
    ),
    BuildStep(
        label="Exportar hoja maestra",
        script="07_scripts/utils/export_master_sheet.py",
        group="generacion",
        tags=["generate"],
        watch=["00_sistema_tesis/canon/**"],
    ),
    BuildStep(
        label="Generar reporte de consistencia",
        script="07_scripts/utils/report_consistency.py",
        group="generacion",
        tags=["generate", "audit"],
        watch=["00_sistema_tesis/**"],
    ),

    # ── Grupo: openclaw ───────────────────────────────────────────────────────
    BuildStep(
        label="Mantenimiento DB Mission Control",
        script="07_scripts/ops/db_maintenance.py",
        args=["04_implementacion/control_mission/mission-control.db", "--repair"],
        group="openclaw",
        tags=["openclaw", "db", "maintenance"],
        watch=["04_implementacion/control_mission/mission-control.db"],
    ),
    BuildStep(
        label="Sincronizar estado de OpenClaw",
        script="07_scripts/ops/build_openclaw_status.py",
        group="openclaw",
        tags=["openclaw"],
        watch=[
            "runtime/openclaw/**",
            "00_sistema_tesis/config/openclaw_status.json",
        ],
    ),
    BuildStep(
        label="Sincronizar presupuesto y uso de tokens",
        script="07_scripts/ops/build_token_usage_snapshot.py",
        group="openclaw",
        tags=["openclaw", "tokens"],
        watch=["runtime/openclaw/**"],
    ),

    # ── Grupo: backups ────────────────────────────────────────────────────────
    BuildStep(
        label="Auditar rotación de backups (dry-run)",
        script="07_scripts/ops/rotate_backups.py",
        group="backups",
        tags=["backup"],
        watch=["00_sistema_tesis/**"],
    ),

    # ── Grupo: ux ─────────────────────────────────────────────────────────────
    BuildStep(
        label="Validar estándares UI/UX",
        script="07_scripts/audit/verify_ui_ux_standards.py",
        group="ux",
        tags=["validate", "ux"],
        watch=["06_dashboard/**"],
    ),

    # ── Grupo: publicacion ────────────────────────────────────────────────────
    BuildStep(
        label="Sincronizar publicación pública sanitizada",
        script="07_scripts/tesis.py",
        args=["publish", "--build"],
        group="publicacion",
        tags=["publish"],
        watch=["00_sistema_tesis/**", "01_planeacion/**"],
        budget_s=30.0,
    ),
    BuildStep(
        label="Validar enlaces derivados y públicos",
        script="07_scripts/audit/validate_links.py",
        group="publicacion",
        tags=["validate", "publish"],
        watch=["06_dashboard/**"],
    ),
    BuildStep(
        label="Validar calidad editorial pública",
        script="07_scripts/audit/validate_public_text.py",
        group="publicacion",
        tags=["validate", "publish"],
        watch=["06_dashboard/**"],
    ),
    BuildStep(
        label="Validar publicación pública sanitizada",
        script="07_scripts/tesis.py",
        args=["publish", "--check"],
        group="publicacion",
        tags=["validate", "publish"],
        watch=["06_dashboard/**"],
    ),

    # ── Grupo: toltecayotl ────────────────────────────────────────────────────
    BuildStep(
        label="Verificar Estado del Motor Epistémico",
        script="07_scripts/tesis.py",
        args=["toltecayotl", "status"],
        group="toltecayotl",
        tags=["toltecayotl", "infra"],
        watch=[
            "07_scripts/toltecayotl/**",
            "runtime/toltecayotl/**",
            "00_sistema_tesis/config/toltecayotl_status.json",
        ],
    ),

    # ── Grupo: infra ──────────────────────────────────────────────────────────
    BuildStep(
        label="Verificar salud de contenedores Docker",
        script="07_scripts/audit/verify_docker_health.py",
        group="infra",
        tags=["infra"],
        soft_fail=True,
    ),
    BuildStep(
        label="Auditoría remota de Nodo Edge",
        script="07_scripts/audit/audit_remote_edge.py",
        group="infra",
        tags=["infra", "edge"],
        soft_fail=True,
    ),
    BuildStep(
        label="Verificar operabilidad humana",
        script="07_scripts/tesis.py",
        args=["doctor", "--check"],
        group="infra",
        tags=["infra", "audit"],
    ),
]

# ── Índices auxiliares ─────────────────────────────────────────────────────────

GROUPS: dict[str, list[BuildStep]] = {}
for _step in STEPS:
    GROUPS.setdefault(_step.group, []).append(_step)

ALL_TAGS: set[str] = {tag for step in STEPS for tag in step.tags}
ALL_GROUPS: set[str] = set(GROUPS.keys())
LABELS: dict[str, BuildStep] = {step.label: step for step in STEPS}
