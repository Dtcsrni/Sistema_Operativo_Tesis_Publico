from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from common import ROOT, now_stamp
from data_io import load_structured_path


DEFAULT_CONFIG_PATH = "00_sistema_tesis/config/agent_task_router.json"
VALID_MUTATION_POLICIES = {
    "read_only",
    "proposal_only",
    "local_model_executes_no_repo_write",
    "agent_integrates_after_gates",
}


class RouterError(ValueError):
    pass


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    raise RouterError(f"Se esperaba lista o string, recibido: {type(value).__name__}")


def load_router_config(config_relative_path: str = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    path = ROOT / config_relative_path
    if not path.exists():
        raise FileNotFoundError(f"No existe configuración del router: {config_relative_path}")
    payload = load_structured_path(path)
    if not isinstance(payload, dict):
        raise RouterError("La configuración del router debe ser un objeto")
    return payload


def _has_env_var(names: list[str]) -> bool:
    return any(os.getenv(name, "").strip() for name in names)


def _normalize_privacy(task: dict[str, Any], config: dict[str, Any]) -> str:
    privacy = str(task.get("privacy_class") or "").strip().lower()
    valid = set(str(item).lower() for item in config.get("privacy_classes", []))
    target_paths = _as_list(task.get("target_paths"))
    sensitive_prefixes = tuple(str(item) for item in config.get("sensitive_path_prefixes", []))
    touches_sensitive = any(path == prefix.rstrip("/") or path.startswith(prefix) for path in target_paths for prefix in sensitive_prefixes)
    if touches_sensitive:
        return "restricted"
    if not privacy:
        return "private"
    if privacy not in valid:
        raise RouterError(f"privacy_class invalida: {privacy}")
    return privacy


def _normalize_risk(task: dict[str, Any], config: dict[str, Any]) -> str:
    risk = str(task.get("risk_level") or "MEDIO").strip().upper()
    valid = set(str(item).upper() for item in config.get("risk_levels", []))
    if risk not in valid:
        raise RouterError(f"risk_level invalido: {risk}")
    return risk


def _task_profile(task: dict[str, Any], privacy: str) -> str:
    task_type = str(task.get("task_type") or "").strip().lower()
    domain = str(task.get("domain") or "").strip().lower()
    complexity = str(task.get("complexity") or task.get("baseline_complexity") or "media").strip().lower()
    target_paths = _as_list(task.get("target_paths"))
    needs_external_docs = bool(task.get("requires_external_docs") or task.get("needs_external_docs"))
    runtime_target = str(task.get("runtime_target") or "").strip().lower()

    if needs_external_docs:
        return "docs_external"
    if privacy in {"public", "redacted"} and bool(task.get("allow_free_cloud")):
        return "public_cloud"
    if runtime_target == "docker" or "docker" in task_type or "contenedor" in task_type:
        return "docker_runtime"
    if target_paths or "gobernanza" in task_type or "trazabilidad" in task_type:
        return "repo_governance"
    if domain in {"academico", "profesional"} and complexity in {"alta", "critica", "crítica"}:
        return "academic_heavy"
    return "default"


def _blocked_routes(
    *,
    task: dict[str, Any],
    config: dict[str, Any],
    privacy: str,
    allowed_routes: list[str],
) -> dict[str, str]:
    blocked: dict[str, str] = {}
    forbidden = set(_as_list(task.get("forbidden_routes")))
    cloud_allowed = set(str(item) for item in config.get("cloud_allowed_privacy_classes", []))
    context7_allowed = set(str(item) for item in config.get("context7_allowed_privacy_classes", []))
    cloud_routes = set(str(item) for item in config.get("cloud_free_routes", []))
    context_routes = set(str(item) for item in config.get("external_context_routes", []))
    github_required_env = _as_list(config.get("github_models", {}).get("required_env_vars"))

    for route in allowed_routes:
        if route in forbidden:
            blocked[route] = "forbidden_by_task"
        elif route in cloud_routes and privacy not in cloud_allowed:
            blocked[route] = "privacy_blocks_free_cloud"
        elif route in cloud_routes and not _has_env_var(github_required_env):
            blocked[route] = "missing_github_models_token"
        elif route in context_routes and privacy not in context7_allowed:
            blocked[route] = "privacy_blocks_external_context"
    return blocked


def _build_subtasks(task: dict[str, Any], route: str, privacy: str, risk: str) -> list[dict[str, Any]]:
    objective = str(task.get("objective") or task.get("task_summary") or task.get("task_type") or "tarea agéntica").strip()
    mutation_policy = str(task.get("mutation_policy") or "agent_integrates_after_gates").strip()
    if mutation_policy not in VALID_MUTATION_POLICIES:
        raise RouterError(f"mutation_policy invalida: {mutation_policy}")
    return [
        {
            "id": "scope",
            "instruction": f"Delimitar alcance y evidencias mínimas para: {objective}",
            "route": "serena" if route != "context7_docs" else "context7_docs",
            "expected_output": "referencias compactas, rutas relevantes y riesgos iniciales",
        },
        {
            "id": "execute",
            "instruction": "Producir propuesta estructurada sin escribir directamente en el repositorio.",
            "route": route,
            "expected_output": "summary, proposed_patch_or_steps, confidence, evidence_refs, risks, needs_human_step_id",
            "mutation_policy": mutation_policy,
        },
        {
            "id": "gate",
            "instruction": "Evaluar calidad, privacidad, trazabilidad y necesidad de Step ID antes de integrar.",
            "route": "wsl_native",
            "expected_output": "quality_gate_passed, blocked_reasons, next_required_action",
            "privacy_class": privacy,
            "risk_level": risk,
        },
    ]


def classify_task(task: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = config or load_router_config()
    privacy = _normalize_privacy(task, config)
    risk = _normalize_risk(task, config)
    profile = _task_profile(task, privacy)
    route_preferences = dict(config.get("route_preferences", {}))
    preferred_routes = list(route_preferences.get(profile) or route_preferences.get("default") or [config.get("default_route", "wsl_native")])
    explicit_allowed = _as_list(task.get("allowed_routes"))
    allowed_routes = explicit_allowed or preferred_routes
    if not allowed_routes:
        allowed_routes = [str(config.get("default_route", "wsl_native"))]

    blocked = _blocked_routes(task=task, config=config, privacy=privacy, allowed_routes=allowed_routes)
    candidates = [route for route in allowed_routes if route not in blocked]
    if not candidates:
        fallback = str(config.get("default_route", "wsl_native"))
        candidates = [fallback]
        blocked[fallback] = "all_preferred_routes_blocked_fallback_requires_manual_review"
    recommended = candidates[0]

    max_tokens = int(task.get("max_tokens") or 1800)
    max_latency_ms = int(task.get("max_latency_ms") or 90000)
    quality_gate = dict(config.get("quality_gate_defaults", {}))
    quality_gate.update(dict(task.get("quality_gate", {})) if isinstance(task.get("quality_gate"), dict) else {})

    return {
        "generated_at": now_stamp(),
        "task_id": str(task.get("task_id") or "task-router-local"),
        "profile": profile,
        "privacy_class": privacy,
        "risk_level": risk,
        "recommended_route": recommended,
        "candidate_routes": candidates,
        "blocked_routes": blocked,
        "limits": {
            "max_tokens": max_tokens,
            "max_latency_ms": max_latency_ms,
        },
        "quality_gate": quality_gate,
        "subtasks": _build_subtasks(task, recommended, privacy, risk),
        "notes": [
            "Los modelos locales pueden ejecutar subtareas, pero no escriben directo al repo.",
            "GitHub Models solo se permite con contexto public/redacted y token models:read.",
            "Context7 se limita a documentación externa; Serena conserva repo/canon/gobernanza.",
        ],
    }


def _load_task(args: argparse.Namespace) -> dict[str, Any]:
    if args.task_json:
        payload = json.loads(args.task_json)
    elif args.task_file:
        payload = load_structured_path(Path(args.task_file))
    else:
        raise RouterError("Se requiere --task-json o --task-file")
    if not isinstance(payload, dict):
        raise RouterError("La tarea debe ser un objeto JSON")
    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Router agéntico local-first para economía de tokens")
    parser.add_argument("--config", default=DEFAULT_CONFIG_PATH, help="Ruta relativa de configuración")
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify = subparsers.add_parser("classify", help="Clasificar tarea y emitir ruta recomendada")
    classify.add_argument("--task-json", default="", help="Tarea JSON inline")
    classify.add_argument("--task-file", default="", help="Ruta a tarea JSON/YAML")

    dispatch = subparsers.add_parser("dispatch", help="Preparar despacho seguro de subtareas")
    dispatch.add_argument("--task-json", default="", help="Tarea JSON inline")
    dispatch.add_argument("--task-file", default="", help="Ruta a tarea JSON/YAML")
    dispatch.add_argument("--dry-run", action="store_true", help="No ejecutar modelos; solo emitir plan")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_router_config(args.config)
    task = _load_task(args)
    result = classify_task(task, config)
    if args.command == "dispatch":
        result["dispatch_status"] = "dry_run" if args.dry_run else "planned_only"
        result["dispatch_note"] = "La integración de respuestas al repo queda reservada al agente principal tras gates."
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
