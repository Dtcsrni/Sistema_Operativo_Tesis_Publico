from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import asdict, dataclass
from typing import Any


FACTUAL_TYPES = {"hecho_verificado", "inferencia_razonada"}
NON_FACTUAL_TYPES = {"hipotesis", "propuesta", "afirmacion_no_soportada"}


@dataclass(slots=True)
class ClaimAuditRow:
    claim_id: str
    afirmacion: str
    tipo_afirmacion: str
    hash_soporte: str
    fuente: str
    autoridad: str
    certeza: str
    estado_auditoria: str
    accion_recomendada: str
    riesgo: str
    observaciones: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PETIngestaRecord:
    """Registro de un PET bundle ingestado de un sistema externo."""
    bundle_id: str
    package_id: str
    source_system: str
    source_timestamp: str
    integrity_hash: str
    status: str
    validation_errors: str = ""
    claims_count: int = 0
    fragments_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def sha256_text(text: str) -> str:
    """Calcula SHA-256 de un texto."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_dict(data: dict[str, Any]) -> str:
    """Calcula SHA-256 de un diccionario normalizado."""
    normalized = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def audit_claim(
    *,
    claim_id: str,
    afirmacion: str,
    tipo_afirmacion: str,
    hash_soporte: str = "",
    fuente: str = "",
    autoridad: str = "IA",
    certeza: str = "Baja",
    riesgo: str = "medio",
    observaciones: str = "",
) -> ClaimAuditRow:
    """Audita un claim: verifica que claims factuales tengan soporte."""
    normalized_type = tipo_afirmacion.strip().lower()
    normalized_hash = hash_soporte.strip().lower()

    if normalized_type in FACTUAL_TYPES:
        if normalized_hash:
            estado = "aprobado"
            accion = "emitir"
            riesgo_final = riesgo
        else:
            estado = "bloqueado"
            accion = "requiere_evidencia"
            riesgo_final = "alto"
            observaciones = _append_note(observaciones, "claim factual sin hash de soporte")
    elif normalized_type in NON_FACTUAL_TYPES:
        estado = "pendiente"
        accion = "marcar_como_no_factual"
        riesgo_final = riesgo
        if normalized_type == "afirmacion_no_soportada":
            observaciones = _append_note(observaciones, "claim no soportado; debe eliminarse o reclasificarse")
    else:
        estado = "bloqueado"
        accion = "reclasificar"
        riesgo_final = "alto"
        observaciones = _append_note(observaciones, "tipo de afirmacion no reconocido")

    return ClaimAuditRow(
        claim_id=claim_id,
        afirmacion=afirmacion,
        tipo_afirmacion=normalized_type,
        hash_soporte=normalized_hash,
        fuente=fuente,
        autoridad=autoridad,
        certeza=certeza,
        estado_auditoria=estado,
        accion_recomendada=accion,
        riesgo=riesgo_final,
        observaciones=observaciones,
    )


def validate_pet_bundle_integrity(
    *,
    content_literal: str,
    claims_matrix_csv: str,
    decisions_log_md: str,
    metadata: dict[str, Any],
    expected_integrity_hash: str,
) -> tuple[bool, str]:
    """Valida la integridad SHA-256 de un bundle PET ingestado."""
    computed_payload = {
        "content_literal": content_literal.strip(),
        "claims_matrix_csv": claims_matrix_csv.strip(),
        "decisions_log_md": decisions_log_md.strip(),
        "metadata": metadata,
    }
    computed_hash = sha256_dict(computed_payload)

    if computed_hash.lower() != expected_integrity_hash.lower():
        error = f"Integrity mismatch: expected {expected_integrity_hash}, got {computed_hash}"
        return False, error

    return True, ""


def audit_pet_bundle_claims(
    *,
    claims_matrix_csv: str,
) -> tuple[list[ClaimAuditRow], list[str]]:
    """Audita todos los claims dentro de un bundle PET ingestado."""
    errors = []
    claims = []

    reader = csv.DictReader(io.StringIO(claims_matrix_csv))
    for row_idx, row in enumerate(reader, start=2):
        try:
            claim = audit_claim(
                claim_id=row.get("claim_id", f"C_{row_idx}"),
                afirmacion=row.get("afirmacion", ""),
                tipo_afirmacion=row.get("tipo_afirmacion", "hipotesis"),
                hash_soporte=row.get("hash_soporte", ""),
                fuente=row.get("fuente", ""),
                autoridad=row.get("autoridad", "externo"),
                certeza=row.get("certeza", "media"),
            )
            claims.append(claim)
        except Exception as e:
            errors.append(f"Row {row_idx}: {str(e)}")

    return claims, errors


def ingest_pet_bundle(
    *,
    bundle_id: str,
    package_id: str,
    source_system: str,
    source_timestamp: str,
    content_literal: str,
    claims_matrix_csv: str,
    decisions_log_md: str,
    metadata: dict[str, Any],
    integrity_hash: str,
) -> tuple[PETIngestaRecord, list[str]]:
    """Registra la ingesta de un PET bundle de un sistema externo."""
    errors = []

    is_valid, integrity_error = validate_pet_bundle_integrity(
        content_literal=content_literal,
        claims_matrix_csv=claims_matrix_csv,
        decisions_log_md=decisions_log_md,
        metadata=metadata,
        expected_integrity_hash=integrity_hash,
    )

    if not is_valid:
        errors.append(integrity_error)
        status = "rejected"
    else:
        status = "validated"

    audited_claims, audit_errors = audit_pet_bundle_claims(claims_matrix_csv=claims_matrix_csv)
    errors.extend(audit_errors)

    fragments_count = content_literal.count("FRAGMENTO:")

    record = PETIngestaRecord(
        bundle_id=bundle_id,
        package_id=package_id,
        source_system=source_system,
        source_timestamp=source_timestamp,
        integrity_hash=integrity_hash,
        status=status,
        validation_errors="; ".join(errors) if errors else "",
        claims_count=len(audited_claims),
        fragments_count=fragments_count,
    )

    return record, errors


def extract_fragments_from_content_literal(content_literal: str) -> list[dict[str, str]]:
    """Extrae fragmentos con hash del contenido literal."""
    fragments = []
    current_fragment = None
    in_literal = False
    literal_lines = []

    for line in content_literal.split("\n"):
        if line.startswith("FRAGMENTO:"):
            current_fragment = {"fragment_id": line.split(":", 1)[1].strip()}
        elif line.startswith("HASH_SHA256:") and current_fragment:
            current_fragment["hash_sha256"] = line.split(":", 1)[1].strip()
        elif line.startswith("AUTORIDAD:") and current_fragment:
            current_fragment["authority"] = line.split(":", 1)[1].strip()
        elif line.startswith("CERTEZA:") and current_fragment:
            current_fragment["certainty"] = line.split(":", 1)[1].strip()
        elif line.startswith("FUNDAMENTO:") and current_fragment:
            current_fragment["fundamento"] = line.split(":", 1)[1].strip()
        elif line == "TEXTO_LITERAL:" and current_fragment:
            in_literal = True
            literal_lines = []
        elif line == "FIN_FRAGMENTO" and current_fragment and in_literal:
            current_fragment["text_literal"] = "\n".join(literal_lines).strip()
            fragments.append(current_fragment)
            current_fragment = None
            in_literal = False
            literal_lines = []
        elif in_literal:
            literal_lines.append(line)

    return fragments


def _append_note(current: str, note: str) -> str:
    """Appends a note to a string without duplication."""
    if not current.strip():
        return note
    if note in current:
        return current
    return f"{current}; {note}"
