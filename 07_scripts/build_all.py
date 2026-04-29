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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))   # 07_scripts/

from build_runner.registry import STEPS, GROUPS, ALL_TAGS, ALL_GROUPS, LABELS
from build_runner.cache import BuildCache
from build_runner.runner import run_step, write_profile, print_summary, StepReport
from common import preferred_python_executable

PROFILE_DIR = ROOT / "00_sistema_tesis" / "bitacora" / "audit_history"


# ── CLI ────────────────────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="build_all.py",
        description="Build modular e incremental del proyecto SIOT.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
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
    from build_runner.registry import BuildStep

    # Sin filtros → todos
    if not args.group and not args.tag and not args.only:
        return list(STEPS)

    selected: list[BuildStep] = []
    seen: set[str] = set()

    def _add(step: BuildStep) -> None:
        if step.label not in seen:
            selected.append(step)
            seen.add(step.label)

    # --only por nombre exacto
    for label in args.only:
        if label in LABELS:
            _add(LABELS[label])
        else:
            print(f"[WARN] Paso desconocido: '{label}'")
            print(f"       Pasos disponibles: {', '.join(LABELS.keys())}")

    # --group
    for group in args.group:
        if group in GROUPS:
            for step in GROUPS[group]:
                _add(step)
        else:
            print(f"[WARN] Grupo desconocido: '{group}'. Grupos: {', '.join(sorted(ALL_GROUPS))}")

    # --tag (AND lógico si se pasa múltiples veces, OR si se quiere flexibilidad)
    # Implementamos OR: paso incluido si tiene CUALQUIERA de los tags pedidos
    if args.tag:
        tag_set = set(args.tag)
        for step in STEPS:
            if tag_set & set(step.tags):
                _add(step)

    # Reordenar según el orden canónico de STEPS
    order = {step.label: i for i, step in enumerate(STEPS)}
    selected.sort(key=lambda s: order.get(s.label, 9999))
    return selected


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    python_exe = preferred_python_executable()

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
    steps = _select_steps(args)
    if not steps:
        print("[WARN] No se seleccionó ningún paso. Usa --list para ver los disponibles.")
        return 1

    mode_label = "COMPLETO" if not (args.group or args.tag or args.only) else "PARCIAL"
    force_label = " [FORCE]" if args.force else ""
    dry_label   = " [DRY-RUN]" if args.dry_run else ""
    cache_label = " [sin caché]" if args.no_cache else ""
    print(f"\n[BUILD {mode_label}{force_label}{dry_label}{cache_label}] "
          f"{len(steps)} paso(s) seleccionado(s)\n")

    # ── Ejecución ─────────────────────────────────────────────────────────────
    reports: list[StepReport] = []
    hard_failed = False

    for step in steps:
        report = run_step(
            step=step,
            root=ROOT,
            python_exe=python_exe,
            cache=cache,
            force=args.force,
            dry_run=args.dry_run,
        )
        reports.append(report)

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
        profile_path = write_profile(reports, PROFILE_DIR)
        print_summary(reports, profile_path, ROOT)
    else:
        print(f"\n[DRY-RUN] {len(steps)} paso(s) se ejecutarían.")

    return 1 if hard_failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
