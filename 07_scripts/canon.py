from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from common import ROOT, apply_agent_identity_placeholders, file_sha256, load_agent_identity, load_yaml_json, now_stamp
from data_io import canonical_json, dump_jsonl_path, dump_structured_path, load_jsonl_path, load_structured_path


CANON_DIR = ROOT / "00_sistema_tesis" / "canon"
EVENTS_PATH = CANON_DIR / "events.jsonl"
STATE_PATH = CANON_DIR / "state.json"

LEDGER_PATH = ROOT / "00_sistema_tesis" / "bitacora" / "log_conversaciones_ia.md"
MATRIX_PATH = ROOT / "00_sistema_tesis" / "bitacora" / "matriz_trazabilidad.md"
BITACORA_DIR = ROOT / "00_sistema_tesis" / "bitacora"
IA_JOURNAL_PATH = ROOT / "00_sistema_tesis" / "ia_journal.json"
SIGN_OFFS_PATH = ROOT / "00_sistema_tesis" / "config" / "sign_offs.json"
BITACORA_TEMPLATE_PATH = ROOT / "00_sistema_tesis" / "plantillas" / "bitacora_template.md"
SOURCE_INDEX_PATH = ROOT / "00_sistema_tesis" / "bitacora" / "indice_fuentes_conversacion.md"
SOURCE_EVIDENCE_DIR = ROOT / "00_sistema_tesis" / "evidencia_privada" / "conversaciones_codex"

STEP_ID_PATTERN = re.compile(r"^VAL-STEP-[A-Za-z0-9_-]+$")
EVENT_ID_PATTERN = re.compile(r"^EVT-(\d+)$")


def ensure_canon_dir() -> None:
    CANON_DIR.mkdir(parents=True, exist_ok=True)


def normalize_path(relative_path: str) -> str:
    return relative_path.replace("\\", "/").strip()


def normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    return normalized


def normalize_verbal_confirmation_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def verbal_confirmation_hash(text: str) -> str:
    normalized = normalize_verbal_confirmation_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def file_sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_evidence_policy() -> dict[str, Any]:
    config = load_yaml_json("00_sistema_tesis/config/ia_gobernanza.yaml")
    section = dict(config.get("evidencia_fuente_conversacion", {}))
    activation = dict(section.get("activacion", {}))
    return {
        "obligatoria_para_val_step_nuevo": bool(section.get("obligatoria_para_val_step_nuevo", True)),
        "desde_step_id": str(activation.get("desde_step_id", "VAL-STEP-501")).strip(),
        "platform": str(section.get("platform", "codex")).strip(),
        "client_surface": str(section.get("client_surface", "vscode_codex")).strip(),
        "capture_method": str(section.get("capture_method", "manual_transcript_plus_screenshot")).strip(),
        "captura_manual_requerida": bool(section.get("captura_manual_requerida", True)),
        "message_role_default": str(section.get("message_role_default", "human")).strip(),
    }


def step_sequence_value(step_id: str) -> int | None:
    match = re.match(r"^VAL-STEP-(\d+)$", step_id.strip())
    return int(match.group(1)) if match else None


def source_evidence_required_for_step(step_id: str) -> bool:
    if not STEP_ID_PATTERN.match(step_id):
        return False
    policy = source_evidence_policy()
    if not policy["obligatoria_para_val_step_nuevo"]:
        return False
    current = step_sequence_value(step_id)
    threshold = step_sequence_value(str(policy["desde_step_id"]))
    if current is None or threshold is None:
        return False
    return current >= threshold


def resolve_human_validation_source_metadata(event: dict[str, Any]) -> dict[str, Any]:
    human_validation = dict(event.get("human_validation", {}))
    source_event_id = str(human_validation.get("source_event_id", "")).strip()
    source_required = source_evidence_required_for_step(str(event.get("event_id", "")))
    return {
        "source_event_id": source_event_id,
        "provenance_status": str(
            human_validation.get("provenance_status")
            or ("corroborated_conversation_source" if source_event_id else "legacy_unverified_source")
        ).strip(),
        "quote_verification_status": str(
            human_validation.get("quote_verification_status")
            or ("verified_against_source" if source_event_id else "internal_canon_only")
        ).strip(),
        "source_capture_required": bool(human_validation.get("source_capture_required", source_required)),
    }


def events_by_id(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(event["event_id"]): event for event in events}


def sanitize_session_id_for_path(session_id: str) -> str:
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", session_id.strip())
    return candidate or "sin_sesion"


def ensure_source_evidence_dir() -> None:
    SOURCE_EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


def _extract_dialog_line(content_text: str, actor_marker: str) -> str:
    for raw_line in reversed(normalize_text(content_text).splitlines()):
        stripped = raw_line.strip()
        if actor_marker == "Agente:" and stripped.startswith("Agente:"):
            match = re.match(r"^Agente:\s*(.*)$", stripped)
            if match:
                return match.group(1).strip()
        if actor_marker == "Tesista" and stripped.startswith("Tesista"):
            match = re.match(r"^Tesista.*?\):\s*(.*)$", stripped)
            if match:
                return match.group(1).strip()
    return ""


def derive_verbal_confirmation_data(content_text: str) -> dict[str, str]:
    question_text = _extract_dialog_line(content_text, "Agente:")
    confirmation_text = _extract_dialog_line(content_text, "Tesista")
    confirmation_kind = "enunciado_humano"

    if not question_text:
        question_text = "Instrucción humana directa registrada sin pregunta previa del agente."
        confirmation_kind = "instruccion_directa"
    if confirmation_text.endswith("?"):
        confirmation_kind = "pregunta_humana_directa"
    if confirmation_text.lower().startswith(("si", "sí", "\"si", "\"sí")):
        confirmation_kind = "respuesta_afirmativa"
    if not confirmation_text:
        confirmation_kind = "sin_confirmacion_explicita"

    return {
        "question_text": question_text,
        "confirmation_text": confirmation_text,
        "confirmation_kind": confirmation_kind,
        "confirmation_source_type": "derivada_de_content_text",
    }


def resolve_human_validation_evidence(event: dict[str, Any]) -> dict[str, str]:
    payload = dict(event.get("payload", {}))
    human_validation = dict(event.get("human_validation", {}))
    content_text = str(payload.get("content_text", ""))
    derived = derive_verbal_confirmation_data(content_text)
    question_text = str(
        human_validation.get("question_text")
        or payload.get("question_text")
        or derived["question_text"]
    ).strip()
    confirmation_text = str(
        human_validation.get("confirmation_text")
        or payload.get("confirmation_text")
        or derived["confirmation_text"]
    ).strip()
    confirmation_kind = str(
        human_validation.get("confirmation_kind")
        or payload.get("confirmation_kind")
        or derived["confirmation_kind"]
    ).strip()
    source_type = str(
        human_validation.get("confirmation_source_type")
        or payload.get("confirmation_source_type")
        or derived["confirmation_source_type"]
    ).strip()
    source_of_truth = str(
        human_validation.get("confirmation_source_of_truth")
        or payload.get("confirmation_source_of_truth")
        or f"00_sistema_tesis/canon/events.jsonl :: {event['event_id']} :: human_validation.confirmation_text"
    ).strip()
    confirmation_hash = str(
        human_validation.get("confirmation_text_hash")
        or payload.get("confirmation_text_hash")
        or (verbal_confirmation_hash(confirmation_text) if confirmation_text else "")
    ).strip()
    return {
        "question_text": question_text,
        "confirmation_text": confirmation_text,
        "confirmation_kind": confirmation_kind,
        "confirmation_source_type": source_type,
        "confirmation_source_of_truth": source_of_truth,
        "confirmation_text_hash": confirmation_hash,
    }


def event_payload_hash(event: dict[str, Any]) -> str:
    payload = {key: value for key, value in event.items() if key not in {"prev_event_hash", "content_hash"}}
    rendered = canonical_json(payload)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def reseal_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    previous_hash = "INICIO"
    sealed: list[dict[str, Any]] = []
    for original in events:
        event = dict(original)
        event["prev_event_hash"] = previous_hash
        event["content_hash"] = event_payload_hash(event)
        previous_hash = event["content_hash"]
        sealed.append(event)
    return sealed


def load_events() -> list[dict[str, Any]]:
    return load_jsonl_path(EVENTS_PATH)


def projection_paths(events: list[dict[str, Any]] | None = None) -> list[str]:
    items = load_events() if events is None else events
    projected = {
        "00_sistema_tesis/bitacora/log_conversaciones_ia.md",
        "00_sistema_tesis/bitacora/matriz_trazabilidad.md",
        "00_sistema_tesis/bitacora/indice_fuentes_conversacion.md",
        "00_sistema_tesis/ia_journal.json",
        "00_sistema_tesis/config/sign_offs.json",
        "00_sistema_tesis/canon/state.json",
    }
    for event in items:
        if event.get("event_type") == "session_recorded":
            path = normalize_path(str(event.get("payload", {}).get("path", "")))
            if path:
                projected.add(path)
    return sorted(projected)


def build_state(events: list[dict[str, Any]]) -> dict[str, Any]:
    latest_step = next((event["event_id"] for event in reversed(events) if str(event["event_id"]).startswith("VAL-STEP-")), "")
    generated_at = str(events[-1]["occurred_at"]) if events else now_stamp()
    human_events = [event for event in events if event["event_type"] == "human_validation"]
    source_events = [event for event in events if event["event_type"] == "conversation_source_registered"]
    source_linked = sum(1 for event in human_events if resolve_human_validation_source_metadata(event)["source_event_id"])
    required_steps = sum(1 for event in human_events if source_evidence_required_for_step(str(event["event_id"])))
    return {
        "generated_at": generated_at,
        "canon": {
            "event_count": len(events),
            "latest_event_id": events[-1]["event_id"] if events else "",
            "latest_step_id": latest_step,
            "projection_paths": projection_paths(events),
        },
        "counts_by_type": {
            event_type: sum(1 for event in events if event["event_type"] == event_type)
            for event_type in sorted({str(event["event_type"]) for event in events})
        },
        "source_evidence": {
            "enforcement_from_step_id": source_evidence_policy()["desde_step_id"],
            "registered_sources": len(source_events),
            "human_validations_with_source": source_linked,
            "human_validations_requiring_source": required_steps,
            "legacy_without_source": len(human_events) - source_linked,
        },
    }


def save_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ensure_canon_dir()
    sealed = reseal_events(events)
    dump_jsonl_path(EVENTS_PATH, sealed)
    dump_structured_path(STATE_PATH, build_state(sealed))
    return sealed


def next_evt_id(events: list[dict[str, Any]]) -> str:
    max_value = 0
    for event in events:
        match = EVENT_ID_PATTERN.match(str(event.get("event_id", "")))
        if match:
            max_value = max(max_value, int(match.group(1)))
    return f"EVT-{max_value + 1:04d}"


def conversation_source_event(source_event_id: str, events: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    items = load_events() if events is None else events
    event = events_by_id(items).get(source_event_id)
    if not event or event.get("event_type") != "conversation_source_registered":
        return None
    return event


def human_validation_event(step_id: str, events: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    items = load_events() if events is None else events
    event = events_by_id(items).get(step_id)
    if not event or event.get("event_type") != "human_validation":
        return None
    return event


def verify_conversation_source_for_step(
    step_id: str,
    events: list[dict[str, Any]] | None = None,
    *,
    require_local: bool = True,
) -> dict[str, Any]:
    items = load_events() if events is None else events
    step_event = human_validation_event(step_id, items)
    result: dict[str, Any] = {
        "step_id": step_id,
        "source_event_id": "",
        "session_id": "",
        "provenance_status": "",
        "quote_verification_status": "",
        "repo_status": "missing",
        "local_status": "skipped",
        "repo_errors": [],
        "local_errors": [],
    }
    if not step_event:
        result["repo_errors"].append(f"No existe el Step ID {step_id} en el canon.")
        result["local_status"] = "not_applicable"
        return result

    source_meta = resolve_human_validation_source_metadata(step_event)
    evidence = resolve_human_validation_evidence(step_event)
    result["source_event_id"] = source_meta["source_event_id"]
    result["provenance_status"] = str(source_meta["provenance_status"])
    result["quote_verification_status"] = str(source_meta["quote_verification_status"])

    if not source_meta["source_event_id"]:
        if source_evidence_required_for_step(step_id):
            result["repo_errors"].append(f"{step_id} requiere source_event_id y no lo declara.")
            result["repo_status"] = "fail"
            result["local_status"] = "fail" if require_local else "skipped"
        else:
            result["repo_status"] = "legacy_unverified_source"
            result["local_status"] = "legacy_unverified_source"
        return result

    source_event = conversation_source_event(source_meta["source_event_id"], items)
    if not source_event:
        result["repo_errors"].append(
            f"{step_id} referencia {source_meta['source_event_id']}, pero no existe un evento conversation_source_registered."
        )
        result["repo_status"] = "fail"
        result["local_status"] = "fail" if require_local else "skipped"
        return result

    payload = dict(source_event.get("payload", {}))
    result["session_id"] = str(payload.get("session_id", source_event.get("session_id", ""))).strip()
    quoted_text = str(payload.get("quoted_text", "")).strip()
    quoted_text_hash = str(payload.get("quoted_text_hash", "")).strip()
    if quoted_text != evidence["confirmation_text"]:
        result["repo_errors"].append(
            f"{step_id} no coincide con la cita registrada en {source_meta['source_event_id']}."
        )
    expected_hash = verbal_confirmation_hash(evidence["confirmation_text"]) if evidence["confirmation_text"] else ""
    if quoted_text_hash and quoted_text_hash != expected_hash:
        result["repo_errors"].append(
            f"{step_id} tiene hash de cita distinto al registrado en {source_meta['source_event_id']}."
        )

    transcript_rel = normalize_path(str(payload.get("transcript_path", "")))
    if not transcript_rel:
        result["repo_errors"].append(f"{source_meta['source_event_id']} no declara transcript_path.")
    transcript_sha = str(payload.get("transcript_sha256", "")).strip()
    if transcript_rel and not transcript_sha:
        result["repo_errors"].append(f"{source_meta['source_event_id']} no declara transcript_sha256.")

    screenshot_paths = [normalize_path(str(item)) for item in payload.get("screenshot_paths", []) if str(item).strip()]
    screenshot_hashes = [str(item).strip() for item in payload.get("screenshot_hashes", []) if str(item).strip()]
    if screenshot_paths and len(screenshot_paths) != len(screenshot_hashes):
        result["repo_errors"].append(f"{source_meta['source_event_id']} tiene capturas y hashes desalineados.")

    result["repo_status"] = "ok" if not result["repo_errors"] else "fail"
    if not require_local:
        result["local_status"] = "skipped"
        return result

    transcript_path = ROOT / transcript_rel if transcript_rel else None
    if not transcript_path or not transcript_path.exists():
        result["local_errors"].append(f"Falta la transcripción local para {source_meta['source_event_id']}.")
    else:
        current_hash = file_sha256_path(transcript_path)
        if transcript_sha and current_hash != transcript_sha:
            result["local_errors"].append(f"La transcripción local no coincide con el hash de {source_meta['source_event_id']}.")
        transcript_text = transcript_path.read_text(encoding="utf-8")
        if quoted_text and quoted_text not in transcript_text:
            result["local_errors"].append(f"La cita exacta no aparece en la transcripción local de {source_meta['source_event_id']}.")

    for rel_path, expected in zip(screenshot_paths, screenshot_hashes):
        screenshot_path = ROOT / rel_path
        if not screenshot_path.exists():
            result["local_errors"].append(f"Falta la captura local {rel_path}.")
            continue
        if expected and file_sha256_path(screenshot_path) != expected:
            result["local_errors"].append(f"La captura {rel_path} no coincide con el hash registrado.")

    result["local_status"] = "ok" if not result["local_errors"] else "fail"
    return result


def source_evidence_status(
    events: list[dict[str, Any]] | None = None,
    *,
    require_local: bool = True,
) -> dict[str, Any]:
    items = load_events() if events is None else events
    validations = [event for event in items if event["event_type"] == "human_validation"]
    results = [
        verify_conversation_source_for_step(str(event["event_id"]), items, require_local=require_local)
        for event in validations
    ]
    repo_failures = [result for result in results if result["repo_status"] == "fail"]
    local_failures = [result for result in results if result["local_status"] == "fail"]
    return {
        "results": results,
        "repo_status": "ok" if not repo_failures else "fail",
        "local_status": "ok" if not local_failures else "fail",
        "repo_failures": repo_failures,
        "local_failures": local_failures,
        "required_steps": [
            str(event["event_id"]) for event in validations if source_evidence_required_for_step(str(event["event_id"]))
        ],
    }


def create_conversation_source_scaffold(session_id: str, *, overwrite: bool = False) -> dict[str, str]:
    policy = source_evidence_policy()
    ensure_source_evidence_dir()
    session_dir = SOURCE_EVIDENCE_DIR / sanitize_session_id_for_path(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = session_dir / "transcripcion.md"
    metadata_draft_path = session_dir / "metadata_draft.json"

    if overwrite or not transcript_path.exists():
        transcript_path.write_text(
            normalize_text(
                "# Transcripción de corroboración\n\n"
                f"- session_id: {session_id}\n"
                "- pegar_aqui: confirmación verbal exacta\n\n"
                "## Conversación\n\n"
                "[Pegar transcripción completa aquí]\n"
            ),
            encoding="utf-8",
        )

    draft_payload = {
        "session_id": session_id,
        "captured_at": now_stamp(),
        "platform": policy["platform"],
        "client_surface": policy["client_surface"],
        "message_role": policy["message_role_default"],
        "capture_method": policy["capture_method"],
        "transcript_path": normalize_path(str(transcript_path.relative_to(ROOT))),
        "screenshots_expected": [],
        "quoted_text": "",
        "message_locator": "",
    }
    if overwrite or not metadata_draft_path.exists():
        metadata_draft_path.write_text(json.dumps(draft_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    return {
        "session_dir": normalize_path(str(session_dir.relative_to(ROOT))),
        "transcript_path": normalize_path(str(transcript_path.relative_to(ROOT))),
        "metadata_draft_path": normalize_path(str(metadata_draft_path.relative_to(ROOT))),
    }


def validate_events(events: list[dict[str, Any]] | None = None) -> list[str]:
    items = load_events() if events is None else events
    errors: list[str] = []
    required_fields = {
        "event_id",
        "event_type",
        "occurred_at",
        "actor",
        "session_id",
        "risk_level",
        "links",
        "payload",
        "affected_files",
        "human_validation",
        "prev_event_hash",
        "content_hash",
    }
    previous_hash = "INICIO"
    seen_ids: set[str] = set()
    indexed = events_by_id(items)
    for index, event in enumerate(items, start=1):
        missing = required_fields - set(event.keys())
        if missing:
            errors.append(f"Evento {index} incompleto. Faltan campos: {', '.join(sorted(missing))}")
            continue
        event_id = str(event["event_id"])
        if event_id in seen_ids:
            errors.append(f"ID duplicado en canon: {event_id}")
        seen_ids.add(event_id)
        if event.get("prev_event_hash") != previous_hash:
            errors.append(f"Cadena rota en {event_id}: prev_event_hash esperado {previous_hash}")
        recalculated = event_payload_hash(event)
        if event.get("content_hash") != recalculated:
            errors.append(f"Hash inválido en {event_id}")
        previous_hash = str(event.get("content_hash", previous_hash))
        if event_id.startswith("VAL-STEP-") and not STEP_ID_PATTERN.match(event_id):
            errors.append(f"Step ID inválido en canon: {event_id}")
        if event.get("event_type") == "conversation_source_registered":
            payload = dict(event.get("payload", {}))
            required_payload = {
                "platform",
                "client_surface",
                "session_id",
                "captured_at",
                "transcript_path",
                "transcript_sha256",
                "screenshot_paths",
                "screenshot_hashes",
                "quoted_text",
                "quoted_text_hash",
                "message_role",
                "message_locator",
                "capture_method",
            }
            missing_payload = [key for key in sorted(required_payload) if key not in payload]
            if missing_payload:
                errors.append(f"Fuente de conversación incompleta en {event_id}: {', '.join(missing_payload)}")
            quoted_text = str(payload.get("quoted_text", "")).strip()
            quoted_text_hash = str(payload.get("quoted_text_hash", "")).strip()
            if not quoted_text:
                errors.append(f"Fuente de conversación sin quoted_text en {event_id}")
            if quoted_text and quoted_text_hash != verbal_confirmation_hash(quoted_text):
                errors.append(f"Hash de quoted_text inválido en {event_id}")
            screenshot_paths = payload.get("screenshot_paths", [])
            screenshot_hashes = payload.get("screenshot_hashes", [])
            if not isinstance(screenshot_paths, list):
                errors.append(f"Fuente de conversación con screenshot_paths inválido en {event_id}")
            if not isinstance(screenshot_hashes, list) or len(screenshot_hashes) != len(screenshot_paths):
                errors.append(f"Fuente de conversación con hashes de captura inconsistentes en {event_id}")
        if event.get("event_type") == "human_validation":
            human_validation = dict(event.get("human_validation", {}))
            if str(human_validation.get("step_id", "")) != event_id:
                errors.append(f"Validación humana sin step_id consistente en {event_id}")
            if not str(human_validation.get("status", "")).strip():
                errors.append(f"Validación humana sin estado en {event_id}")
            if not str(human_validation.get("validated_at", "")).strip():
                errors.append(f"Validación humana sin fecha en {event_id}")
            if not str(human_validation.get("mode", "")).strip():
                errors.append(f"Validación humana sin modo en {event_id}")
            evidence = resolve_human_validation_evidence(event)
            if not evidence["confirmation_text"]:
                errors.append(f"Validación humana sin texto de confirmación verbal en {event_id}")
            if not evidence["question_text"]:
                errors.append(f"Validación humana sin pregunta crítica o disparador en {event_id}")
            if evidence["confirmation_text"]:
                expected_confirmation_hash = verbal_confirmation_hash(evidence["confirmation_text"])
                if evidence["confirmation_text_hash"] != expected_confirmation_hash:
                    errors.append(f"Hash de confirmación verbal inválido en {event_id}")
            if not evidence["confirmation_source_of_truth"]:
                errors.append(f"Validación humana sin fuente de verdad de confirmación en {event_id}")
            source_meta = resolve_human_validation_source_metadata(event)
            if source_evidence_required_for_step(event_id):
                required_fields = ("source_event_id", "provenance_status", "quote_verification_status", "source_capture_required")
                for field in required_fields:
                    if field not in human_validation:
                        errors.append(f"Validación humana {event_id} no declara {field}.")
                if not source_meta["source_event_id"]:
                    errors.append(f"Validación humana {event_id} requiere source_event_id.")
            if source_meta["source_event_id"]:
                source_event = indexed.get(source_meta["source_event_id"])
                if not source_event or source_event.get("event_type") != "conversation_source_registered":
                    errors.append(
                        f"Validación humana {event_id} referencia {source_meta['source_event_id']} sin fuente de conversación válida."
                    )
                else:
                    payload = dict(source_event.get("payload", {}))
                    quoted_text = str(payload.get("quoted_text", "")).strip()
                    quoted_text_hash = str(payload.get("quoted_text_hash", "")).strip()
                    if quoted_text != evidence["confirmation_text"]:
                        errors.append(f"La cita de {event_id} no coincide con la fuente {source_meta['source_event_id']}.")
                    if quoted_text_hash and quoted_text_hash != evidence["confirmation_text_hash"]:
                        errors.append(
                            f"El hash de cita de {event_id} no coincide con la fuente {source_meta['source_event_id']}."
                        )
    return errors


def _parse_legacy_ledger_blocks() -> list[dict[str, Any]]:
    content = _read_legacy_ledger_source()
    if not content:
        return []
    entries: list[dict[str, Any]] = []
    pattern = re.compile(
        r"## \[(VAL-STEP-[A-Za-z0-9_-]+)\](.*?)(?=\n---+\n\n## \[VAL-STEP-[A-Za-z0-9_-]+\]|\n\*\*Navegación:\*\*|\Z)",
        re.DOTALL,
    )
    for match in pattern.finditer(content):
        step_id = match.group(1)
        block = match.group(0)
        content_match = re.search(r"-\s+\*\*Contenido:\*\*\s*<<<[\n\r]*(.*?)[\n\r]*>>>", block, re.DOTALL)
        matrix_ref = re.search(r"-\s+\*\*Vínculo:\*\*\s+(.*)", block)
        provider = re.search(r"-\s+\*\*Proveedor:\*\*\s+(.*)", block)
        model = re.search(r"-\s+\*\*Modelo/Versión:\*\*\s+(.*)", block)
        date = re.search(r"-\s+\*\*Fecha:\*\*\s+(\d{4}-\d{2}-\d{2})", block)
        audit_level = re.search(r"-\s+\*\*Audit Level:\*\*\s+(.*)", block)
        clean_content = content_match.group(1).replace("\r\n", "\n").strip() if content_match else ""
        session_id_match = re.search(r"ID de Sesión:\s*(.*)", clean_content)
        entries.append(
            {
                "step_id": step_id,
                "provider": provider.group(1).strip() if provider else "",
                "model_version": model.group(1).strip() if model else "",
                "date": date.group(1).strip() if date else "",
                "linked_reference": matrix_ref.group(1).strip() if matrix_ref else "[DEC-0014]",
                "audit_level": audit_level.group(1).strip() if audit_level else "MEDIO",
                "content_text": clean_content,
                "session_id": session_id_match.group(1).strip() if session_id_match else "",
            }
        )
    return entries


def _read_legacy_ledger_source() -> str:
    if LEDGER_PATH.exists():
        content = LEDGER_PATH.read_text(encoding="utf-8")
        if _ledger_content_has_payload(content):
            return content

    git_content = _read_file_from_git_head("00_sistema_tesis/bitacora/log_conversaciones_ia.md")
    if git_content and _ledger_content_has_payload(git_content):
        return git_content

    backups = sorted(
        (ROOT / "config" / "backups").glob("00_sistema_tesis_bitacora_log_conversaciones_ia.md*.bak"),
        reverse=True,
    )
    for backup in backups:
        backup_content = backup.read_text(encoding="utf-8")
        if _ledger_content_has_payload(backup_content):
            return backup_content
    return ""


def _read_file_from_git_head(rel_path: str) -> str:
    result = subprocess.run(
        ["git", "show", f"HEAD:{rel_path}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode == 0:
        return result.stdout
    return ""


def _ledger_content_has_payload(content: str) -> bool:
    blocks = re.findall(r"-\s+\*\*Contenido:\*\*\s*<<<[\n\r]*(.*?)[\n\r]*>>>", content, re.DOTALL)
    return any(block.strip() for block in blocks)


def _parse_legacy_matrix() -> dict[str, dict[str, str]]:
    if not MATRIX_PATH.exists():
        return {}
    rows: dict[str, dict[str, str]] = {}
    pattern = re.compile(
        r"^\|\s*(?P<fecha>[^|]+)\|\s*\[(?P<step>VAL-STEP-[A-Za-z0-9_-]+)\]\s*\|\s*(?P<referencia>[^|]+)\|\s*(?P<summary>[^|]+)\|\s*(?P<risk>[^|]+)\|\s*(?P<ethics>[^|]+)\|\s*(?P<estado>[^|]+)\|"
    )
    for raw_line in MATRIX_PATH.read_text(encoding="utf-8").splitlines():
        match = pattern.match(raw_line.strip())
        if not match:
            continue
        rows[match.group("step")] = {
            "date": match.group("fecha").strip(),
            "reference": match.group("referencia").strip(),
            "summary": match.group("summary").strip(),
            "risk_level": match.group("risk").strip(),
            "ethical_alignment": match.group("ethics").strip(),
            "state_label": match.group("estado").strip(),
        }
    return rows


def _extract_session_date_from_filename(path: Path) -> str:
    match = re.match(r"(\d{4}-\d{2}-\d{2})_", path.name)
    return match.group(1) if match else datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")


def import_legacy_events(force: bool = False) -> list[dict[str, Any]]:
    if EVENTS_PATH.exists() and not force:
        return load_events()

    matrix_rows = _parse_legacy_matrix()
    events: list[dict[str, Any]] = []

    for ledger_entry in _parse_legacy_ledger_blocks():
        step_id = ledger_entry["step_id"]
        matrix_entry = matrix_rows.get(step_id, {})
        evidence = derive_verbal_confirmation_data(ledger_entry["content_text"])
        events.append(
            {
                "event_id": step_id,
                "event_type": "human_validation",
                "occurred_at": f"{ledger_entry['date']} 00:00:00" if ledger_entry["date"] else now_stamp(),
                "actor": {
                    "type": "ai",
                    "id": ledger_entry["provider"] or "legacy-ai",
                    "display_name": ledger_entry["provider"] or "legacy-ai",
                    "provider": ledger_entry["provider"],
                    "model_version": ledger_entry["model_version"],
                },
                "session_id": ledger_entry["session_id"],
                "risk_level": matrix_entry.get("risk_level", ledger_entry["audit_level"]),
                "links": {
                    "reference": matrix_entry.get("reference", ledger_entry["linked_reference"]),
                    "matrix_row": matrix_entry,
                },
                "payload": {
                    "provider": ledger_entry["provider"],
                    "model_version": ledger_entry["model_version"],
                    "date": ledger_entry["date"],
                    "linked_reference": matrix_entry.get("reference", ledger_entry["linked_reference"]),
                    "audit_level": ledger_entry["audit_level"],
                    "content_text": ledger_entry["content_text"],
                    "matrix_row": matrix_entry,
                },
                "affected_files": [
                    "00_sistema_tesis/bitacora/log_conversaciones_ia.md",
                    "00_sistema_tesis/bitacora/matriz_trazabilidad.md",
                ],
                "human_validation": {
                    "required": True,
                    "step_id": step_id,
                    "status": "validated",
                    "validated_at": ledger_entry["date"],
                    "mode": "Confirmación Verbal",
                    "question_text": evidence["question_text"],
                    "confirmation_text": evidence["confirmation_text"],
                    "confirmation_kind": evidence["confirmation_kind"],
                    "confirmation_source_type": "derivada_de_content_text",
                    "confirmation_source_of_truth": f"00_sistema_tesis/canon/events.jsonl :: {step_id} :: human_validation.confirmation_text",
                    "confirmation_text_hash": verbal_confirmation_hash(evidence["confirmation_text"]) if evidence["confirmation_text"] else "",
                    "provenance_status": "legacy_unverified_source",
                    "quote_verification_status": "internal_canon_only",
                    "source_capture_required": False,
                },
                "prev_event_hash": "",
                "content_hash": "",
            }
        )

    bitacora_files = sorted(
        path
        for path in BITACORA_DIR.glob("*.md")
        if path.name not in {"log_conversaciones_ia.md", "matriz_trazabilidad.md"}
    )
    for bitacora_path in bitacora_files:
        content = normalize_text(bitacora_path.read_text(encoding="utf-8"))
        events.append(
            {
                "event_id": next_evt_id(events),
                "event_type": "session_recorded",
                "occurred_at": f"{_extract_session_date_from_filename(bitacora_path)} 00:00:00",
                "actor": {"type": "human", "id": "tesista", "display_name": "tesista"},
                "session_id": bitacora_path.stem,
                "risk_level": "MEDIO",
                "links": {},
                "payload": {"path": normalize_path(str(bitacora_path.relative_to(ROOT))), "content": content},
                "affected_files": [normalize_path(str(bitacora_path.relative_to(ROOT)))],
                "human_validation": {"required": False},
                "prev_event_hash": "",
                "content_hash": "",
            }
        )

    journal = load_structured_path(IA_JOURNAL_PATH) if IA_JOURNAL_PATH.exists() else {"journal": []}
    for record in journal.get("journal", []):
        events.append(
            {
                "event_id": next_evt_id(events),
                "event_type": "agent_activity",
                "occurred_at": str(record.get("timestamp", now_stamp())),
                "actor": {"type": "ai", "id": str(record.get("agente", "legacy-agent")), "display_name": str(record.get("agente", "legacy-agent"))},
                "session_id": str(record.get("session_id", "")),
                "risk_level": "MEDIO",
                "links": {},
                "payload": {"record": record},
                "affected_files": [item["archivo"] for item in record.get("detalles_archivos", []) if isinstance(item, dict) and item.get("archivo")],
                "human_validation": {"required": False},
                "prev_event_hash": "",
                "content_hash": "",
            }
        )

    signoffs = load_structured_path(SIGN_OFFS_PATH) if SIGN_OFFS_PATH.exists() else {"sign_offs": []}
    for record in signoffs.get("sign_offs", []):
        events.append(
            {
                "event_id": next_evt_id(events),
                "event_type": "artifact_signed",
                "occurred_at": str(record.get("fecha", now_stamp())),
                "actor": {"type": "human", "id": "tesista", "display_name": "tesista"},
                "session_id": "",
                "risk_level": "ALTO",
                "links": {},
                "payload": {"record": record},
                "affected_files": [str(record.get("archivo", ""))],
                "human_validation": {"required": True, "status": "signed", "validated_at": str(record.get("fecha", ""))},
                "prev_event_hash": "",
                "content_hash": "",
            }
        )

    sealed = save_events(events)
    materialize_events(sealed)
    return sealed


def render_ledger(events: list[dict[str, Any]]) -> str:
    lines = [
        "<!-- SISTEMA_TESIS:PROTEGIDO -->",
        "# Ledger de Conversaciones IA (Inmutable y Enlazado)",
        "",
        "Este archivo es el **Libro Mayor** de las validaciones humanas. El contenido exacto está entre `<<<` y `>>>`. ",
        "Cada bloque forma parte de una **Cadena de Evidencia Vinculada**.",
        "",
    ]
    human_events = [event for event in events if event["event_type"] == "human_validation"]
    human_ids = [str(event["event_id"]) for event in human_events]
    for index, event in enumerate(human_events):
        payload = event["payload"]
        evidence = resolve_human_validation_evidence(event)
        source_meta = resolve_human_validation_source_metadata(event)
        step_id = str(event["event_id"])
        content_text = str(payload.get("content_text", "")).strip()
        previous_id = human_ids[index - 1] if index > 0 else "INICIO"
        next_id = human_ids[index + 1] if index < len(human_ids) - 1 else "FIN"
        block_hash = hashlib.sha256(content_text.encode("utf-8")).hexdigest()
        lines.extend(
            [
                "---",
                "",
                f"## [{step_id}]",
                f"- **Proveedor:** {payload.get('provider', '')}",
                f"- **Modelo/Versión:** {payload.get('model_version', '')}",
                f"- **Fecha:** {payload.get('date', str(event['occurred_at'])[:10])}",
                f"- **Vínculo:** {payload.get('linked_reference', '[DEC-0014]')}",
                f"- **Hash:** `sha256:{block_hash}`",
                f"- **Audit Level:** {payload.get('audit_level', event.get('risk_level', 'MEDIO'))}",
                f"- **Pregunta Crítica / Disparador:** {evidence['question_text']}",
                f"- **Confirmación Verbal (Texto Exacto):** {evidence['confirmation_text'] or '[No conservada]'}",
                f"- **Hash de Confirmación Verbal:** `sha256:{evidence['confirmation_text_hash']}`" if evidence["confirmation_text_hash"] else "- **Hash de Confirmación Verbal:** `sha256:N/A`",
                f"- **Fuente de Verdad de Confirmación:** `{evidence['confirmation_source_of_truth']}`",
                f"- **Tipo de Confirmación:** {evidence['confirmation_kind']} | Fuente: {evidence['confirmation_source_type']}",
                f"- **Proveniencia de la Confirmación:** {source_meta['provenance_status']} | Verificación: {source_meta['quote_verification_status']}",
                f"- **Fuente de Conversación Registrada:** `{source_meta['source_event_id'] or 'N/A'}` | Captura requerida: {source_meta['source_capture_required']}",
                f"- **Cadena:** [Anterior: {previous_id}] | [Siguiente: {next_id}]",
                "- **Contenido:**",
                "<<<",
                f"{content_text}>>>",
                "",
            ]
        )
    lines.extend(
        [
            "**Navegación:**",
            "- [Volver a la Matriz](matriz_trazabilidad.md)",
            "",
        ]
    )
    return "\n".join(lines)


def render_matrix(events: list[dict[str, Any]]) -> str:
    lines = [
        "<!-- SISTEMA_TESIS:PROTEGIDO -->",
        "# Matriz de Trazabilidad Maestra (Índice de Integridad)",
        "",
        "Este archivo es el índice central de todas las validaciones de soberanía humana y trazabilidad técnica en el sistema operativo de la tesis.",
        "",
        "## Estado General de Integridad",
        "- [x] Firma GPG de Infraestructura",
        "- [x] Verificación de Ledger (Libro Mayor)",
        "- [x] Consistencia de Matriz",
        "- [/] Cadena de Bitácoras (En proceso de mejora)",
        "",
        "## Registro de Validaciones de Soberanía (Handshake)",
        "",
        "| Fecha | Step ID | Referencia | Intención / Resumen del Cambio | Nivel de Riesgo | Alineación Ética | Estado | Evidencia (Ledger) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    human_events = [event for event in events if event["event_type"] == "human_validation"]
    for event in human_events:
        step_id = str(event["event_id"])
        matrix_row = dict(event.get("payload", {}).get("matrix_row", {}))
        lines.append(
            "| {date} | [{step}] | {reference} | {summary} | {risk} | {ethics} | {state} | [Log](log_conversaciones_ia.md#{anchor}) |".format(
                date=matrix_row.get("date", str(event["occurred_at"])[:10]),
                step=step_id,
                reference=matrix_row.get("reference", event.get("links", {}).get("reference", "[DEC-0014]")),
                summary=matrix_row.get("summary", "Cambio registrado en canon"),
                risk=matrix_row.get("risk_level", event.get("risk_level", "MEDIO")),
                ethics=matrix_row.get("ethical_alignment", "Responsabilidad (ISO 42001)"),
                state=matrix_row.get("state_label", "[x] Validado"),
                anchor=step_id.lower(),
            )
        )
    lines.extend(
        [
            "",
            "---",
            "**Navegación:**",
            "- [Volver al Inicio](../../README.md)",
            "- [Consultar Libro Mayor](log_conversaciones_ia.md)",
            "- [Auditoría del Sistema](../../06_dashboard/generado/reporte_consistencia.md)",
            "",
        ]
    )
    for event in human_events:
        step_id = str(event["event_id"])
        lines.append(f"[{step_id}]: log_conversaciones_ia.md#{step_id.lower()}")
    return "\n".join(lines) + "\n"


def render_conversation_source_index(events: list[dict[str, Any]]) -> str:
    lines = [
        "<!-- SISTEMA_TESIS:PROTEGIDO -->",
        "# Índice Privado de Fuentes de Conversación",
        "",
        "Este índice enlaza cada `VAL-STEP-*` con su estatus de evidencia fuente de conversación.",
        "La evidencia cruda vive en `00_sistema_tesis/evidencia_privada/conversaciones_codex/` y no forma parte de la superficie pública.",
        "",
        f"- **Enforcement desde:** `{source_evidence_policy()['desde_step_id']}`",
        f"- **Directorio privado:** `{normalize_path(str(SOURCE_EVIDENCE_DIR.relative_to(ROOT)))}`",
        "",
        "| Step ID | Proveniencia | Verificación de cita | Source EVT | Sesión | Estado repo |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]
    for event in [item for item in events if item["event_type"] == "human_validation"]:
        step_id = str(event["event_id"])
        status = verify_conversation_source_for_step(step_id, events, require_local=False)
        lines.append(
            "| {step} | {prov} | {quote} | {source} | {session} | {repo} |".format(
                step=step_id,
                prov=status["provenance_status"] or "n/a",
                quote=status["quote_verification_status"] or "n/a",
                source=status["source_event_id"] or "N/A",
                session=status["session_id"] or "N/A",
                repo=status["repo_status"],
            )
        )
        for error in status["repo_errors"]:
            lines.append(f"|  |  |  |  |  | repo_error: {error} |")
    lines.extend(
        [
            "",
            "**Navegación:**",
            "- [Volver al Ledger](log_conversaciones_ia.md)",
            "- [Volver a la Matriz](matriz_trazabilidad.md)",
            "",
            "[LID]: file:///v:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/bitacora/log_conversaciones_ia.md",
            "[GOV]: file:///v:/Sistema_Operativo_Tesis_Posgrado/00_sistema_tesis/config/ia_gobernanza.yaml",
            "[AUD]: file:///v:/Sistema_Operativo_Tesis_Posgrado/07_scripts/build_all.py",
            "",
        ]
    )
    return "\n".join(lines)


def render_journal(events: list[dict[str, Any]]) -> dict[str, Any]:
    records = [dict(event["payload"]["record"]) for event in events if event["event_type"] == "agent_activity"]
    return {"journal": records}


def render_signoffs(events: list[dict[str, Any]]) -> dict[str, Any]:
    latest_by_path: dict[str, dict[str, Any]] = {}
    for event in events:
        if event["event_type"] != "artifact_signed":
            continue
        record = dict(event["payload"]["record"])
        path = str(record.get("archivo", "")).strip()
        if path:
            latest_by_path[path] = record
    ordered = [latest_by_path[key] for key in sorted(latest_by_path)]
    return {"sign_offs": ordered}


def render_session_files(events: list[dict[str, Any]]) -> dict[str, str]:
    sessions: dict[str, str] = {}
    for event in events:
        if event["event_type"] != "session_recorded":
            continue
        path = normalize_path(str(event["payload"].get("path", "")))
        content = normalize_text(str(event["payload"].get("content", "")))
        if path:
            sessions[path] = content
    return sessions


def projected_payloads(events: list[dict[str, Any]]) -> dict[str, str]:
    outputs: dict[str, str] = {
        "00_sistema_tesis/bitacora/log_conversaciones_ia.md": render_ledger(events),
        "00_sistema_tesis/bitacora/matriz_trazabilidad.md": render_matrix(events),
        "00_sistema_tesis/bitacora/indice_fuentes_conversacion.md": render_conversation_source_index(events),
        "00_sistema_tesis/ia_journal.json": json.dumps(render_journal(events), ensure_ascii=False, indent=2) + "\n",
        "00_sistema_tesis/config/sign_offs.json": json.dumps(render_signoffs(events), ensure_ascii=False, indent=2) + "\n",
        "00_sistema_tesis/canon/state.json": json.dumps(build_state(events), ensure_ascii=False, indent=2) + "\n",
    }
    outputs.update(render_session_files(events))
    return outputs


def materialize_events(events: list[dict[str, Any]] | None = None, *, check: bool = False) -> list[str]:
    items = load_events() if events is None else events
    outputs = projected_payloads(items)
    drift: list[str] = []
    for rel_path, content in outputs.items():
        target = ROOT / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        normalized = normalize_text(content) if target.suffix.lower() == ".md" else content
        if not target.exists() or target.read_text(encoding="utf-8") != normalized:
            drift.append(rel_path)
            if not check:
                target.write_text(normalized, encoding="utf-8")
    return drift


def step_ids_exist(step_ids: list[str], events: list[dict[str, Any]] | None = None) -> bool:
    items = load_events() if events is None else events
    existing = {str(event["event_id"]) for event in items if str(event["event_id"]).startswith("VAL-STEP-")}
    return all(step_id in existing for step_id in step_ids)


def append_event(event: dict[str, Any], *, materialize: bool = True) -> dict[str, Any]:
    events = load_events()
    prepared = dict(event)
    if not prepared.get("event_id"):
        prepared["event_id"] = next_evt_id(events)
    if not prepared.get("occurred_at"):
        prepared["occurred_at"] = now_stamp()
    prepared.setdefault("actor", {"type": "system", "id": "tesis-cli", "display_name": "tesis-cli"})
    prepared.setdefault("session_id", "")
    prepared.setdefault("risk_level", "MEDIO")
    prepared.setdefault("links", {})
    prepared.setdefault("payload", {})
    prepared.setdefault("affected_files", [])
    prepared.setdefault("human_validation", {"required": False})
    prepared["affected_files"] = [normalize_path(path) for path in prepared["affected_files"]]
    events.append(prepared)
    sealed = save_events(events)
    if materialize:
        materialize_events(sealed)
    return sealed[-1]


def append_conversation_source(
    *,
    session_id: str,
    transcript_source_path: str,
    screenshot_source_paths: list[str] | None,
    quoted_text: str,
    captured_at: str = "",
    message_role: str = "",
    message_locator: str = "",
    capture_method: str = "",
) -> dict[str, Any]:
    if not quoted_text.strip():
        raise ValueError("La cita exacta (`quoted_text`) es obligatoria.")
    transcript_input = Path(transcript_source_path)
    if not transcript_input.exists():
        raise FileNotFoundError(f"No existe la transcripción fuente: {transcript_source_path}")
    normalized_screenshots = screenshot_source_paths or []
    if source_evidence_policy()["captura_manual_requerida"] and not normalized_screenshots:
        raise ValueError("La política activa requiere al menos una captura para registrar evidencia fuente.")

    policy = source_evidence_policy()
    ensure_source_evidence_dir()
    session_dir = SOURCE_EVIDENCE_DIR / sanitize_session_id_for_path(session_id)
    session_dir.mkdir(parents=True, exist_ok=True)
    resolved_captured_at = captured_at or now_stamp()

    transcript_dest = session_dir / "transcripcion.md"
    transcript_dest.write_text(normalize_text(transcript_input.read_text(encoding="utf-8")), encoding="utf-8")

    screenshot_rel_paths: list[str] = []
    screenshot_hashes: list[str] = []
    for index, raw_path in enumerate(normalized_screenshots, start=1):
        source_path = Path(raw_path)
        if not source_path.exists():
            raise FileNotFoundError(f"No existe la captura fuente: {raw_path}")
        suffix = source_path.suffix.lower() or ".bin"
        destination = session_dir / f"captura_{index:03d}{suffix}"
        shutil.copy2(source_path, destination)
        screenshot_rel_paths.append(normalize_path(str(destination.relative_to(ROOT))))
        screenshot_hashes.append(file_sha256_path(destination))

    transcript_rel = normalize_path(str(transcript_dest.relative_to(ROOT)))
    transcript_hash = file_sha256_path(transcript_dest)
    event = append_event(
        {
            "event_type": "conversation_source_registered",
            "occurred_at": resolved_captured_at,
            "actor": {"type": "system", "id": "tesis-cli", "display_name": "tesis-cli"},
            "session_id": session_id,
            "risk_level": "ALTO",
            "links": {"reference": "[DEC-0014]", "policy": "[DEC-0018]"},
            "payload": {
                "platform": policy["platform"],
                "client_surface": policy["client_surface"],
                "session_id": session_id,
                "captured_at": resolved_captured_at,
                "transcript_path": transcript_rel,
                "transcript_sha256": transcript_hash,
                "screenshot_paths": screenshot_rel_paths,
                "screenshot_hashes": screenshot_hashes,
                "quoted_text": normalize_verbal_confirmation_text(quoted_text),
                "quoted_text_hash": verbal_confirmation_hash(quoted_text),
                "message_role": message_role or policy["message_role_default"],
                "message_locator": message_locator,
                "capture_method": capture_method or policy["capture_method"],
            },
            "affected_files": [
                "00_sistema_tesis/canon/events.jsonl",
                "00_sistema_tesis/bitacora/indice_fuentes_conversacion.md",
                transcript_rel,
                *screenshot_rel_paths,
                normalize_path(str((session_dir / "metadata.json").relative_to(ROOT))),
            ],
            "human_validation": {"required": False},
        }
    )

    metadata_path = session_dir / "metadata.json"
    metadata = {
        "event_id": event["event_id"],
        "session_id": session_id,
        "captured_at": resolved_captured_at,
        "transcript_path": transcript_rel,
        "transcript_sha256": transcript_hash,
        "screenshot_paths": screenshot_rel_paths,
        "screenshot_hashes": screenshot_hashes,
        "quoted_text": normalize_verbal_confirmation_text(quoted_text),
        "quoted_text_hash": verbal_confirmation_hash(quoted_text),
        "message_role": message_role or policy["message_role_default"],
        "message_locator": message_locator,
        "capture_method": capture_method or policy["capture_method"],
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return event


def append_human_validation(
    *,
    step_id: str,
    audit_level: str,
    content_text: str,
    linked_reference: str = "[DEC-0014]",
    matrix_summary: str = "Cambio registrado en canon",
    matrix_reference: str | None = None,
    ethical_alignment: str = "Responsabilidad (ISO 42001)",
    state_label: str = "[x] Validado",
    session_id: str = "",
    provider: str | None = None,
    model_version: str | None = None,
    confirmation_question: str = "",
    confirmation_text: str = "",
    confirmation_kind: str = "",
    source_event_id: str = "",
    provenance_status: str = "",
    quote_verification_status: str = "",
    source_capture_required: bool | None = None,
) -> dict[str, Any]:
    if not STEP_ID_PATTERN.match(step_id):
        raise ValueError(f"Step ID inválido: {step_id}")
    identity = load_agent_identity()
    record_provider = provider or identity["provider"]
    record_model = model_version or identity["model_version"]
    derived_evidence = derive_verbal_confirmation_data(content_text.strip())
    resolved_question = (confirmation_question or derived_evidence["question_text"]).strip()
    resolved_confirmation = (confirmation_text or derived_evidence["confirmation_text"]).strip()
    resolved_kind = (confirmation_kind or derived_evidence["confirmation_kind"]).strip()
    source_required = source_evidence_required_for_step(step_id)
    resolved_source_event_id = source_event_id.strip()
    resolved_provenance = (provenance_status or ("corroborated_conversation_source" if resolved_source_event_id else "legacy_unverified_source")).strip()
    resolved_quote_status = (quote_verification_status or ("verified_against_source" if resolved_source_event_id else "internal_canon_only")).strip()
    resolved_source_capture_required = source_required if source_capture_required is None else bool(source_capture_required)
    if source_required and not resolved_source_event_id:
        raise ValueError(f"{step_id} requiere source_event_id a partir de {source_evidence_policy()['desde_step_id']}.")
    if resolved_source_event_id:
        source_event = conversation_source_event(resolved_source_event_id)
        if not source_event:
            raise ValueError(f"La fuente de conversación {resolved_source_event_id} no existe en el canon.")
        source_payload = dict(source_event.get("payload", {}))
        source_quote = str(source_payload.get("quoted_text", "")).strip()
        if source_quote and source_quote != resolved_confirmation:
            raise ValueError(f"La cita exacta de {step_id} no coincide con la fuente {resolved_source_event_id}.")
    matrix_row = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "reference": matrix_reference or linked_reference,
        "summary": matrix_summary,
        "risk_level": audit_level,
        "ethical_alignment": ethical_alignment,
        "state_label": state_label,
    }
    event = {
        "event_id": step_id,
        "event_type": "human_validation",
        "occurred_at": now_stamp(),
        "actor": {
            "type": "ai",
            "id": record_provider,
            "display_name": record_provider,
            "provider": record_provider,
            "model_version": record_model,
        },
        "session_id": session_id,
        "risk_level": audit_level,
        "links": {"reference": linked_reference, "matrix_row": matrix_row},
        "payload": {
            "provider": record_provider,
            "model_version": record_model,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "linked_reference": linked_reference,
            "audit_level": audit_level,
            "content_text": content_text.strip(),
            "matrix_row": matrix_row,
        },
        "affected_files": [
            "00_sistema_tesis/canon/events.jsonl",
            "00_sistema_tesis/bitacora/log_conversaciones_ia.md",
            "00_sistema_tesis/bitacora/matriz_trazabilidad.md",
        ],
        "human_validation": {
            "required": True,
            "step_id": step_id,
            "status": "validated",
            "validated_at": datetime.now().strftime("%Y-%m-%d"),
            "mode": "Confirmación Verbal",
            "question_text": resolved_question,
            "confirmation_text": resolved_confirmation,
            "confirmation_kind": resolved_kind,
            "confirmation_source_type": "campo_canonico_explicito",
            "confirmation_source_of_truth": f"00_sistema_tesis/canon/events.jsonl :: {step_id} :: human_validation.confirmation_text",
            "confirmation_text_hash": verbal_confirmation_hash(resolved_confirmation) if resolved_confirmation else "",
            "source_event_id": resolved_source_event_id,
            "provenance_status": resolved_provenance,
            "quote_verification_status": resolved_quote_status,
            "source_capture_required": resolved_source_capture_required,
        },
    }
    return append_event(event)


def append_artifact_signed(*, rel_path: str, comment: str, session_id: str = "") -> dict[str, Any]:
    record = {
        "archivo": normalize_path(rel_path),
        "hash_verificado": file_sha256(rel_path),
        "fecha": now_stamp(),
        "comentario": comment,
    }
    return append_event(
        {
            "event_type": "artifact_signed",
            "occurred_at": record["fecha"],
            "actor": {"type": "human", "id": "tesista", "display_name": "tesista"},
            "session_id": session_id,
            "risk_level": "ALTO",
            "links": {},
            "payload": {"record": record},
            "affected_files": [record["archivo"], "00_sistema_tesis/config/sign_offs.json"],
            "human_validation": {"required": True, "status": "signed", "validated_at": record["fecha"]},
        }
    )


def append_agent_activity(*, session_id: str, task_summary: str, files_touched: list[str], agent_name: str | None = None) -> dict[str, Any]:
    identity = load_agent_identity()
    file_details = []
    for rel_path in files_touched:
        normalized = normalize_path(rel_path)
        target = ROOT / normalized
        if target.exists() and target.is_file():
            file_details.append({"archivo": normalized, "hash": file_sha256(normalized)})
    record = {
        "timestamp": now_stamp(),
        "session_id": session_id,
        "agente": agent_name or identity["agent_role"],
        "tarea": task_summary,
        "detalles_archivos": file_details,
    }
    return append_event(
        {
            "event_type": "agent_activity",
            "occurred_at": record["timestamp"],
            "actor": {
                "type": "ai",
                "id": identity["agent_role"],
                "display_name": identity["agent_role"],
                "provider": identity["provider"],
                "model_version": identity["model_version"],
            },
            "session_id": session_id,
            "risk_level": "MEDIO",
            "links": {},
            "payload": {"record": record},
            "affected_files": [item["archivo"] for item in file_details] + ["00_sistema_tesis/ia_journal.json"],
            "human_validation": {"required": False},
        }
    )


def create_session_content(session_id: str) -> tuple[str, str]:
    template = apply_agent_identity_placeholders(BITACORA_TEMPLATE_PATH.read_text(encoding="utf-8"))
    today = datetime.now().strftime("%Y-%m-%d")
    existing_paths = {path.name for path in BITACORA_DIR.glob("*.md")}
    filename = f"{today}_bitacora_sesion.md"
    counter = 1
    while filename in existing_paths:
        filename = f"{today}_bitacora_sesion_{counter}.md"
        counter += 1
    path = normalize_path(str((BITACORA_DIR / filename).relative_to(ROOT)))
    content = (
        template.replace("YYYY-MM-DD", today)
        .replace("[ID-SESION-GUID]", session_id)
        .replace("[hash_bitacora_previa_o_INICIO]", "INICIO")
    )
    return path, normalize_text(content)


def append_session_record(*, rel_path: str, content: str, session_id: str) -> dict[str, Any]:
    return append_event(
        {
            "event_type": "session_recorded",
            "occurred_at": now_stamp(),
            "actor": {"type": "human", "id": "tesista", "display_name": "tesista"},
            "session_id": session_id,
            "risk_level": "MEDIO",
            "links": {},
            "payload": {"path": normalize_path(rel_path), "content": normalize_text(content)},
            "affected_files": [normalize_path(rel_path)],
            "human_validation": {"required": False},
        }
    )
