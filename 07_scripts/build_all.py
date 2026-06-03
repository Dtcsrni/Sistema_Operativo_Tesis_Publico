"""build_all.py — Entry point del sistema de build modular e incremental.

Uso básico:
  python 07_scripts/build_all.py                   # build completo (incremental)
  python 07_scripts/build_all.py --force           # ignora caché, ejecuta todo
  python 07_scripts/build_all.py --group canon     # solo pasos del grupo 'canon'
  python 07_scripts/build_all.py --tag audit       # solo pasos con tag 'audit'
  python 07_scripts/build_all.py --only "Auditar Ledger IA"  # paso exacto por nombre
  python 07_scripts/build_all.py --dry-run         # muestra qué se ejecutaría
  python 07_scripts/build_all.py --list            # lista todos los pasos
  python 07_scripts/build_all.py --clear-cache     # limpia caché incremental

Combinaciones útiles:
  python 07_scripts/build_all.py --group openclaw --force
  python 07_scripts/build_all.py --tag security --tag audit
  python 07_scripts/build_all.py --group canon --group integridad
"""
from __future__ import annotations

import argparse
import sys
import time
from dataclasses import replace
from fnmatch import fnmatch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))   # 07_scripts/

from build_runner.registry import STEPS, GROUPS, ALL_TAGS, ALL_GROUPS, LABELS
from build_runner.cache import BuildCache
from build_runner.runner import run_step, write_profile, print_summary, StepReport
from common import preferred_python_executable

PROFILE_DIR = ROOT / "00_sistema_tesis" / "bitacora" / "audit_history"

SMOKE_LABELS = (
    "Materializar proyecciones del canon",
    "Auditar canon unificado",
    "Validar estructura",
    "Validar specs SDD",
    "Evaluar Harness Readiness SIOT",
    "Ejecutar suite de pruebas (pytest)",
)

DEV_LABELS = (
    "Validar estructura",
    "Validar specs SDD",
    "Evaluar Harness Readiness SIOT",
    "Ejecutar suite de pruebas (pytest)",
)

TEST_STEP_LABEL = "Ejecutar suite de pruebas (pytest)"


# ── CLI ────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_all.py",
        description="Build modular e incremental del proyecto SIOT.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--profile", choices=["dev", "changed", "smoke", "full", "release"], default="full",
        help="Perfil de ejecución: dev/changed/smoke para ciclos ágiles; full/release para gates completos.",
    )
    p.add_argument(
        "--max-step-seconds", type=float, default=None,
        help="Timeout máximo por paso. Si se omite, no impone límite duro por paso.",
    )
    p.add_argument(
        "--global-timeout", type=float, default=None,
        help="Timeout máximo total del build en segundos.",
    )
    p.add_argument(
        "--explain", action="store_true",
        help="Mostrar por qué fue seleccionado cada paso.",
    )
    p.add_argument(
        "--group", "-g", action="append", metavar="GRUPO", default=[],
        help=f"Ejecutar solo pasos del grupo. Grupos disponibles: {', '.join(sorted(ALL_GROUPS))}",
    )
    p.add_argument(
        "--tag", "-t", action="append", metavar="TAG", default=[],
        help=f"Ejecutar solo pasos con el tag. Tags disponibles: {', '.join(sorted(ALL_TAGS))}",
    )
    p.add_argument(
        "--only", "-o", action="append", metavar="LABEL", default=[],
        help="Ejecutar solo el paso con ese nombre exacto (puede repetirse).",
    )
    p.add_argument(
        "--force", "-f", action="store_true",
        help="Ignorar caché incremental y ejecutar todos los pasos seleccionados.",
    )
    p.add_argument(
        "--dry-run", "-n", action="store_true",
        help="Mostrar qué se ejecutaría sin ejecutar nada.",
    )
    p.add_argument(
        "--no-cache", action="store_true",
        help="Desactivar caché incremental para esta ejecución (sin borrarla).",
    )
    p.add_argument(
        "--clear-cache", action="store_true",
        help="Borrar toda la caché incremental antes de ejecutar.",
    )
    p.add_argument(
        "--list", "-l", action="store_true",
        help="Listar todos los pasos disponibles con su grupo y tags.",
    )
    p.add_argument(
        "--fail-fast", action="store_true",
        help="Detener el build en el primer fallo (salvo soft_fail).",
    )
    p.add_argument(
        "--no-serena-gate", action="store_true",
        help="Omitir la comprobación previa 'serena gate' (solo use si sabe lo que hace).",
    )
    return p


# ── Listado ───────────────────────────────────────────────────────────────────

def _list_steps(cache: BuildCache | None) -> None:
    """Imprime tabla de pasos con estado de caché."""
    current_group = None
    for step in STEPS:
        if step.group != current_group:
            current_group = step.group
            print(f"\n  [{step.group.upper()}]")
        tags_str = ", ".join(step.tags) if step.tags else "—"
        cached = ""
        if cache is not None:
            cached = "  [cache OK]" if cache.is_hit(step) else ""
        soft = "  [soft]" if step.soft_fail else ""
        print(f"    · {step.label}{soft}{cached}")
        print(f"      tags: {tags_str}")
    print()


# ── Selección de pasos ────────────────────────────────────────────────────────

def _select_steps(args: argparse.Namespace):
    """Retorna la lista ordenada de pasos a ejecutar según los filtros CLI."""
    return [item[0] for item in _select_steps_with_reasons(args)]


def _select_steps_with_reasons(args: argparse.Namespace):
    """Retorna pares (BuildStep, razón) según perfil y filtros CLI."""
    from build_runner.registry import BuildStep

    selected: list[tuple[BuildStep, str]] = []
    seen: set[str] = set()

    def _add(step: BuildStep, reason: str) -> None:
        if step.label not in seen:
            selected.append((_adapt_step_for_profile(step, args.profile), reason))
            seen.add(step.label)

    # Los filtros explícitos conservan precedencia sobre perfiles ágiles.
    if not args.group and not args.tag and not args.only:
        if args.profile == "dev":
            for label in DEV_LABELS:
                _add(LABELS[label], "profile:dev")
            return selected
        if args.profile == "smoke":
            for label in SMOKE_LABELS:
                _add(LABELS[label], "profile:smoke")
            return selected
        if args.profile == "changed":
            for step, reason in _changed_profile_steps():
                _add(step, reason)
            return selected
        # full/release sin filtros → todos
        for step in STEPS:
            _add(step, f"profile:{args.profile}")
        return selected

    # --only por nombre exacto
    for label in args.only:
        if label in LABELS:
            _add(LABELS[label], f"only:{label}")
        else:
            print(f"[WARN] Paso desconocido: '{label}'")
            print(f"       Pasos disponibles: {', '.join(LABELS.keys())}")

    # --group
    for group in args.group:
        if group in GROUPS:
            for step in GROUPS[group]:
                _add(step, f"group:{group}")
        else:
            print(f"[WARN] Grupo desconocido: '{group}'. Grupos: {', '.join(sorted(ALL_GROUPS))}")

    # --tag (AND lógico si se pasa múltiples veces, OR si se quiere flexibilidad)
    # Implementamos OR: paso incluido si tiene CUALQUIERA de los tags pedidos
    if args.tag:
        tag_set = set(args.tag)
        for step in STEPS:
            if tag_set & set(step.tags):
                _add(step, f"tag:{','.join(sorted(tag_set & set(step.tags)))}")

    # Reordenar según el orden canónico de STEPS
    order = {step.label: i for i, step in enumerate(STEPS)}
    selected.sort(key=lambda item: order.get(item[0].label, 9999))
    return selected


def _adapt_step_for_profile(step, profile: str):
    """Ajusta comandos de pasos compartidos sin mutar el registro global."""
    if step.label != TEST_STEP_LABEL:
        return step
    if profile in {"dev", "smoke", "changed"}:
        return replace(step, args=["--profile", profile, "--fast"])
    if profile in {"full", "release"}:
        return replace(step, args=["--profile", "full"])
    return step


def _changed_profile_steps():
    from build_runner.registry import BuildStep
    from ops import test_impact_gate

    changed_paths = test_impact_gate.discover_changed_paths()
    selected: list[tuple[BuildStep, str]] = []
    seen: set[str] = set()

    def _add(step: BuildStep, reason: str) -> None:
        if step.label not in seen:
            selected.append((step, reason))
            seen.add(step.label)

    for path in changed_paths:
        for step in STEPS:
            if _path_matches_any_watch(path, step.watch):
                _add(step, f"watch:{path}")

    impact_report = test_impact_gate.build_report(paths=changed_paths)
    impact_ids = {item["id"] for item in impact_report.get("selected_commands", [])}
    if impact_ids:
        _add(LABELS[TEST_STEP_LABEL], "test-impact:" + ",".join(sorted(impact_ids)))

    if not selected:
        for label in SMOKE_LABELS:
            _add(LABELS[label], "fallback:smoke")

    order = {step.label: i for i, step in enumerate(STEPS)}
    selected.sort(key=lambda item: order.get(item[0].label, 9999))
    return selected


def _path_matches_any_watch(path: str, patterns: list[str]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in patterns:
        pat = pattern.replace("\\", "/")
        if pat.endswith("/**") and normalized.startswith(pat[:-3] + "/"):
            return True
        if fnmatch(normalized, pat):
            return True
    return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.profile == "release":
        args.force = True
        args.fail_fast = True

    python_exe = preferred_python_executable()

    # ── Preflight Serena gate (fail-closed) ─────────────────────────────────
    if not args.dry_run and not getattr(args, "no_serena_gate", False):
        import subprocess
        gate_script = Path(__file__).parent / "ops" / "serena_gate.py"
        try:
            p = subprocess.run([python_exe, str(gate_script)], capture_output=True, text=True, timeout=60)
        except Exception as e:
            print(f"[ERROR] fallo al ejecutar la puerta Serena: {e}")
            return 2

        if p.returncode != 0:
            print("[ERROR] Serena gate failed — abortando build.")
            if p.stdout:
                print(p.stdout)
            if p.stderr:
                print(p.stderr, file=sys.stderr)
            return 2

    # ── Caché ─────────────────────────────────────────────────────────────────
    use_cache = not args.no_cache and not args.dry_run
    cache = BuildCache(ROOT, PROFILE_DIR) if use_cache else None

    if args.clear_cache and cache is not None:
        cache.clear()
        print("[INFO] Caché incremental limpiada.")

    # ── Listado ───────────────────────────────────────────────────────────────
    if args.list:
        print("\nPasos del build (ordenados por ejecución):\n")
        _list_steps(cache)
        return 0

    # ── Selección de pasos ────────────────────────────────────────────────────
    selected_steps = _select_steps_with_reasons(args)
    if not selected_steps:
        print("[WARN] No se seleccionó ningún paso. Usa --list para ver los disponibles.")
        return 1

    mode_label = "COMPLETO" if args.profile in {"full", "release"} and not (args.group or args.tag or args.only) else "PARCIAL"
    force_label = " [FORCE]" if args.force else ""
    dry_label   = " [DRY-RUN]" if args.dry_run else ""
    cache_label = " [sin caché]" if args.no_cache else ""
    print(f"\n[BUILD {mode_label} profile={args.profile}{force_label}{dry_label}{cache_label}] "
          f"{len(selected_steps)} paso(s) seleccionado(s)\n")

    if args.explain:
        for step, reason in selected_steps:
            print(f"  - {step.label}: {reason}")
        print()

    # ── Ejecución ─────────────────────────────────────────────────────────────
    reports: list[StepReport] = []
    hard_failed = False
    started = time.perf_counter()

    for step, reason in selected_steps:
        if args.global_timeout is not None and (time.perf_counter() - started) >= args.global_timeout:
            print(f"\n[ABORT] global-timeout alcanzado ({args.global_timeout:.1f}s)")
            hard_failed = True
            break

        report = run_step(
            step=step,
            root=ROOT,
            python_exe=python_exe,
            cache=cache,
            force=args.force,
            dry_run=args.dry_run,
            profile=args.profile,
            selected_reason=reason,
            timeout_seconds=args.max_step_seconds,
        )
        reports.append(report)
        if not args.dry_run:
            write_profile(reports, PROFILE_DIR, profile=args.profile, partial=True)

        if report.status == "failed":
            hard_failed = True
            if args.fail_fast:
                print(f"\n[ABORT] fail-fast activado tras fallo en: {step.label}")
                break

    # ── Persistir caché ───────────────────────────────────────────────────────
    if cache is not None:
        cache.save()

    # ── Perfil y resumen ──────────────────────────────────────────────────────
    if not args.dry_run:
        profile_path = write_profile(reports, PROFILE_DIR, profile=args.profile, partial=False)
        print_summary(reports, profile_path, ROOT)
    else:
        print(f"\n[DRY-RUN] {len(selected_steps)} paso(s) se ejecutarían.")

    return 1 if hard_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
