from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import DomainPolicy, DomainSecretPolicy


ROOT = Path(__file__).resolve().parents[3]


def _load_json_document(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_domain_policies(root: Path | None = None) -> dict[str, Any]:
    repo_root = root or ROOT
    domain_boundaries = _load_json_document(repo_root / "manifests" / "domain_boundaries.yaml")
    backend_routing = _load_json_document(repo_root / "manifests" / "backend_routing_policy.yaml")

    routing_preferences = backend_routing.get("dominios", {})
    domains: dict[str, DomainPolicy] = {}
    for item in domain_boundaries.get("dominios", []):
        domain_id = str(item["id"])
        domains[domain_id] = DomainPolicy(
            domain_id=domain_id,
            description=str(item["descripcion"]),
            allowed_backends=list(item.get("backends", [])),
            routing_preferences=list(routing_preferences.get(domain_id, {}).get("preferencia", [])),
            workspace_roots=list(item.get("rutas", [])),
            publicable=item.get("publicable", False),
        )

    return {
        "routing_hierarchy": list(backend_routing.get("jerarquia", [])),
        "fallback": list(backend_routing.get("fallback", [])),
        "criteria": list(backend_routing.get("criterios", [])),
        "domains": domains,
    }


def load_runtime_contracts(root: Path | None = None) -> dict[str, Any]:
    repo_root = root or ROOT
    return _load_json_document(repo_root / "manifests" / "openclaw_runtime_contracts.yaml")


def load_provider_registry(root: Path | None = None) -> dict[str, Any]:
    repo_root = root or ROOT
    return _load_json_document(repo_root / "manifests" / "openclaw_provider_registry.yaml")


def load_domain_secret_policies(root: Path | None = None) -> dict[str, Any]:
    repo_root = root or ROOT
    document = _load_json_document(repo_root / "manifests" / "openclaw_domain_secret_policy.yaml")
    domains: dict[str, DomainSecretPolicy] = {}
    for domain_id, item in document.get("domains", {}).items():
        domains[domain_id] = DomainSecretPolicy(
            domain_id=domain_id,
            network_mode=str(item.get("network_mode", "offline")),
            allow_web_assisted=bool(item.get("allow_web_assisted", False)),
            allow_api_formal=bool(item.get("allow_api_formal", False)),
            allow_publication=item.get("allow_publication", False),
            requires_strict_redaction=bool(item.get("requires_strict_redaction", True)),
            providers={str(provider): [str(value) for value in values] for provider, values in item.get("providers", {}).items()},
        )
    return {
        "env_root": str(document.get("env_root", "/etc/tesis-os/domains")),
        "domains": domains,
    }


def load_budget_policy(root: Path | None = None) -> dict[str, Any]:
    repo_root = root or ROOT
    return _load_json_document(repo_root / "manifests" / "openclaw_budget_policy.yaml")
