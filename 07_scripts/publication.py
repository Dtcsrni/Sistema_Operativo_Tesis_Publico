from __future__ import annotations

import hashlib
import json
import posixpath
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
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)")
MARKDOWN_TARGET_PATTERN = re.compile(r"(?P<prefix>\]\()(?P<href>[^)]+)(?P<suffix>\))")
HTML_HREF_PATTERN = re.compile(r'(?P<prefix>\bhref\s*=\s*)(?P<quote>["\'])(?P<href>[^"\']+)(?P=quote)', re.IGNORECASE)
MARKDOWN_PLACEHOLDER_HREF_PATTERN = re.compile(r"(?P<prefix>\]\()(?P<href>\[[^)]+\])(?P<suffix>\))")
ALLOWED_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:", "javascript:")
PRIVATE_PREFIXES = (
    "00_sistema_tesis/evidencia_privada/",
    "config/backups/",
)
PUBLIC_REPO_NAME = "Dtcsrni/Sistema_Operativo_Tesis_Publico"
PUBLIC_EDIT_PLACEHOLDER_PATTERN = re.compile(r"\[[A-Za-z0-9_]+(?:_redactad[ao]|_privad[ao]|_intern[ao])\]")
PUBLIC_HASH_LINE_PATTERN = re.compile(r"^\s*-\s+\*\*Hash(?: de Confirmación Verbal)?:\*\*.*$", re.MULTILINE)
PUBLIC_CONFIRMATION_SOURCE_PATTERN = re.compile(r"^\s*-\s+\*\*Fuente de Verdad de Confirmación:\*\*.*$", re.MULTILINE)
PUBLIC_CHAIN_PATTERN = re.compile(r"^\s*-\s+\*\*Cadena:\*\*.*$", re.MULTILINE)
PUBLIC_SESSION_HEADING_PATTERN = re.compile(r"^### \[{1,2}[^\]]+\]{1,2}\s*$", re.MULTILINE)
PUBLIC_LAST_UPDATE_MARKDOWN = "_Última actualización: `{generated_at}`._"
PUBLIC_LAST_UPDATE_HTML = '<footer class="public-update"><p>Última actualización: <strong>{generated_at}</strong></p></footer>'
PUBLIC_TEXTUAL_REPLACEMENTS = (
    ("[validacion_humana_interna]", "validación humana interna no pública"),
    ("[evento_interno]", "evento interno no público"),
    ("[hash_redactado]", "hash omitido"),
    ("[redactado]", "omitido"),
    ("[fecha_hora_redactada]", "{generated_at}"),
    ("[identidad_agente_privada]", "identidad técnica no publicada por seguridad"),
    ("[ruta_local_redactada]", "ruta local no pública"),
    ("[canon_privado]", "canon no público"),
    ("[matriz_privada]", "matriz interna no pública"),
    ("[ledger_privado]", "ledger interno no público"),
    ("[indice_fuentes_privado]", "índice interno de fuentes no público"),
    ("[bitacora_privada]", "bitácora interna no pública"),
    ("[reportes_privados]", "reportes internos no públicos"),
    ("[firmas_humanas_privadas]", "firmas humanas no publicadas"),
    ("[journal_ia_privado]", "journal de IA no público"),
    ("[evidencia_privada_redactada]", "evidencia privada no publicada"),
    ("[historial_interno_redactado]", "historial interno no público"),
    ("[reporte_interno_redactado]", "reporte interno no publicado"),
    ("[agente_ia_interno]", "agente de apoyo no publicado"),
    ("[proveedor_ia_interno]", "proveedor de IA no publicado"),
    ("[modelo_ia_interno]", "modelo de IA no publicado"),
    ("[runtime_ia_interno]", "runtime de IA no publicado"),
)
PUBLIC_PHRASE_REPLACEMENTS = (
    ("Este repositorio privado gobierna", "Este repositorio documenta"),
    ("Este repositorio privado", "Este repositorio"),
    ("repositorio privado soberano", "repositorio canónico del proyecto"),
    ("repositorio privado", "repositorio canónico"),
    ("bundle sanitizado", "bundle público curado"),
    ("superficie privada", "superficie canónica no pública"),
    ("capa privada", "capa canónica no pública"),
    ("canon privado", "canon no público"),
    ("trazabilidad operativa interna", "trazabilidad operativa"),
)


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
    try:
        identity = load_agent_identity()
    except (FileNotFoundError, KeyError, OSError):
        identity = {
            "agent_role": "",
            "provider": "",
            "model_version": "",
            "runtime_label": "",
        }
    rules = [
        (str(ROOT), "[ruta_local_redactada]"),
        (ROOT.as_posix(), "[ruta_local_redactada]"),
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
    # El bundle publico no debe conservar el literal `sha256:` porque es un token prohibido en salida.
    sanitized = re.sub(r"sha256:[0-9a-fA-F]{8,64}", "[hash_redactado]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"sha256:[^\s`<>()\]\[]+", "[hash_redactado]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"sha256:", "[hash_redactado]:", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'"(?:transcript_sha256|quoted_text_hash)"\s*:\s*"[0-9a-fA-F]{32,64}"', '"hash":"[redactado]"', sanitized)
    sanitized = re.sub(r'"screenshot_hashes"\s*:\s*\[[^\]]*\]', '"screenshot_hashes":["[redactado]"]', sanitized)
    sanitized = re.sub(r"(\d{4}-\d{2}-\d{2}) \d{2}:\d{2}:\d{2}", r"\1", sanitized)
    sanitized = re.sub(r'"content_hash"\s*:\s*"[0-9a-fA-F]{16,}"', '"content_hash":"[redactado]"', sanitized)
    sanitized = re.sub(r'"prev_event_hash"\s*:\s*"[0-9a-fA-FA-FINICIO]{6,}"', '"prev_event_hash":"[redactado]"', sanitized)
    sanitized = CURP_PATTERN.sub("[curp_redactada]", sanitized)
    return sanitized


def _replace_public_tokens(text: str, generated_at: str) -> str:
    rewritten = text
    for old, new in PUBLIC_TEXTUAL_REPLACEMENTS:
        rewritten = rewritten.replace(old, new.format(generated_at=generated_at))
    return rewritten.replace("[curp_redactada]", "CURP no publicada por seguridad")


def _rewrite_public_phrases(text: str) -> str:
    rewritten = text
    for old, new in PUBLIC_PHRASE_REPLACEMENTS:
        rewritten = rewritten.replace(old, new)
    rewritten = rewritten.replace("La capa canónica no pública puede mostrar ejemplos concretos como validación humana interna no pública o evento interno no público.", "La capa canónica no pública utiliza identificadores internos que no se exponen textualmente en esta superficie pública.")
    rewritten = rewritten.replace("##### Desglose de `validación humana interna no pública`", "##### Validación humana interna no pública")
    rewritten = rewritten.replace("### `validación humana interna no pública`", "### Validación humana interna no pública")
    rewritten = rewritten.replace("La superficie **pública** es un bundle público curado, derivado y reproducible para divulgación y evaluación externa.", "La superficie **pública** es un bundle editorialmente curado y reproducible para divulgación y evaluación externa.")
    rewritten = rewritten.replace("La superficie **privada**", "La superficie **canónica no pública**")
    return rewritten


def _rewrite_public_bitacora(text: str) -> str:
    rewritten = PUBLIC_SESSION_HEADING_PATTERN.sub("### Sesión con validación humana interna no pública", text)
    rewritten = PUBLIC_HASH_LINE_PATTERN.sub("- **Hash:** `Hash omitido por seguridad`", rewritten)
    rewritten = PUBLIC_CONFIRMATION_SOURCE_PATTERN.sub("- **Fuente de confirmación:** `Referencia interna no pública`", rewritten)
    rewritten = PUBLIC_CHAIN_PATTERN.sub("- **Cadena de trazabilidad:** `Referencia interna no pública`", rewritten)
    rewritten = rewritten.replace("Hash de Confirmación Verbal", "Confirmación verbal")
    return rewritten


def _rewrite_public_system_tables(text: str) -> str:
    rewritten = text.replace("|agent_identity|identidad técnica no publicada por seguridad|sí|", "|agent_identity|Identidad técnica no publicada por seguridad|sí|")
    rewritten = rewritten.replace(">agent_identity</td><td>identidad técnica no publicada por seguridad</td><td>sí</td>", ">agent_identity</td><td>Identidad técnica no publicada por seguridad</td><td>sí</td>")
    return rewritten


def _append_public_footer(text: str, public_rel: str, generated_at: str) -> str:
    if public_rel.endswith(".json"):
        return text
    if public_rel.endswith(".html"):
        if "Última actualización:" in text:
            return text
        footer = PUBLIC_LAST_UPDATE_HTML.format(generated_at=generated_at)
        return text.replace("</main>", f"    {footer}\n  </main>") if "</main>" in text else text + footer
    if public_rel.endswith(".md"):
        if "Última actualización:" in text:
            return text
        return text.rstrip() + "\n\n" + PUBLIC_LAST_UPDATE_MARKDOWN.format(generated_at=generated_at) + "\n"
    return text


def render_public_text(*, text: str, source_rel: str, public_rel: str, config: dict, generated_at: str) -> str:
    rewritten = sanitize_text(text, config)
    rewritten = rewrite_public_links(rewritten, source_rel=source_rel, public_rel=public_rel, config=config)
    rewritten = _replace_public_tokens(rewritten, generated_at)
    rewritten = _rewrite_public_phrases(rewritten)
    rewritten = _rewrite_public_system_tables(rewritten)
    if "/bitacora." in public_rel or public_rel.endswith("bitacora.md") or public_rel.endswith("bitacora.html"):
        rewritten = _rewrite_public_bitacora(rewritten)
    rewritten = PUBLIC_EDIT_PLACEHOLDER_PATTERN.sub("referencia interna no pública", rewritten)
    rewritten = re.sub(r"`validación humana interna no pública`", "validación humana interna no pública", rewritten)
    rewritten = re.sub(r"`evento interno no público`", "evento interno no público", rewritten)
    rewritten = re.sub(r"`hash omitido`(?::`omitido`)?", "`Hash omitido por seguridad`", rewritten)
    return _append_public_footer(rewritten, public_rel, generated_at)


def build_public_access_note(config: dict, generated_at: str) -> str:
    lines = [
        "# Nota de seguridad y acceso",
        "",
        "Esta referencia existe para mantener navegable la superficie pública sin exponer artefactos privados o no publicados.",
        "",
        f"- **Generado:** `{generated_at}`",
        f"- **Aviso:** {config['politica']['aviso_no_editar']}",
        "",
        "## Qué significa este desvío",
        "",
        "- El enlace original apunta a un archivo interno, sensible o fuera del bundle público.",
        "- La capa pública conserva contexto y trazabilidad general, pero no expone ledger, canon privado, bitácoras privadas ni superficies operativas internas.",
        "",
        "## Qué sí puedes consultar aquí",
        "",
        "- `README_publico.md`",
        "- `MEMORY_publico.md`",
        "- `index.md`",
        "- `manifest_publico.json`",
        "- `wiki/index.md`",
        "- `wiki_html/index.html`",
        "- `dashboard/index.html`",
        "",
    ]
    return "\n".join(lines)


def _is_allowed_scheme(href: str) -> bool:
    return href.startswith(ALLOWED_SCHEMES)


def _normalize_relpath(base_rel: str, href: str) -> str:
    base_dir = Path(base_rel).parent.as_posix()
    return posixpath.normpath(posixpath.join(base_dir, href)).lstrip("./")


def _public_note_relpath() -> str:
    return "06_dashboard/publico/NOTA_SEGURIDAD_Y_ACCESO.md"


def _public_repo_blob_href(target_rel: str) -> str:
    return f"https://github.com/{PUBLIC_REPO_NAME}/blob/main/{target_rel}"


def _public_equivalent_for_source(target_rel: str, config: dict) -> str | None:
    if target_rel == "06_dashboard/generado/wiki_manifest.json":
        return "06_dashboard/publico/manifest_publico.json"
    _, source_to_public, expected_outputs = _artifact_output_cache(config)
    if target_rel in expected_outputs:
        return target_rel
    return source_to_public.get(target_rel)


def _requires_public_note(target_rel: str) -> bool:
    if "[" in target_rel and "]" in target_rel:
        return True
    if target_rel.startswith(PRIVATE_PREFIXES):
        return True
    private_tokens = (
        "[ruta_local_redactada]",
        "[identidad_agente_privada]",
        "[canon_privado]",
        "[matriz_privada]",
        "[ledger_privado]",
        "[indice_fuentes_privado]",
    )
    return any(token in target_rel for token in private_tokens)


def _public_href_for_target(*, source_rel: str, public_rel: str, href: str, config: dict) -> str:
    if not href or href.startswith("#") or _is_allowed_scheme(href):
        return href
    target, separator, anchor = href.partition("#")
    normalized = _normalize_relpath(source_rel, target)
    if _requires_public_note(normalized):
        mapped = _public_note_relpath()
    else:
        mapped = _public_equivalent_for_source(normalized, config)
        if mapped is None:
            return _public_repo_blob_href(normalized)
    relative = Path(posixpath.relpath(mapped, Path(public_rel).parent.as_posix())).as_posix()
    if separator and mapped != _public_note_relpath():
        return f"{relative}#{anchor}"
    return relative


def _extract_markdown_href(raw_href: str) -> str:
    href = raw_href.strip()
    if href.startswith("<") and href.endswith(">"):
        href = href[1:-1].strip()
    if not href:
        return ""
    if " " in href:
        href = href.split(" ", 1)[0].strip()
    return href


def rewrite_public_links(text: str, *, source_rel: str, public_rel: str, config: dict) -> str:
    def replace_markdown(match: re.Match[str]) -> str:
        label, href = match.groups()
        return f"[{label}]({_public_href_for_target(source_rel=source_rel, public_rel=public_rel, href=href.strip(), config=config)})"

    def replace_html(match: re.Match[str]) -> str:
        href = match.group("href").strip()
        rewritten = _public_href_for_target(source_rel=source_rel, public_rel=public_rel, href=href, config=config)
        return f"{match.group('prefix')}{match.group('quote')}{rewritten}{match.group('quote')}"

    rewritten = MARKDOWN_LINK_PATTERN.sub(replace_markdown, text)
    rewritten = MARKDOWN_TARGET_PATTERN.sub(
        lambda match: (
            f"{match.group('prefix')}"
            f"{_public_href_for_target(source_rel=source_rel, public_rel=public_rel, href=_extract_markdown_href(match.group('href')), config=config)}"
            f"{match.group('suffix')}"
        ),
        rewritten,
    )
    rewritten = HTML_HREF_PATTERN.sub(replace_html, rewritten)
    note_rel = Path(posixpath.relpath(_public_note_relpath(), Path(public_rel).parent.as_posix())).as_posix()
    rewritten = MARKDOWN_PLACEHOLDER_HREF_PATTERN.sub(
        lambda match: f"{match.group('prefix')}{note_rel}{match.group('suffix')}",
        rewritten,
    )
    return rewritten


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


def _artifact_output_cache(config: dict) -> tuple[list[tuple[Path, str]], dict[str, str], set[str]]:
    cached_outputs = config.get("__artifact_outputs_cache")
    cached_map = config.get("__artifact_source_to_public_cache")
    cached_expected = config.get("__artifact_expected_outputs_cache")
    if cached_outputs is not None and cached_map is not None and cached_expected is not None:
        return cached_outputs, cached_map, cached_expected

    outputs = _iter_artifact_outputs(config)
    source_to_public = {
        source_path.relative_to(ROOT).as_posix(): _relative_output_path(config, rel_target)
        for source_path, rel_target in outputs
    }
    expected = set(source_to_public.values())
    config["__artifact_outputs_cache"] = outputs
    config["__artifact_source_to_public_cache"] = source_to_public
    config["__artifact_expected_outputs_cache"] = expected
    return outputs, source_to_public, expected


def expected_publication_outputs(config: dict | None = None) -> set[str]:
    publication = load_publication_config() if config is None else config
    _, _, expected = _artifact_output_cache(publication)
    expected = set(expected)
    expected.add(publication["salida"]["manifest"])
    expected.add(_relative_output_path(publication, "index.md"))
    expected.add(_public_note_relpath())
    return expected


def build_publication_index(config: dict, manifest_payload: dict) -> str:
    lines = [
        "# Bundle público editorial",
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
        "- **Pública:** derivado curado editorialmente para lectura humana, divulgación y evaluación externa.",
        "- **IA:** apoyo opcional; la operación del bundle público no depende de IA.",
        "",
        "## Rutas de navegación pública",
        "",
        "- Entrada general: `README_publico.md`.",
        "- Estado operativo breve: `MEMORY_publico.md`.",
        "- Mapa del sistema y ruta base: `wiki/index.md`.",
        "- Propósito, módulos y flujos: `wiki/sistema.md`.",
        "- Reglas y límites: `wiki/gobernanza.md`.",
        "- Términos, IDs y convenciones: `wiki/terminologia.md`.",
        "- Exploración visual: `dashboard/index.html` y `wiki_html/index.html`.",
        "",
        "## Cómo rastrear hacia el origen canónico",
        "",
        "- Cada página pública proviene de una página wiki derivada de la base privada.",
        "- La wiki declara sus fuentes canónicas y el bundle conserva esa semántica con curaduría editorial y resguardo de datos sensibles.",
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
        source_rel = path.relative_to(ROOT).as_posix()
        _, source_to_public, _ = _artifact_output_cache(config)
        public_rel = source_to_public[source_rel]
        generated_at = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        return render_public_text(
            text=path.read_text(encoding="utf-8"),
            source_rel=source_rel,
            public_rel=public_rel,
            config=config,
            generated_at=generated_at,
        ).encode("utf-8")
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
    artifact_outputs, _, _ = _artifact_output_cache(publication)

    for source_path, rel_target in artifact_outputs:
        payload = _read_output_payload(source_path, publication)
        public_rel = _relative_output_path(publication, rel_target)
        rendered[public_rel] = payload
        artifacts.append(
            {
                "source": source_path.relative_to(ROOT).as_posix(),
                "output": public_rel,
            }
        )

    latest_source_mtime = max(source_path.stat().st_mtime for source_path, _ in artifact_outputs)
    generated_at = datetime.fromtimestamp(latest_source_mtime).strftime("%Y-%m-%d")
    manifest_payload = _render_manifest(
        publication,
        artifacts,
        generated_at,
        bundle_fingerprint=_bundle_fingerprint(rendered),
    )
    rendered[publication["salida"]["manifest"]] = (json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    index_rel = _relative_output_path(publication, "index.md")
    index_content = build_publication_index(publication, manifest_payload) + "\n"
    rendered[index_rel] = render_public_text(
        text=index_content,
        source_rel=index_rel,
        public_rel=index_rel,
        config=publication,
        generated_at=generated_at,
    ).encode("utf-8")
    note_rel = _public_note_relpath()
    rendered[note_rel] = render_public_text(
        text=build_public_access_note(publication, generated_at) + "\n",
        source_rel=note_rel,
        public_rel=note_rel,
        config=publication,
        generated_at=generated_at,
    ).encode("utf-8")

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
