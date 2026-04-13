from __future__ import annotations

import hashlib
import json
import os
import re
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import guardrails
from data_io import load_jsonl_path, load_structured_path


CONFIG_RELATIVE_PATH = "00_sistema_tesis/config/serena_mcp.json"
EVENTS_RELATIVE_PATH = "00_sistema_tesis/canon/events.jsonl"
GOVERNANCE_RELATIVE_PATH = "00_sistema_tesis/config/ia_gobernanza.yaml"
AGENT_IDENTITY_RELATIVE_PATH = "00_sistema_tesis/config/agent_identity.json"
STEP_ID_PATTERN = re.compile(r"^VAL-STEP-[A-Za-z0-9_-]+$")
SOURCE_EVENT_PATTERN = re.compile(r"^EVT-[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class ToolContract:
    name: str
    description: str
    risk_level: str
    write_scope: str
    requires_step_id: bool
    enabled: bool


def resolve_root(root: Path | None = None) -> Path:
    if root is not None:
        return root.resolve()
    env_root = os.getenv("SISTEMA_TESIS_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[1]


def normalize_rel_path(path: str) -> str:
    normalized = str(path).strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _load_structured(root: Path, relative_path: str) -> Any:
    return load_structured_path(root / normalize_rel_path(relative_path))


def load_serena_config(root: Path | None = None) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    payload = _load_structured(resolved_root, CONFIG_RELATIVE_PATH)
    if not isinstance(payload, dict):
        raise ValueError("serena_mcp.json debe contener un objeto")
    return payload


def load_events(root: Path | None = None) -> list[dict[str, Any]]:
    resolved_root = resolve_root(root)
    return load_jsonl_path(resolved_root / EVENTS_RELATIVE_PATH)


def load_governance(root: Path | None = None) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    payload = _load_structured(resolved_root, GOVERNANCE_RELATIVE_PATH)
    if not isinstance(payload, dict):
        raise ValueError("ia_gobernanza.yaml debe contener un objeto")
    return payload


def load_tool_contracts(root: Path | None = None) -> dict[str, ToolContract]:
    config = load_serena_config(root)
    tool_payloads = dict(config.get("tools", {}))
    contracts: dict[str, ToolContract] = {}
    for name, payload in tool_payloads.items():
        item = dict(payload)
        contracts[name] = ToolContract(
            name=name,
            description=str(item.get("description", "")).strip(),
            risk_level=str(item.get("risk_level", "MEDIO")).strip(),
            write_scope=str(item.get("write_scope", "read_only")).strip(),
            requires_step_id=bool(item.get("requires_step_id", False)),
            enabled=bool(item.get("enabled", True)),
        )
    return contracts


def get_tool_contract(tool_name: str, root: Path | None = None) -> ToolContract:
    contracts = load_tool_contracts(root)
    if tool_name not in contracts:
        raise KeyError(f"Herramienta MCP no registrada: {tool_name}")
    return contracts[tool_name]


def step_sequence_value(step_id: str) -> int | None:
    match = re.match(r"^VAL-STEP-(\d+)$", step_id.strip())
    if not match:
        return None
    return int(match.group(1))


def source_evidence_required(step_id: str, root: Path | None = None) -> bool:
    if not STEP_ID_PATTERN.match(step_id.strip()):
        return False
    governance = load_governance(root)
    section = dict(governance.get("evidencia_fuente_conversacion", {}))
    activation = dict(section.get("activacion", {}))
    enabled = bool(section.get("obligatoria_para_val_step_nuevo", True))
    threshold = step_sequence_value(str(activation.get("desde_step_id", "VAL-STEP-501")).strip())
    current = step_sequence_value(step_id.strip())
    if not enabled or threshold is None or current is None:
        return False
    return current >= threshold


def event_index(root: Path | None = None) -> dict[str, dict[str, Any]]:
    return {
        str(event.get("event_id", "")).strip(): event
        for event in load_events(root)
        if isinstance(event, dict)
    }


def step_exists(step_id: str, root: Path | None = None) -> bool:
    return step_id.strip() in event_index(root)


def source_event_exists(source_event_id: str, root: Path | None = None) -> bool:
    event = event_index(root).get(source_event_id.strip())
    return bool(event and str(event.get("event_type", "")).strip() == "conversation_source_registered")


def validate_step_and_source(
    *,
    step_id: str,
    source_event_id: str,
    root: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    normalized_step = step_id.strip()
    normalized_source = source_event_id.strip()

    if not normalized_step:
        errors.append("Se requiere step_id para esta operación.")
        return errors
    if not STEP_ID_PATTERN.match(normalized_step):
        errors.append("step_id debe cumplir el formato VAL-STEP-XXX.")
        return errors
    if not step_exists(normalized_step, root):
        errors.append(f"El step_id `{normalized_step}` no existe en el canon.")
        return errors
    if source_evidence_required(normalized_step, root):
        if not normalized_source:
            errors.append(f"{normalized_step} requiere source_event_id por política activa.")
            return errors
        if not SOURCE_EVENT_PATTERN.match(normalized_source):
            errors.append("source_event_id debe cumplir el formato EVT-XXX.")
            return errors
        indexed = event_index(root)
        source_event = indexed.get(normalized_source)
        if not source_event or str(source_event.get("event_type", "")).strip() != "conversation_source_registered":
            errors.append(f"`{normalized_source}` no existe como conversation_source_registered.")
            return errors
        step_event = indexed.get(normalized_step, {})
        human_validation = dict(step_event.get("human_validation", {}))
        linked_source = str(human_validation.get("source_event_id", "")).strip()
        if linked_source and linked_source != normalized_source:
            errors.append(
                f"El step_id `{normalized_step}` está enlazado a `{linked_source}` y no a `{normalized_source}`."
            )
    return errors


def _configured_roots(config: dict[str, Any], key: str) -> list[str]:
    roots = config.get("paths", {}).get(key, [])
    if not isinstance(roots, list):
        return []
    return [normalize_rel_path(item) for item in roots if str(item).strip()]


def _configured_allowlist(config: dict[str, Any], key: str) -> set[str]:
    items = config.get("paths", {}).get(key, [])
    if not isinstance(items, list):
        return set()
    return {normalize_rel_path(item) for item in items if str(item).strip()}


def is_under_prefix(rel_path: str, prefixes: list[str]) -> bool:
    return any(rel_path == prefix.rstrip("/") or rel_path.startswith(prefix) for prefix in prefixes)


def is_protected_path(rel_path: str, root: Path | None = None) -> bool:
    resolved_root = resolve_root(root)
    normalized = normalize_rel_path(rel_path)
    target = resolved_root / normalized
    if normalized in guardrails.UNPROTECTED_EXACT_PATHS:
        return False
    if any(normalized.startswith(prefix) for prefix in guardrails.UNPROTECTED_DIR_PREFIXES):
        return False
    if normalized in guardrails.PROTECTED_EXACT_PATHS:
        return True
    if any(normalized.startswith(prefix) for prefix in guardrails.PROTECTED_DIR_PREFIXES):
        return True
    if target.exists() and target.suffix.lower() in {".md", ".markdown", ".yaml", ".yml", ".html"}:
        try:
            content = target.read_text(encoding="utf-8")
        except OSError:
            return False
        return "<!-- SISTEMA_TESIS:PROTEGIDO -->" in content
    return False


def classify_write_scope(rel_path: str, root: Path | None = None) -> str:
    resolved_root = resolve_root(root)
    config = load_serena_config(resolved_root)
    normalized = normalize_rel_path(rel_path)
    derived_roots = _configured_roots(config, "derived_write_roots")
    derived_allowlist = _configured_allowlist(config, "derived_write_allowlist")
    controlled_roots = _configured_roots(config, "controlled_write_roots")

    if normalized in derived_allowlist or is_under_prefix(normalized, derived_roots):
        return "derived"
    if is_protected_path(normalized, resolved_root):
        return "protected"
    if is_under_prefix(normalized, controlled_roots):
        return "controlled"
    return "blocked"


def classify_path_risk(rel_path: str, root: Path | None = None) -> str:
    normalized = normalize_rel_path(rel_path)
    if is_protected_path(normalized, root):
        return "ALTO"
    if normalized.startswith(".vscode/"):
        return "ALTO"
    if normalized.startswith("00_sistema_tesis/config/"):
        return "ALTO"
    if normalized.startswith("07_scripts/"):
        return "ALTO"
    if normalized.startswith("docs/"):
        return "MEDIO"
    return "MEDIO"


def strongest_write_scope(scopes: list[str]) -> str:
    order = {"read_only": 0, "derived": 1, "controlled": 2, "protected": 3, "blocked": 4}
    highest = "read_only"
    best_value = -1
    for scope in scopes:
        current = order.get(scope, -1)
        if current > best_value:
            best_value = current
            highest = scope
    return highest


def strongest_risk_level(levels: list[str]) -> str:
    order = {"BAJO": 0, "MEDIO": 1, "ALTO": 2, "CRÍTICO": 3}
    highest = "BAJO"
    best_value = -1
    for level in levels:
        current = order.get(level, 1)
        if current > best_value:
            best_value = current
            highest = level
    return highest


def tool_declaration(tool_name: str, root: Path | None = None) -> dict[str, Any]:
    contract = get_tool_contract(tool_name, root)
    return {
        "name": contract.name,
        "description": contract.description,
        "risk_level": contract.risk_level,
        "write_scope": contract.write_scope,
        "requires_step_id": contract.requires_step_id,
        "enabled": contract.enabled,
    }


def preflight(
    *,
    tool_name: str,
    target_paths: list[str] | None = None,
    step_id: str = "",
    source_event_id: str = "",
    intent: str = "",
    root: Path | None = None,
) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    contract = get_tool_contract(tool_name, resolved_root)
    normalized_targets = [normalize_rel_path(path) for path in (target_paths or []) if str(path).strip()]
    path_assessments = []
    path_scopes: list[str] = [contract.write_scope]
    risk_levels: list[str] = [contract.risk_level]
    errors: list[str] = []

    for rel_path in normalized_targets:
        scope = classify_write_scope(rel_path, resolved_root)
        risk = classify_path_risk(rel_path, resolved_root)
        path_assessments.append(
            {
                "path": rel_path,
                "write_scope": scope,
                "risk_level": risk,
                "protected": is_protected_path(rel_path, resolved_root),
            }
        )
        path_scopes.append(scope)
        risk_levels.append(risk)
        if scope == "blocked":
            errors.append(f"La ruta `{rel_path}` queda fuera del alcance permitido del MCP.")

    effective_write_scope = strongest_write_scope(path_scopes)
    effective_risk = strongest_risk_level(risk_levels)
    requires_step = contract.requires_step_id or effective_write_scope in {"controlled", "protected"}
    requires_source = bool(step_id.strip()) and source_evidence_required(step_id, resolved_root)

    if requires_step:
        errors.extend(validate_step_and_source(step_id=step_id, source_event_id=source_event_id, root=resolved_root))

    status = "ok"
    next_required_action = "none"
    if errors:
        status = "blocked"
        next_required_action = errors[0]
    elif requires_step or effective_risk in {"ALTO", "CRÍTICO"}:
        status = "requires_human"
        next_required_action = "Confirmar que el step_id y la intención siguen vigentes antes de ejecutar."

    return {
        "status": status,
        "risk_level": effective_risk,
        "write_scope": effective_write_scope,
        "tool": tool_declaration(tool_name, resolved_root),
        "intent": intent.strip(),
        "evidence": {
            "step_id": step_id.strip(),
            "source_event_id": source_event_id.strip(),
            "requires_step_id": requires_step,
            "requires_source_event_id": requires_source,
        },
        "artifacts": path_assessments,
        "next_required_action": next_required_action,
        "errors": errors,
    }


@contextmanager
def _patched_guardrails_root(root: Path):
    previous_root = guardrails.ROOT
    previous_manifest = guardrails.MANIFEST_PATH
    guardrails.ROOT = root
    guardrails.MANIFEST_PATH = root / "00_sistema_tesis" / "config" / "integrity_manifest.json"
    try:
        yield
    finally:
        guardrails.ROOT = previous_root
        guardrails.MANIFEST_PATH = previous_manifest


def backup_file(rel_path: str, root: Path | None = None) -> str | None:
    resolved_root = resolve_root(root)
    target = resolved_root / normalize_rel_path(rel_path)
    if not target.exists():
        return None
    with _patched_guardrails_root(resolved_root):
        guardrails.backup_file(target)
    return normalize_rel_path(rel_path)


def update_manifest(root: Path | None = None) -> None:
    resolved_root = resolve_root(root)
    with _patched_guardrails_root(resolved_root):
        guardrails.update_manifest()


def update_manifest_for_path(rel_path: str, root: Path | None = None) -> None:
    resolved_root = resolve_root(root)
    with _patched_guardrails_root(resolved_root):
        guardrails.update_manifest_for_path(resolved_root / normalize_rel_path(rel_path))


def file_sha256_text(content: str) -> str:
    normalized = content.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def runtime_identity(root: Path | None = None) -> dict[str, str]:
    resolved_root = resolve_root(root)
    config = load_serena_config(resolved_root)
    env_map = dict(config.get("runtime_env", {}))
    payload = _load_structured(resolved_root, AGENT_IDENTITY_RELATIVE_PATH)
    canonical_identity = dict(payload.get("agent_identity", {}))
    identity = {
        "agent_role": str(canonical_identity.get("agent_role", "")).strip(),
        "provider": str(canonical_identity.get("provider", "")).strip(),
        "model_version": str(canonical_identity.get("model_version", "")).strip(),
        "runtime_label": str(canonical_identity.get("runtime_label", "")).strip(),
        "host_kind": "",
    }
    for key, env_key in {
        "agent_role": str(env_map.get("agent_role", "SISTEMA_TESIS_AGENT_ROLE")),
        "provider": str(env_map.get("provider", "SISTEMA_TESIS_AGENT_PROVIDER")),
        "model_version": str(env_map.get("model_version", "SISTEMA_TESIS_AGENT_MODEL_VERSION")),
        "runtime_label": str(env_map.get("runtime_label", "SISTEMA_TESIS_AGENT_RUNTIME")),
        "host_kind": str(env_map.get("host_kind", "SISTEMA_TESIS_MCP_HOST_KIND")),
    }.items():
        override = os.getenv(env_key, "").strip()
        if override:
            identity[key] = override
    return identity
