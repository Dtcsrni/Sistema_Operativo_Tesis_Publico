"""build_runner/runner.py -- Motor de ejecucion de pasos del build.

Responsabilidades:
  - Ejecutar un BuildStep en subproceso con medicion de tiempo
  - Respetar soft_fail, budget_s y skip_if
  - Integrar con BuildCache para ejecucion incremental
  - Generar StepReport inmutable por cada paso
  - Escribir perfiles JSON (timestamped + latest)
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from build_runner.cache import BuildCache
    from build_runner.registry import BuildStep

# -- Colores ANSI (solo si el terminal lo soporta) ----------------------------
_USE_COLOR = sys.stdout.isatty()

def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _USE_COLOR else text

def GREEN(t: str)  -> str: return _c("32", t)
def YELLOW(t: str) -> str: return _c("33", t)
def RED(t: str)    -> str: return _c("31", t)
def CYAN(t: str)   -> str: return _c("36", t)
def BOLD(t: str)   -> str: return _c("1",  t)
def DIM(t: str)    -> str: return _c("2",  t)


# -- Resultado de un paso -----------------------------------------------------

@dataclass(frozen=True)
class StepReport:
    label: str
    script: str
    args: list[str]
    group: str
    started_at_utc: str
    duration_seconds: float
    budget_seconds: float | None
    status: str           # "ok" | "slow" | "failed" | "skipped" | "soft_fail"
    returncode: int | None
    cache_hit: bool
    skip_reason: str | None = None

    def is_ok(self) -> bool:
        return self.status in ("ok", "slow", "soft_fail", "skipped")

    def to_dict(self) -> dict:
        return asdict(self)


# -- Motor de ejecucion -------------------------------------------------------

def run_step(
    step: "BuildStep",
    root: Path,
    python_exe: str,
    cache: "BuildCache | None" = None,
    force: bool = False,
    dry_run: bool = False,
) -> StepReport:
    """Ejecuta un BuildStep y retorna su StepReport.

    Args:
        step:       El paso a ejecutar.
        root:       Raiz del repositorio.
        python_exe: Ejecutable Python a usar.
        cache:      Cache de fingerprints (None = sin cache incremental).
        force:      Si True, ignora el cache aunque haya hit.
        dry_run:    Si True, imprime el comando pero no lo ejecuta.
    """
    started_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")

    # -- Verificar skip_if ----------------------------------------------------
    if step.skip_if is not None and step.skip_if():
        print(DIM(f"  [SKIP] {step.label} (skip_if cumplido)"))
        return StepReport(
            label=step.label, script=step.script, args=step.args,
            group=step.group, started_at_utc=started_at,
            duration_seconds=0.0, budget_seconds=step.budget_s,
            status="skipped", returncode=None, cache_hit=False,
            skip_reason="skip_if",
        )

    # -- Verificar cache incremental ------------------------------------------
    if not force and cache is not None and cache.is_hit(step):
        print(DIM(f"  [CACHE] {step.label} (sin cambios, omitido)"))
        return StepReport(
            label=step.label, script=step.script, args=step.args,
            group=step.group, started_at_utc=started_at,
            duration_seconds=0.0, budget_seconds=step.budget_s,
            status="skipped", returncode=None, cache_hit=True,
            skip_reason="cache_hit",
        )

    # -- Construir comando -----------------------------------------------------
    cmd = [python_exe, str(root / step.script), *step.args]
    print(CYAN(f"\n[RUN] {step.label}") + DIM(f"  ->  {step.script}"))

    if dry_run:
        print(DIM(f"       (dry-run) {' '.join(cmd)}"))
        return StepReport(
            label=step.label, script=step.script, args=step.args,
            group=step.group, started_at_utc=started_at,
            duration_seconds=0.0, budget_seconds=step.budget_s,
            status="skipped", returncode=None, cache_hit=False,
            skip_reason="dry_run",
        )

    # -- Ejecutar -------------------------------------------------------------
    t0 = time.perf_counter()
    try:
        result = subprocess.run(cmd, cwd=root, check=not step.soft_fail)
        returncode = result.returncode
        raw_ok = returncode == 0
    except subprocess.CalledProcessError as exc:
        returncode = exc.returncode
        raw_ok = False

    duration = round(time.perf_counter() - t0, 3)

    # -- Determinar status ----------------------------------------------------
    if not raw_ok:
        if step.soft_fail:
            status = "soft_fail"
            print(YELLOW(f"  [WARN] {step.label} finalizo con codigo {returncode} (soft_fail, continuando)"))
        else:
            status = "failed"
            print(RED(f"  [FAIL] {step.label} -- codigo {returncode} -- {duration:.3f}s"))
    elif step.budget_s is not None and duration > step.budget_s:
        status = "slow"
        print(YELLOW(f"  [SLOW] {step.label} -- {duration:.3f}s > presupuesto {step.budget_s:.1f}s"))
    else:
        status = "ok"
        print(GREEN(f"  [OK]   {step.label} -- {duration:.3f}s"))

    # -- Actualizar cache -----------------------------------------------------
    if cache is not None:
        cache.record(step, status if raw_ok else "failed")

    return StepReport(
        label=step.label, script=step.script, args=step.args,
        group=step.group, started_at_utc=started_at,
        duration_seconds=duration, budget_seconds=step.budget_s,
        status=status, returncode=returncode, cache_hit=False,
    )


# -- Generacion de perfiles ---------------------------------------------------

def write_profile(reports: list[StepReport], profile_dir: Path) -> Path:
    """Escribe el perfil JSON de la sesion de build (timestamped + latest)."""
    profile_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    path = profile_dir / f"build_all_profile_{ts}.json"
    latest = profile_dir / "build_all_profile_latest.json"

    executed = [r for r in reports if r.status != "skipped"]
    skipped  = [r for r in reports if r.status == "skipped"]
    failed   = [r for r in reports if r.status == "failed"]
    slow     = [r for r in reports if r.status == "slow"]

    payload = {
        "generated_at_utc": ts,
        "total_duration_seconds": round(sum(r.duration_seconds for r in reports), 3),
        "summary": {
            "total":    len(reports),
            "executed": len(executed),
            "skipped":  len(skipped),
            "failed":   len(failed),
            "slow":     len(slow),
        },
        "slow_stages":   [r.label for r in slow],
        "failed_stages": [r.label for r in failed],
        "steps": [r.to_dict() for r in reports],
    }

    body = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(body, encoding="utf-8")
    latest.write_text(body, encoding="utf-8")
    return path


# -- Resumen de consola -------------------------------------------------------

def print_summary(reports: list[StepReport], profile_path: Path, root: Path) -> None:
    executed = [r for r in reports if r.status != "skipped"]
    skipped  = [r for r in reports if r.status == "skipped"]
    failed   = [r for r in reports if r.status == "failed"]
    slow     = [r for r in reports if r.status == "slow"]
    total_t  = sum(r.duration_seconds for r in reports)

    sep = "=" * 60
    print()
    print(BOLD(sep))
    print(BOLD(f"  Build completado -- {total_t:.2f}s"))
    print(f"  Ejecutados : {GREEN(str(len(executed)))}   "
          f"Omitidos : {DIM(str(len(skipped)))}   "
          f"Lentos : {YELLOW(str(len(slow)))}   "
          f"Fallidos : {RED(str(len(failed)))}")

    if slow:
        print(YELLOW("\n  Etapas lentas:"))
        for r in slow:
            print(YELLOW(f"    * {r.label} ({r.duration_seconds:.2f}s > {r.budget_seconds:.1f}s presupuesto)"))

    if failed:
        print(RED("\n  Etapas fallidas:"))
        for r in failed:
            print(RED(f"    * {r.label} (codigo {r.returncode})"))

    try:
        rel = profile_path.relative_to(root)
    except ValueError:
        rel = profile_path
    print(DIM(f"\n  Perfil: {rel}"))
    print(BOLD(sep))
