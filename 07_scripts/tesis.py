from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
import sys
import tempfile

from canon import (
    EVENTS_PATH,
    append_conversation_source,
    append_agent_activity,
    append_artifact_signed,
    append_event,
    append_human_validation,
    append_session_record,
    create_session_content,
    import_legacy_events,
    load_events,
    materialize_events,
    normalize_path,
    projection_paths,
    create_conversation_source_scaffold,
    sanitize_session_id_for_path,
    source_evidence_policy,
    source_evidence_status,
    validate_events,
    verify_conversation_source_for_step,
)
from common import ROOT, file_sha256, load_csv_rows, load_yaml_json
from governance_gate import extract_step_ids_from_diff
from publication import publication_bundle_status


SECOND_LEVEL_DERIVED_PREFIXES = (
    "06_dashboard/wiki/",
    "06_dashboard/generado/wiki/",
    "06_dashboard/generado/",
    "06_dashboard/publico/",
)
SECOND_LEVEL_DERIVED_PATHS = {
    "06_dashboard/generado/wiki_manifest.json",
    "00_sistema_tesis/config/security_report.json",
    "00_sistema_tesis/config/token_usage_snapshot.json",
    "README.md",
}
HUMAN_OPERATION_MARKERS = {
    "README_INICIO.md": ["Superficie privada", "Superficie pública", "IA opcional"],
    "00_sistema_tesis/manual_operacion_humana.md": ["Retomar", "Registrar cambio", "Auditar", "Publicación pública"],
    "06_dashboard/wiki/index.md": ["Operación humana", "público/privado"],
    "06_dashboard/wiki/sistema.md": ["Operación humana y superficies", "IA opcional"],
    "06_dashboard/wiki/gobernanza.md": ["flujo crítico", "IA es opcional"],
}


def source_evidence_local_enabled() -> bool:
    return os.environ.get("CI", "").strip().lower() not in {"1", "true", "yes"}


def priority_rank(value: str) -> int:
    order = {"critica": 0, "alta": 1, "media": 2, "baja": 3}
    return order.get(value, 99)


def latest_step_id(events: list[dict]) -> str:
    return next((event["event_id"] for event in reversed(events) if str(event["event_id"]).startswith("VAL-STEP-")), "n/a")


def current_signoff_status() -> tuple[int, int]:
    signoffs = load_yaml_json("00_sistema_tesis/config/sign_offs.json").get("sign_offs", [])
    total = len(signoffs)
    stale = 0
    for record in signoffs:
        rel_path = str(record.get("archivo", "")).strip()
        expected_hash = str(record.get("hash_verificado", "")).strip()
        target = ROOT / rel_path
        if not rel_path or not expected_hash or not target.exists() or not target.is_file():
            stale += 1
            continue
        if file_sha256(rel_path) != expected_hash:
            stale += 1
    return total, stale


def human_operability_errors() -> list[str]:
    errors: list[str] = []
    for rel_path, markers in HUMAN_OPERATION_MARKERS.items():
        target = ROOT / rel_path
        if not target.exists():
            errors.append(f"Falta el artefacto humano requerido: {rel_path}")
            continue
        content = target.read_text(encoding="utf-8")
        for marker in markers:
            if marker not in content:
                errors.append(f"El artefacto {rel_path} no expone el marcador requerido: {marker}")
    return errors


def next_items() -> tuple[dict, list[dict], list[dict], dict | None]:
    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    backlog = load_csv_rows("01_planeacion/backlog.csv")
    riesgos = load_csv_rows("01_planeacion/riesgos.csv")
    entregables = load_csv_rows("01_planeacion/entregables.csv")
    tasks = [item for item in backlog if item["estado"] in {"pendiente", "en_progreso"}]
    tasks.sort(key=lambda item: (priority_rank(item["prioridad"]), item["fecha_objetivo"], item["task_id"]))
    risks = [item for item in riesgos if item["estado"] == "abierto"]
    risks.sort(key=lambda item: (priority_rank(item["impacto"]), priority_rank(item["probabilidad"]), item["risk_id"]))
    deliverable = next((item for item in entregables if item["deliverable_id"] == sistema["siguiente_entregable"]), None)
    return sistema, tasks, risks, deliverable


def safe_next_action(
    *,
    drift: list[str],
    publication_drift: list[str],
    publication_errors: list[str],
    human_errors: list[str],
    source_repo_failures: list[dict] | None = None,
    source_local_failures: list[dict] | None = None,
) -> str:
    source_repo_failures = source_repo_failures or []
    source_local_failures = source_local_failures or []
    if drift:
        return "python 07_scripts/tesis.py materialize"
    if source_repo_failures:
        return "python 07_scripts/tesis.py source status --check"
    if source_local_failures:
        first = source_local_failures[0]["step_id"]
        return f"python 07_scripts/tesis.py source verify --step-id {first}"
    if publication_drift or publication_errors:
        return "python 07_scripts/tesis.py publish --build"
    if human_errors:
        return "python 07_scripts/build_all.py"
    return "python 07_scripts/build_all.py"


def ensure_canon_initialized() -> list[dict]:
    if EVENTS_PATH.exists():
        return load_events()
    return import_legacy_events()


def run_python_script(script: str, *args: str) -> None:
    subprocess.run([sys.executable, script, *args], cwd=ROOT, check=True)


def run_command(cmd: list[str], *, check: bool = True, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=ROOT, check=check, text=True, capture_output=True, env=env)


def current_branch() -> str:
    result = run_command(["git", "branch", "--show-current"])
    return result.stdout.strip()


def parse_porcelain_paths(status_output: str) -> list[str]:
    paths: list[str] = []
    for raw_line in status_output.splitlines():
        line = raw_line.rstrip()
        if not line or len(line) < 4:
            continue
        payload = line[3:]
        if " -> " in payload:
            payload = payload.split(" -> ", maxsplit=1)[1]
        normalized = payload.replace("\\", "/").strip()
        if normalized:
            paths.append(normalized)
    seen: set[str] = set()
    ordered: list[str] = []
    for item in paths:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def unique_paths(paths: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in paths:
        normalized = raw.replace("\\", "/").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def step_sequence_value(step_id: str) -> tuple[int, str]:
    prefix = "VAL-STEP-"
    if step_id.startswith(prefix):
        suffix = step_id[len(prefix):]
        if suffix.isdigit():
            return int(suffix), step_id
    return -1, step_id


def latest_step_id_value(step_ids: list[str]) -> str:
    if not step_ids:
        return ""
    ordered = sorted(set(step_ids), key=step_sequence_value)
    return ordered[-1]


def patch_for_path(rel_path: str, *, cached: bool) -> str:
    cmd = ["git", "diff"]
    if cached:
        cmd.append("--cached")
    cmd.extend(["--binary", "--no-color", "--", rel_path])
    result = subprocess.run(
        cmd,
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.decode("utf-8", errors="replace")


def detected_step_ids_for_patch(rel_path: str, patch_text: str) -> list[str]:
    if not patch_text.strip():
        return []
    return extract_step_ids_from_diff(patch_text, [rel_path])


def classify_patches_by_step(
    patches_by_path: dict[str, str],
    primary_projection_paths: list[str],
    existing_step_ids: set[str],
) -> tuple[list[dict[str, object]], list[str], list[str]]:
    operational_paths, derived_paths = classify_sync_paths(list(patches_by_path), primary_projection_paths)
    global_step_ids = sorted(
        {
            step_id
            for rel_path in operational_paths
            for step_id in detected_step_ids_for_patch(rel_path, patches_by_path.get(rel_path, ""))
            if step_id in existing_step_ids
        },
        key=step_sequence_value,
    )
    fallback_step_id = latest_step_id_value(global_step_ids)
    bundles: dict[str, dict[str, object]] = {}
    unassigned: list[str] = []

    for rel_path in operational_paths:
        patch_text = patches_by_path.get(rel_path, "")
        detected = [step_id for step_id in detected_step_ids_for_patch(rel_path, patch_text) if step_id in existing_step_ids]
        selected_step_id = latest_step_id_value(detected) or fallback_step_id
        if not selected_step_id:
            unassigned.append(rel_path)
            continue
        bundle = bundles.setdefault(selected_step_id, {"step_id": selected_step_id, "paths": [], "auto_assigned_paths": []})
        bundle["paths"].append(rel_path)
        if not detected:
            bundle["auto_assigned_paths"].append(rel_path)

    ordered_bundles = sorted(bundles.values(), key=lambda item: step_sequence_value(str(item["step_id"])))
    return ordered_bundles, derived_paths, unassigned


def step_commit_message(step_id: str, events: list[dict]) -> str:
    event = next((item for item in events if item.get("event_id") == step_id), None)
    if not event:
        return f"chore: synchronize protected changes for {step_id}"
    matrix_row = dict(event.get("payload", {}).get("matrix_row", {}))
    summary = str(matrix_row.get("summary", "")).strip()
    if summary:
        return f"chore: {step_id.lower()} {summary}"
    return f"chore: synchronize protected changes for {step_id}"


def run_gate_pre_commit_step(*, step_id: str, agent: str = "") -> None:
    env = dict(os.environ)
    if step_id:
        env["SISTEMA_TESIS_STEP_ID"] = step_id
    if agent:
        env["SISTEMA_TESIS_AGENT"] = agent
    result = run_command(
        [sys.executable, "07_scripts/governance_gate.py", "--stage", "pre-commit"],
        check=False,
        env=env,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)


def apply_cached_patch_text(patch_text: str) -> None:
    if not patch_text.strip():
        return
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n", suffix=".patch", delete=False) as handle:
        handle.write(patch_text)
        patch_path = handle.name
    try:
        run_command(["git", "apply", "--cached", "--binary", "--whitespace=nowarn", patch_path])
    finally:
        try:
            os.unlink(patch_path)
        except OSError:
            pass


def worktree_changed_paths() -> list[str]:
    tracked = run_command(["git", "diff", "--name-only", "--diff-filter=ACMR"]).stdout.splitlines()
    untracked = run_command(["git", "ls-files", "--others", "--exclude-standard"]).stdout.splitlines()
    return unique_paths(tracked + untracked)


def commit_current_index(*, message: str, step_id: str, agent: str = "", sign: bool = True) -> bool:
    diff_name_only = run_command(["git", "diff", "--cached", "--name-only"], check=False).stdout.strip()
    if not diff_name_only:
        return False
    run_gate_pre_commit_step(step_id=step_id, agent=agent)
    env = dict(os.environ)
    if step_id:
        env["SISTEMA_TESIS_STEP_ID"] = step_id
    if agent:
        env["SISTEMA_TESIS_AGENT"] = agent
    cmd = ["git", "commit"]
    if sign:
        cmd.append("-S")
    cmd.extend(["-m", message])
    commit = run_command(cmd, check=False, env=env)
    if commit.returncode == 0:
        if commit.stdout.strip():
            print(commit.stdout.strip())
        return True
    combined = f"{commit.stdout}\n{commit.stderr}".strip()
    if "nothing to commit" in combined.lower():
        return False
    print(combined)
    raise subprocess.CalledProcessError(commit.returncode, commit.args, commit.stdout, commit.stderr)


def classify_sync_paths(paths: list[str], primary_projection_paths: list[str]) -> tuple[list[str], list[str]]:
    primary_set = set(primary_projection_paths)
    operational_bundle: list[str] = []
    secondary_derived: list[str] = []
    for path in paths:
        is_primary_projection = path in primary_set
        is_second_level_derived = path in SECOND_LEVEL_DERIVED_PATHS or any(
            path.startswith(prefix) for prefix in SECOND_LEVEL_DERIVED_PREFIXES
        )
        if is_second_level_derived and not is_primary_projection:
            secondary_derived.append(path)
        else:
            operational_bundle.append(path)
    return operational_bundle, secondary_derived


def stage_and_commit(paths: list[str], message: str, args: argparse.Namespace) -> bool:
    if not paths:
        return False
    run_command(["git", "add", "--", *paths])
    run_gate_pre_commit(args)
    commit = run_command(["git", "commit", "-S", "-m", message], check=False)
    if commit.returncode == 0:
        print(commit.stdout.strip())
        return True
    combined = f"{commit.stdout}\n{commit.stderr}".strip()
    if "nothing to commit" in combined.lower():
        return False
    print(combined)
    raise subprocess.CalledProcessError(commit.returncode, commit.args, commit.stdout, commit.stderr)


def build_gate_env(args: argparse.Namespace) -> dict[str, str]:
    env = dict(os.environ)
    if args.step_id:
        env["SISTEMA_TESIS_STEP_ID"] = args.step_id
    if args.agent:
        env["SISTEMA_TESIS_AGENT"] = args.agent
    return env


def run_gate_pre_commit(args: argparse.Namespace) -> None:
    env = build_gate_env(args)
    result = run_command(
        [sys.executable, "07_scripts/governance_gate.py", "--stage", "pre-commit"],
        check=False,
        env=env,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    if result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, result.args, result.stdout, result.stderr)


def cmd_sync(args: argparse.Namespace) -> int:
    events = ensure_canon_initialized()
    drift = materialize_events(events, check=False)
    if drift:
        print("SYNC: materialize actualizado")
        for rel_path in drift:
            print(f"- {rel_path}")
    status = run_command(["git", "status", "--porcelain"])
    changed_paths = parse_porcelain_paths(status.stdout)
    if not changed_paths:
        print("SYNC: sin cambios")
        return 0

    staged = run_command(["git", "diff", "--cached", "--name-only"]).stdout.strip()
    if staged:
        print("SYNC: abortado, hay cambios ya staged. Limpia el index antes de ejecutar `tesis sync`.")
        return 1

    operational_paths, derived_paths = classify_sync_paths(changed_paths, projection_paths(events))
    committed_any = False
    if operational_paths:
        committed_any = stage_and_commit(operational_paths, args.message, args) or committed_any

    if derived_paths:
        derived_message = args.derived_message or "chore: synchronize generated projections"
        committed_any = stage_and_commit(derived_paths, derived_message, args) or committed_any

    if not committed_any:
        print("SYNC: sin commits nuevos")
        return 0

    if args.push:
        branch = args.branch or current_branch()
        run_command(["git", "push", args.remote, branch])
        print(f"SYNC: push completado -> {args.remote}/{branch}")
    else:
        print("SYNC: commits creados (push omitido)")
    return 0


def cmd_split_staged(args: argparse.Namespace) -> int:
    events = ensure_canon_initialized()
    existing_step_ids = {str(event["event_id"]) for event in events if str(event["event_id"]).startswith("VAL-STEP-")}
    staged_output = run_command(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"]).stdout
    staged_paths = unique_paths(staged_output.splitlines())
    patch_mode = "staged"
    candidate_paths = staged_paths
    if not candidate_paths:
        candidate_paths = worktree_changed_paths()
        patch_mode = "worktree"
    if not candidate_paths:
        print("SPLIT-STAGED: sin cambios para separar")
        return 0

    if patch_mode == "worktree":
        untracked_paths = unique_paths(run_command(["git", "ls-files", "--others", "--exclude-standard"]).stdout.splitlines())
        if untracked_paths:
            run_command(["git", "add", "-N", "--", *untracked_paths])

    patches_by_path = {path: patch_for_path(path, cached=(patch_mode == "staged")) for path in candidate_paths}
    patches_by_path = {path: patch for path, patch in patches_by_path.items() if patch.strip()}
    if not patches_by_path:
        if patch_mode == "worktree":
            run_command(["git", "reset"], check=True)
        print("SPLIT-STAGED: no se pudieron leer parches")
        return 1

    bundles, derived_paths, unassigned = classify_patches_by_step(
        patches_by_path,
        projection_paths(events),
        existing_step_ids,
    )
    if unassigned:
        print("SPLIT-STAGED: hay archivos sin Step ID resoluble")
        for path in unassigned:
            print(f"- {path}")
        return 1

    print(f"SPLIT-STAGED: PLAN ({patch_mode})")
    for bundle in bundles:
        paths = bundle["paths"]
        auto_assigned = bundle["auto_assigned_paths"]
        print(f"- {bundle['step_id']}: {len(paths)} archivos")
        for path in paths:
            marker = " (auto)" if path in auto_assigned else ""
            print(f"  - {path}{marker}")
    if derived_paths:
        print(f"- DERIVED: {len(derived_paths)} archivos")
        for path in derived_paths:
            print(f"  - {path}")

    if not args.commit:
        if patch_mode == "worktree":
            run_command(["git", "reset"], check=True)
        print("SPLIT-STAGED: dry-run. Usa --commit para ejecutar.")
        return 0

    run_command(["git", "reset"], check=True)
    committed_any = False

    for bundle in bundles:
        patch_text = "".join(patches_by_path[path] for path in bundle["paths"])
        apply_cached_patch_text(patch_text)
        message = step_commit_message(str(bundle["step_id"]), events)
        committed_any = commit_current_index(
            message=message,
            step_id=str(bundle["step_id"]),
            agent=args.agent,
            sign=not args.no_sign,
        ) or committed_any

    if derived_paths:
        patch_text = "".join(patches_by_path[path] for path in derived_paths)
        apply_cached_patch_text(patch_text)
        derived_step_id = str(bundles[-1]["step_id"]) if bundles else args.step_id
        derived_message = args.derived_message or "chore: synchronize generated projections"
        committed_any = commit_current_index(
            message=derived_message,
            step_id=derived_step_id,
            agent=args.agent,
            sign=not args.no_sign,
        ) or committed_any

    if not committed_any:
        print("SPLIT-STAGED: sin commits nuevos")
        return 0

    print("SPLIT-STAGED: commits creados")
    return 0


def cmd_materialize(args: argparse.Namespace) -> int:
    ensure_canon_initialized()
    drift = materialize_events(check=args.check)
    if drift:
        if args.check:
            print("MATERIALIZE: DRIFT")
            for rel_path in drift:
                print(f"- {rel_path}")
            return 1
        print("MATERIALIZE: UPDATED")
        for rel_path in drift:
            print(f"- {rel_path}")
        return 0
    print("MATERIALIZE: OK")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    events = ensure_canon_initialized()
    errors = validate_events(events)
    drift = materialize_events(events, check=args.check)
    if errors or (args.check and drift):
        print("AUDIT: FAIL")
        for error in errors:
            print(f"- {error}")
        for rel_path in drift:
            print(f"- Proyección fuera de sincronía: {rel_path}")
        return 1
    print("AUDIT: OK")
    print(f"Eventos: {len(events)}")
    print(f"Proyecciones: {len(projection_paths(events))}")
    return 0


def cmd_status(_: argparse.Namespace) -> int:
    events = ensure_canon_initialized()
    latest = events[-1]["event_id"] if events else "n/a"
    latest_step = latest_step_id(events)
    sistema, tasks, risks, deliverable = next_items()
    source_status = source_evidence_status(events, require_local=False)
    print("STATUS: OK")
    print(f"- Eventos: {len(events)}")
    print(f"- Último evento: {latest}")
    print(f"- Último Step ID: {latest_step}")
    print(f"- Bloque activo: {sistema['bloque_activo']}")
    print(f"- Riesgo principal: {sistema['riesgo_principal_abierto']}")
    print(
        f"- Siguiente entregable: {sistema['siguiente_entregable']}"
        + (f" - {deliverable['nombre']}" if deliverable else "")
    )
    if tasks:
        print(f"- Próxima tarea sugerida: {tasks[0]['task_id']} - {tasks[0]['tarea']}")
    if risks:
        print(f"- Riesgo abierto prioritario: {risks[0]['risk_id']} - {risks[0]['riesgo']}")
    print(f"- Evidencia fuente de conversación: {source_status['repo_status']} (desde {source_evidence_policy()['desde_step_id']})")
    print("- Comandos sugeridos: `python 07_scripts/tesis.py doctor` y `python 07_scripts/tesis.py next`")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    events = ensure_canon_initialized()
    canon_errors = validate_events(events)
    drift = materialize_events(events, check=True)
    publication = publication_bundle_status(build=False)
    signoffs_total, signoffs_stale = current_signoff_status()
    human_errors = human_operability_errors()
    source_status = source_evidence_status(events, require_local=source_evidence_local_enabled())
    next_action = safe_next_action(
        drift=drift,
        publication_drift=publication["drift"],
        publication_errors=publication["errors"],
        human_errors=human_errors,
        source_repo_failures=source_status["repo_failures"],
        source_local_failures=source_status["local_failures"],
    )

    print(
        "DOCTOR: OK"
        if not (
            canon_errors
            or drift
            or publication["drift"]
            or publication["errors"]
            or human_errors
            or source_status["repo_failures"]
            or source_status["local_failures"]
        )
        else "DOCTOR: WARN"
    )
    print(f"- Python: {sys.executable}")
    print(f"- Raíz: {ROOT}")
    print(f"- Eventos canon: {len(events)}")
    print(f"- Último Step ID: {latest_step_id(events)}")
    print(f"- Errores de canon: {len(canon_errors)}")
    print(f"- Drift de proyecciones primarias: {len(drift)}")
    print(f"- Firmas humanas registradas: {signoffs_total}")
    print(f"- Firmas humanas desactualizadas: {signoffs_stale}")
    print(f"- Bundle público con drift: {len(publication['drift'])}")
    print(f"- Bundle público con errores: {len(publication['errors'])}")
    print(f"- Operabilidad humana: {'ok' if not human_errors else 'pendiente'}")
    print(f"- Source evidence repo status: {source_status['repo_status']}")
    print(f"- Source evidence local status: {source_status['local_status']}")
    print(f"- Fuente obligatoria desde: {source_evidence_policy()['desde_step_id']}")
    print(f"- Siguiente acción segura: {next_action}")

    for label, items in (
        ("canon", canon_errors),
        ("proyecciones", drift),
        ("publicación", publication["drift"]),
        ("publicación_sanitizada", publication["errors"]),
        ("operabilidad_humana", human_errors),
    ):
        for item in items:
            print(f"- [{label}] {item}")
    for result in source_status["repo_failures"]:
        for item in result["repo_errors"]:
            print(f"- [source_evidence_repo] {item}")
    for result in source_status["local_failures"]:
        for item in result["local_errors"]:
            print(f"- [source_evidence_local] {item}")

    if args.check and (
        canon_errors
        or drift
        or publication["drift"]
        or publication["errors"]
        or human_errors
        or source_status["repo_failures"]
        or source_status["local_failures"]
    ):
        return 1
    return 0


def cmd_next(_: argparse.Namespace) -> int:
    sistema, tasks, risks, deliverable = next_items()
    print("NEXT: OK")
    print(f"- Bloque activo: {sistema['bloque_activo']}")
    print(
        f"- Entregable vigente: {sistema['siguiente_entregable']}"
        + (f" - {deliverable['nombre']}" if deliverable else "")
    )
    print("- Tareas sugeridas:")
    for item in tasks[:5]:
        print(f"  - {item['task_id']} | {item['bloque']} | {item['prioridad']} | {item['fecha_objetivo']} | {item['tarea']}")
    print("- Riesgos prioritarios:")
    for item in risks[:3]:
        print(f"  - {item['risk_id']} | {item['impacto']} | {item['probabilidad']} | {item['riesgo']}")
    return 0


def cmd_publish(args: argparse.Namespace) -> int:
    result = publication_bundle_status(build=args.build)
    has_issues = bool(result["drift"] or result["errors"])
    mode = "BUILD" if args.build else "CHECK"
    print(f"PUBLISH: {mode}")
    print(f"- Salida: {result['output_root']}")
    print(f"- Artefactos: {len(result['artifacts'])}")
    print(f"- Drift: {len(result['drift'])}")
    print(f"- Errores: {len(result['errors'])}")
    for rel_path in result["drift"]:
        print(f"- Drift: {rel_path}")
    for error in result["errors"]:
        print(f"- Error: {error}")
    if not has_issues or args.build:
        print("PUBLISH: OK")
    return 1 if (not args.build and has_issues) else 0


def cmd_source_register(args: argparse.Namespace) -> int:
    ensure_canon_initialized()
    screenshot_paths = [item.strip() for item in args.screenshots.split(",") if item.strip()] if args.screenshots else []
    event = append_conversation_source(
        session_id=args.session_id,
        transcript_source_path=args.transcript,
        screenshot_source_paths=screenshot_paths,
        quoted_text=args.quote,
        captured_at=args.captured_at,
        message_role=args.message_role,
        message_locator=args.message_locator,
        capture_method=args.capture_method,
    )
    print("SOURCE: REGISTERED")
    print(f"- Event ID: {event['event_id']}")
    print(f"- Session ID: {event['payload']['session_id']}")
    print(f"- Transcript: {event['payload']['transcript_path']}")
    print(f"- Capturas: {len(event['payload']['screenshot_paths'])}")
    return 0


def _extract_quote_from_transcript(transcript_text: str) -> str:
    lines = [line.strip() for line in transcript_text.splitlines() if line.strip()]
    patterns = (
        re.compile(r"^(?:tesista|usuario|human)\s*:\s*(.+)$", re.IGNORECASE),
        re.compile(r"^(?:tesista|usuario).*?\)\s*:\s*(.+)$", re.IGNORECASE),
    )
    for line in reversed(lines):
        for pattern in patterns:
            match = pattern.match(line)
            if match:
                return match.group(1).strip()
    return lines[-1] if lines else ""


def cmd_source_auto_register(args: argparse.Namespace) -> int:
    ensure_canon_initialized()
    session_dir = ROOT / "00_sistema_tesis" / "evidencia_privada" / "conversaciones_codex" / sanitize_session_id_for_path(args.session_id)
    transcript_path = session_dir / "transcripcion.md"
    metadata_draft_path = session_dir / "metadata_draft.json"
    if not transcript_path.exists():
        create_conversation_source_scaffold(args.session_id, overwrite=False)

    message_role = args.message_role
    message_locator = args.message_locator
    capture_method = args.capture_method
    captured_at = args.captured_at

    if metadata_draft_path.exists():
        draft = json.loads(metadata_draft_path.read_text(encoding="utf-8"))
        message_role = message_role or str(draft.get("message_role", "")).strip()
        message_locator = message_locator or str(draft.get("message_locator", "")).strip()
        capture_method = capture_method or str(draft.get("capture_method", "")).strip()
        captured_at = captured_at or str(draft.get("captured_at", "")).strip()

    transcript_text = transcript_path.read_text(encoding="utf-8")
    quote = args.quote.strip() or _extract_quote_from_transcript(transcript_text).strip()
    if not quote:
        quote = "AUTO-QUOTE-NOT-FOUND"

    event = append_conversation_source(
        session_id=args.session_id,
        transcript_source_path=str(transcript_path),
        screenshot_source_paths=[],
        quoted_text=quote,
        captured_at=captured_at,
        message_role=message_role,
        message_locator=message_locator,
        capture_method=capture_method,
    )
    print("SOURCE: AUTO-REGISTERED")
    print(f"- Event ID: {event['event_id']}")
    print(f"- Session ID: {event['payload']['session_id']}")
    print(f"- Transcript: {event['payload']['transcript_path']}")
    print(f"- Quote: {event['payload']['quoted_text']}")
    return 0


def cmd_source_scaffold(args: argparse.Namespace) -> int:
    ensure_canon_initialized()
    result = create_conversation_source_scaffold(args.session_id, overwrite=args.overwrite)
    print("SOURCE: SCAFFOLD")
    print(f"- Session ID: {args.session_id}")
    print(f"- Directorio: {result['session_dir']}")
    print(f"- Transcripción: {result['transcript_path']}")
    print(f"- Draft metadata: {result['metadata_draft_path']}")
    return 0


def cmd_source_verify(args: argparse.Namespace) -> int:
    ensure_canon_initialized()
    result = verify_conversation_source_for_step(args.step_id, require_local=not args.repo_only)
    print("SOURCE: VERIFY")
    print(f"- Step ID: {result['step_id']}")
    print(f"- Source EVT: {result['source_event_id'] or 'N/A'}")
    print(f"- Repo status: {result['repo_status']}")
    print(f"- Local status: {result['local_status']}")
    for item in result["repo_errors"]:
        print(f"- Repo error: {item}")
    for item in result["local_errors"]:
        print(f"- Local error: {item}")
    return 0 if not (result["repo_errors"] or result["local_errors"]) else 1


def cmd_source_status(args: argparse.Namespace) -> int:
    events = ensure_canon_initialized()
    status = source_evidence_status(events, require_local=not args.repo_only and source_evidence_local_enabled())
    print("SOURCE: STATUS")
    print(f"- Repo status: {status['repo_status']}")
    print(f"- Local status: {status['local_status']}")
    print(f"- Steps con enforcement: {len(status['required_steps'])}")
    print(f"- Fallas repo: {len(status['repo_failures'])}")
    print(f"- Fallas local: {len(status['local_failures'])}")
    for result in status["repo_failures"]:
        print(f"- Repo failure: {result['step_id']} -> {result['source_event_id'] or 'sin fuente'}")
    for result in status["local_failures"]:
        print(f"- Local failure: {result['step_id']} -> {result['source_event_id'] or 'sin fuente'}")
    if args.check and (status["repo_failures"] or status["local_failures"]):
        return 1
    return 0


def cmd_session_open(args: argparse.Namespace) -> int:
    ensure_canon_initialized()
    path, content = create_session_content(args.session_id)
    append_session_record(rel_path=path, content=content, session_id=args.session_id)
    scaffold = create_conversation_source_scaffold(args.session_id, overwrite=False)
    print(f"Sesión abierta en {path}")
    print(f"Evidencia privada inicial en {scaffold['session_dir']}")
    return 0


def cmd_session_close(args: argparse.Namespace) -> int:
    ensure_canon_initialized()
    rel_path = normalize_path(args.path)
    content = (ROOT / rel_path).read_text(encoding="utf-8")
    append_session_record(rel_path=rel_path, content=content, session_id=args.session_id)
    print(f"Sesión cerrada y registrada en canon: {rel_path}")
    return 0


def cmd_event_append(args: argparse.Namespace) -> int:
    ensure_canon_initialized()
    if args.event_type == "human_validation":
        append_human_validation(
            step_id=args.step_id,
            audit_level=args.audit_level,
            content_text=args.content,
            linked_reference=args.linked_reference,
            matrix_summary=args.matrix_summary,
            matrix_reference=args.matrix_reference,
            ethical_alignment=args.ethical_alignment,
            state_label=args.state_label,
            session_id=args.session_id,
            confirmation_question=args.confirmation_question,
            confirmation_text=args.confirmation_text,
            confirmation_kind=args.confirmation_kind,
            source_event_id=args.source_event_id,
            provenance_status=args.provenance_status,
            quote_verification_status=args.quote_verification_status,
            source_capture_required=args.source_capture_required,
        )
    elif args.event_type == "artifact_signed":
        append_artifact_signed(rel_path=args.path, comment=args.comment, session_id=args.session_id)
    elif args.event_type == "agent_activity":
        files_touched = [item.strip() for item in args.files.split(",") if item.strip()]
        append_agent_activity(session_id=args.session_id, task_summary=args.task_summary, files_touched=files_touched, agent_name=args.agent_name)
    elif args.event_type == "session_recorded":
        append_session_record(rel_path=args.path, content=(ROOT / normalize_path(args.path)).read_text(encoding="utf-8"), session_id=args.session_id)
    else:
        payload = json.loads(args.payload) if args.payload else {}
        append_event(
            {
                "event_id": args.step_id or "",
                "event_type": args.event_type,
                "occurred_at": args.occurred_at,
                "actor": {"type": "system", "id": "tesis-cli", "display_name": "tesis-cli"},
                "session_id": args.session_id,
                "risk_level": args.audit_level,
                "links": {},
                "payload": payload,
                "affected_files": [normalize_path(item) for item in args.files.split(",") if item.strip()],
                "human_validation": {"required": False},
            }
        )
    print(f"Evento registrado: {args.event_type}")
    return 0


def cmd_task_close(args: argparse.Namespace) -> int:
    ensure_canon_initialized()
    backlog_path = ROOT / "01_planeacion" / "backlog.csv"
    rows: list[dict[str, str]] = []
    with backlog_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        found = False
        for row in reader:
            if row["task_id"] == args.task_id:
                row["estado"] = "hecho"
                found = True
            rows.append(row)
    if not found:
        print(f"[ERROR] No se encontró la tarea {args.task_id}")
        return 1
    with backlog_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    files = [normalize_path(item) for item in args.files.split(",") if item.strip()]
    for rel_path in files:
        append_artifact_signed(rel_path=rel_path, comment=args.comment, session_id=args.session_id)
    append_agent_activity(session_id=args.session_id or "workflow_assistant", task_summary=f"Finalización de {args.task_id}", files_touched=files)
    if args.rebuild:
        run_python_script("07_scripts/build_all.py")
    print(f"[OK] Tarea {args.task_id} cerrada")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI canónica del sistema operativo de tesis.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    materialize = subparsers.add_parser("materialize")
    materialize.add_argument("--check", action="store_true")
    materialize.set_defaults(func=cmd_materialize)

    audit = subparsers.add_parser("audit")
    audit.add_argument("--check", action="store_true")
    audit.set_defaults(func=cmd_audit)

    status = subparsers.add_parser("status")
    status.set_defaults(func=cmd_status)

    doctor = subparsers.add_parser("doctor")
    doctor.add_argument("--check", action="store_true")
    doctor.set_defaults(func=cmd_doctor)

    next_cmd = subparsers.add_parser("next")
    next_cmd.set_defaults(func=cmd_next)

    publish = subparsers.add_parser("publish")
    publish_group = publish.add_mutually_exclusive_group()
    publish_group.add_argument("--check", action="store_true")
    publish_group.add_argument("--build", action="store_true")
    publish.set_defaults(func=cmd_publish, build=False)

    source = subparsers.add_parser("source")
    source_subparsers = source.add_subparsers(dest="source_command", required=True)
    source_register = source_subparsers.add_parser("register")
    source_register.add_argument("--session-id", required=True)
    source_register.add_argument("--transcript", required=True)
    source_register.add_argument("--screenshots", default="", help="Lista separada por comas de capturas fuente (opcional).")
    source_register.add_argument("--quote", required=True)
    source_register.add_argument("--captured-at", default="")
    source_register.add_argument("--message-role", default="")
    source_register.add_argument("--message-locator", default="")
    source_register.add_argument("--capture-method", default="")
    source_register.set_defaults(func=cmd_source_register)

    source_scaffold = source_subparsers.add_parser("scaffold")
    source_scaffold.add_argument("--session-id", required=True)
    source_scaffold.add_argument("--overwrite", action="store_true")
    source_scaffold.set_defaults(func=cmd_source_scaffold)

    source_auto_register = source_subparsers.add_parser("auto-register")
    source_auto_register.add_argument("--session-id", required=True)
    source_auto_register.add_argument("--quote", default="")
    source_auto_register.add_argument("--captured-at", default="")
    source_auto_register.add_argument("--message-role", default="")
    source_auto_register.add_argument("--message-locator", default="")
    source_auto_register.add_argument("--capture-method", default="")
    source_auto_register.set_defaults(func=cmd_source_auto_register)

    source_verify = source_subparsers.add_parser("verify")
    source_verify.add_argument("--step-id", required=True)
    source_verify.add_argument("--repo-only", action="store_true")
    source_verify.set_defaults(func=cmd_source_verify)

    source_status = source_subparsers.add_parser("status")
    source_status.add_argument("--check", action="store_true")
    source_status.add_argument("--repo-only", action="store_true")
    source_status.set_defaults(func=cmd_source_status)

    session = subparsers.add_parser("session")
    session_subparsers = session.add_subparsers(dest="session_command", required=True)
    session_open = session_subparsers.add_parser("open")
    session_open.add_argument("--session-id", required=True)
    session_open.set_defaults(func=cmd_session_open)
    session_close = session_subparsers.add_parser("close")
    session_close.add_argument("--session-id", required=True)
    session_close.add_argument("--path", required=True)
    session_close.set_defaults(func=cmd_session_close)

    event = subparsers.add_parser("event")
    event_subparsers = event.add_subparsers(dest="event_command", required=True)
    event_append = event_subparsers.add_parser("append")
    event_append.add_argument("--type", dest="event_type", required=True)
    event_append.add_argument("--session-id", default="")
    event_append.add_argument("--step-id", default="")
    event_append.add_argument("--audit-level", default="MEDIO")
    event_append.add_argument("--linked-reference", default="[DEC-0014]")
    event_append.add_argument("--matrix-reference", default="")
    event_append.add_argument("--matrix-summary", default="Cambio registrado en canon")
    event_append.add_argument("--ethical-alignment", default="Responsabilidad (ISO 42001)")
    event_append.add_argument("--state-label", default="[x] Validado")
    event_append.add_argument("--content", default="")
    event_append.add_argument("--confirmation-question", default="")
    event_append.add_argument("--confirmation-text", default="")
    event_append.add_argument("--confirmation-kind", default="")
    event_append.add_argument("--source-event-id", default="")
    event_append.add_argument("--provenance-status", default="")
    event_append.add_argument("--quote-verification-status", default="")
    event_append.add_argument("--source-capture-required", action="store_true", default=None)
    event_append.add_argument("--path", default="")
    event_append.add_argument("--comment", default="Revisado y aprobado por tesista humano.")
    event_append.add_argument("--files", default="")
    event_append.add_argument("--task-summary", default="")
    event_append.add_argument("--agent-name", default="")
    event_append.add_argument("--occurred-at", default="")
    event_append.add_argument("--payload", default="")
    event_append.set_defaults(func=cmd_event_append)

    task = subparsers.add_parser("task")
    task_subparsers = task.add_subparsers(dest="task_command", required=True)
    task_close = task_subparsers.add_parser("close")
    task_close.add_argument("--task-id", required=True)
    task_close.add_argument("--files", required=True)
    task_close.add_argument("--comment", required=True)
    task_close.add_argument("--session-id", default="workflow_assistant")
    task_close.add_argument("--rebuild", action="store_true")
    task_close.set_defaults(func=cmd_task_close)

    sync = subparsers.add_parser("sync")
    sync.add_argument("--message", required=True)
    sync.add_argument("--derived-message", default="")
    sync.add_argument("--step-id", default="")
    sync.add_argument("--agent", default="")
    sync.add_argument("--push", action="store_true")
    sync.add_argument("--remote", default="origin")
    sync.add_argument("--branch", default="")
    sync.set_defaults(func=cmd_sync)

    split_staged = subparsers.add_parser("split-staged")
    split_staged.add_argument("--commit", action="store_true")
    split_staged.add_argument("--derived-message", default="chore: synchronize generated projections")
    split_staged.add_argument("--step-id", default="")
    split_staged.add_argument("--agent", default="")
    split_staged.add_argument("--no-sign", action="store_true")
    split_staged.set_defaults(func=cmd_split_staged)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
