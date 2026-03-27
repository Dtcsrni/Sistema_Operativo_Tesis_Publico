from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

from common import ROOT, load_agent_identity, load_yaml_json


TEXT_SUFFIXES = {
    ".appcache",
    ".css",
    ".csv",
    ".html",
    ".js",
    ".json",
    ".manifest",
    ".md",
    ".svg",
    ".txt",
    ".webmanifest",
    ".xml",
    ".yml",
    ".yaml",
}
DEFAULT_PUBLICATION_CONFIG = "00_sistema_tesis/config/publicacion.yaml"
FILE_URI_PATTERN = re.compile(r"file:///[^\s)>\]`\"']+")
WINDOWS_PATH_PATTERN = re.compile(r"(?<![A-Za-z])[A-Za-z]:[\\/][^\s)>\]`\"']+")
GITHUB_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{36}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{82}"),
)
CURP_PATTERN = re.compile(r"\b[A-Z]{4}\d{6}[HM][A-Z]{5}[A-Z0-9]\d\b", re.IGNORECASE)


def load_publication_config(relative_path: str = DEFAULT_PUBLICATION_CONFIG) -> dict:
    return load_yaml_json(relative_path)


def _resolved_output_root(config: dict) -> Path:
    return ROOT / config["salida"]["directorio"]


def _relative_output_path(config: dict, rel_path: str) -> str:
    return str((Path(config["salida"]["directorio"]) / rel_path).as_posix())


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def _regex_rules(config: dict) -> list[tuple[str, re.Pattern[str], str]]:
    rules: list[tuple[str, re.Pattern[str], str]] = []
    for item in config.get("sanitizacion", {}).get("redacciones_regex", []):
        rules.append((item["nombre"], re.compile(item["patron"], re.IGNORECASE), item["reemplazo"]))
    return rules


def _literal_rules(config: dict) -> list[tuple[str, str]]:
    identity = load_agent_identity()
    rules = [
        (str(ROOT), "[ruta_local_redactada]"),
        (ROOT.as_posix(), "[ruta_local_redactada]"),
        ("00_sistema_tesis/canon/events.jsonl", "[canon_privado]"),
        ("00_sistema_tesis/canon/", "[canon_privado]/"),
        ("00_sistema_tesis/canon", "[canon_privado]"),
        ("00_sistema_tesis/bitacora/log_conversaciones_ia.md", "[ledger_privado]"),
        ("00_sistema_tesis/bitacora/matriz_trazabilidad.md", "[matriz_privada]"),
        ("00_sistema_tesis/bitacora/indice_fuentes_conversacion.md", "[indice_fuentes_privado]"),
        ("00_sistema_tesis/bitacora/", "[bitacora_privada]/"),
        ("00_sistema_tesis/bitacora", "[bitacora_privada]"),
        ("00_sistema_tesis/reportes_semanales/", "[reportes_privados]/"),
        ("00_sistema_tesis/reportes_semanales", "[reportes_privados]"),
        ("00_sistema_tesis/evidencia_privada/", "[evidencia_privada_redactada]/"),
        ("00_sistema_tesis/evidencia_privada", "[evidencia_privada_redactada]"),
        ("00_sistema_tesis/bitacora/audit_history", "[historial_interno_redactado]"),
        ("00_sistema_tesis/config/agent_identity.json", "[identidad_agente_privada]"),
        ("00_sistema_tesis/config/sign_offs.json", "[firmas_humanas_privadas]"),
        ("00_sistema_tesis/ia_journal.json", "[journal_ia_privado]"),
        ("06_dashboard/generado/reporte_consistencia.md", "[reporte_interno_redactado]"),
        (identity["agent_role"], "[agente_ia_interno]"),
        (identity["provider"], "[proveedor_ia_interno]"),
        (identity["model_version"], "[modelo_ia_interno]"),
        (identity["runtime_label"], "[runtime_ia_interno]"),
    ]
    for item in config.get("sanitizacion", {}).get("redacciones_literales", []):
        rules.append((item["literal"], item["reemplazo"]))
    ordered = sorted((item for item in rules if item[0]), key=lambda pair: len(pair[0]), reverse=True)
    return ordered


def sanitize_text(text: str, config: dict) -> str:
    sanitized = text
    for _, pattern, replacement in _regex_rules(config):
        sanitized = pattern.sub(replacement, sanitized)
    for literal, replacement in _literal_rules(config):
        sanitized = sanitized.replace(literal, replacement)
    sanitized = FILE_URI_PATTERN.sub("[ruta_local_redactada]", sanitized)
    sanitized = WINDOWS_PATH_PATTERN.sub("[ruta_local_redactada]", sanitized)
    sanitized = re.sub(r"EVT-\d{4,}", "[evento_interno]", sanitized)
    sanitized = re.sub(r"EVT-\*", "[evento_interno]", sanitized)
    sanitized = re.sub(r"VAL-STEP-[A-Za-z0-9_-]+", "[validacion_humana_interna]", sanitized)
    sanitized = re.sub(r"VAL-STEP-\*", "[validacion_humana_interna]", sanitized)
    sanitized = re.sub(r"sha256:[0-9a-fA-F]{8,64}", "sha256:[redactado]", sanitized)
    sanitized = re.sub(r'"(?:transcript_sha256|quoted_text_hash)"\s*:\s*"[0-9a-fA-F]{32,64}"', '"hash":"[redactado]"', sanitized)
    sanitized = re.sub(r'"screenshot_hashes"\s*:\s*\[[^\]]*\]', '"screenshot_hashes":["[redactado]"]', sanitized)
    sanitized = re.sub(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "[fecha_hora_redactada]", sanitized)
    sanitized = re.sub(r'"content_hash"\s*:\s*"[0-9a-fA-F]{16,}"', '"content_hash":"[redactado]"', sanitized)
    sanitized = re.sub(r'"prev_event_hash"\s*:\s*"[0-9a-fA-FA-FINICIO]{6,}"', '"prev_event_hash":"[redactado]"', sanitized)
    sanitized = CURP_PATTERN.sub("[curp_redactada]", sanitized)
    return sanitized


def _iter_artifact_outputs(config: dict) -> list[tuple[Path, str]]:
    outputs: list[tuple[Path, str]] = []
    excluded_prefixes = tuple(config.get("sanitizacion", {}).get("excluir_prefijos", []))
    for artifact in config["artefactos"]:
        source = ROOT / artifact["source"]
        target = Path(artifact["target"])
        if source.is_file():
            outputs.append((source, target.as_posix()))
            continue
        if not source.is_dir():
            continue
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            rel_source = path.relative_to(ROOT).as_posix()
            if any(rel_source.startswith(prefix) for prefix in excluded_prefixes):
                continue
            outputs.append((path, (target / path.relative_to(source)).as_posix()))
    return outputs


def expected_publication_outputs(config: dict | None = None) -> set[str]:
    publication = load_publication_config() if config is None else config
    expected = {_relative_output_path(publication, rel_path) for _, rel_path in _iter_artifact_outputs(publication)}
    expected.add(publication["salida"]["manifest"])
    expected.add(_relative_output_path(publication, "index.md"))
    return expected


def build_publication_index(config: dict, manifest_payload: dict) -> str:
    lines = [
        "# Bundle público sanitizado",
        "",
        config["proposito"],
        "",
        f"- **Generado:** `{manifest_payload['generated_at']}`",
        f"- **Estado:** `{manifest_payload['status']}`",
        f"- **Fingerprint del bundle:** `{manifest_payload['bundle_fingerprint']}`",
        f"- **Aviso:** {config['politica']['aviso_no_editar']}",
        "",
        "## Superficies",
        "",
        "- **Privada:** canon, ledger, matriz, bitácoras, backlog y auditoría completa.",
        "- **Pública:** derivado sanitizado para lectura humana, divulgación y evaluación externa.",
        "- **IA:** apoyo opcional; la operación del bundle público no depende de IA.",
        "",
        "## Rutas de navegación pública",
        "",
        "- Entrada general: `README_publico.md`.",
        "- Mapa del sistema y ruta base: `wiki/index.md`.",
        "- Propósito, módulos y flujos: `wiki/sistema.md`.",
        "- Reglas y límites: `wiki/gobernanza.md`.",
        "- Términos, IDs y convenciones: `wiki/terminologia.md`.",
        "- Exploración visual: `dashboard/index.html` y `wiki_html/index.html`.",
        "",
        "## Cómo rastrear hacia el origen canónico",
        "",
        "- Cada página pública proviene de una página wiki derivada de la base privada.",
        "- La wiki declara sus fuentes canónicas y el bundle conserva esa semántica con sanitización aplicada.",
        "- Si necesitas reconstruir o auditar, usa el par `wiki/index.md` + `manifest_publico.json` y compáralo con la wiki interna generada.",
        "- La capa pública explica el origen, pero no expone ledger privado, transcripciones ni canon sensible.",
        "",
        "## Artefactos incluidos",
        "",
    ]
    for item in manifest_payload["artifacts"]:
        lines.append(f"- `{item['output']}` ← `{item['source']}`")
    lines.extend(
        [
            "",
            "## Reglas aplicadas",
            "",
        ]
    )
    for item in manifest_payload["applied_rules"]:
        lines.append(f"- {item}")
    lines.extend(
        [
            "",
            "## Qué revisar siempre",
            "",
            "- `README_publico.md`",
            "- `dashboard/index.html`",
            "- `wiki/index.md`",
            "- `manifest_publico.json`",
            "",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def _render_manifest(
    config: dict,
    artifacts: list[dict[str, str]],
    generated_at: str,
    *,
    bundle_fingerprint: str,
) -> dict:
    rules = [item["nombre"] for item in config.get("sanitizacion", {}).get("redacciones_regex", [])]
    literal_rules = config.get("sanitizacion", {}).get("redacciones_literales", [])
    rules.extend(f"literal_rule_{index + 1}" for index, _ in enumerate(literal_rules))
    rules.extend(
        [
            "file_uri_redaction",
            "absolute_windows_path_redaction",
            "val_step_redaction",
            "sha256_redaction",
            "private_canon_redaction",
            "agent_identity_redaction",
        ]
    )
    return {
        "generated_at": generated_at,
        "status": "ok",
        "scope": "publico_sanitizado",
        "bundle_fingerprint": bundle_fingerprint,
        "notice": config["politica"]["aviso_no_editar"],
        "artifacts": artifacts,
        "applied_rules": rules,
    }


def _read_output_payload(path: Path, config: dict) -> bytes:
    if _is_text_file(path):
        return sanitize_text(path.read_text(encoding="utf-8"), config).encode("utf-8")
    return path.read_bytes()


def _bundle_fingerprint(payloads: dict[str, bytes]) -> str:
    digest = hashlib.sha256()
    for rel_path in sorted(payloads):
        digest.update(rel_path.encode("utf-8"))
        digest.update(b"\n")
        digest.update(payloads[rel_path])
        digest.update(b"\n")
    return digest.hexdigest()


def _write_output(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def validate_publication_output(relative_path: str, payload: bytes, config: dict) -> list[str]:
    errors: list[str] = []
    if relative_path.endswith(".json") and relative_path == config["salida"]["manifest"]:
        return errors
    text = payload.decode("utf-8", errors="ignore")
    prohibited_literals = config.get("sanitizacion", {}).get("prohibidos_en_salida", [])
    for token in prohibited_literals:
        if token in text:
            errors.append(f"El artefacto público {relative_path} contiene el patrón prohibido: {token}")
    if FILE_URI_PATTERN.search(text):
        errors.append(f"El artefacto público {relative_path} mantiene una ruta `file:///`.")
    if WINDOWS_PATH_PATTERN.search(text):
        errors.append(f"El artefacto público {relative_path} mantiene una ruta absoluta de Windows.")
    for pattern in GITHUB_PATTERNS:
        if pattern.search(text):
            errors.append(f"El artefacto público {relative_path} contiene un token sensible.")
    if CURP_PATTERN.search(text):
        errors.append(f"El artefacto público {relative_path} contiene una CURP.")
    return errors


def publication_bundle_status(*, build: bool = False, config: dict | None = None) -> dict:
    publication = load_publication_config() if config is None else config
    output_root = _resolved_output_root(publication)
    output_root.mkdir(parents=True, exist_ok=True)
    rendered: dict[str, bytes] = {}
    artifacts: list[dict[str, str]] = []

    for source_path, rel_target in _iter_artifact_outputs(publication):
        payload = _read_output_payload(source_path, publication)
        public_rel = _relative_output_path(publication, rel_target)
        rendered[public_rel] = payload
        artifacts.append(
            {
                "source": source_path.relative_to(ROOT).as_posix(),
                "output": public_rel,
            }
        )

    latest_source_mtime = max(source_path.stat().st_mtime for source_path, _ in _iter_artifact_outputs(publication))
    generated_at = datetime.fromtimestamp(latest_source_mtime).strftime("%Y-%m-%d")
    manifest_payload = _render_manifest(
        publication,
        artifacts,
        generated_at,
        bundle_fingerprint=_bundle_fingerprint(rendered),
    )
    rendered[publication["salida"]["manifest"]] = (json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    index_content = build_publication_index(publication, manifest_payload) + "\n"
    rendered[_relative_output_path(publication, "index.md")] = sanitize_text(index_content, publication).encode("utf-8")

    drift: list[str] = []
    validation_errors: list[str] = []
    for rel_path, payload in rendered.items():
        validation_errors.extend(validate_publication_output(rel_path, payload, publication))
        target = ROOT / rel_path
        if not target.exists() or target.read_bytes() != payload:
            drift.append(rel_path)
            if build:
                _write_output(target, payload)

    existing = {
        path.relative_to(ROOT).as_posix()
        for path in output_root.rglob("*")
        if path.is_file()
    }
    expected = set(rendered)
    unexpected = sorted(existing - expected)
    if unexpected:
        drift.extend(unexpected)
        if build:
            for rel_path in unexpected:
                target = ROOT / rel_path
                resolved = target.resolve()
                if output_root.resolve() not in resolved.parents:
                    raise ValueError(f"Ruta inesperada fuera del bundle público: {rel_path}")
                target.unlink()
                parent = target.parent
                while parent != output_root and parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent

    return {
        "artifacts": artifacts,
        "drift": sorted(set(drift)),
        "errors": validation_errors,
        "generated_at": manifest_payload["generated_at"],
        "output_root": output_root.relative_to(ROOT).as_posix(),
    }


def public_bundle_sha256(relative_path: str) -> str:
    digest = hashlib.sha256()
    with (ROOT / relative_path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
