from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "runtime" / "openclaw"

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from openclaw_local.epistemic import (  # noqa: E402
    audit_claim,
    sha256_dict,
    validate_pet_bundle_integrity,
    audit_pet_bundle_claims,
    ingest_pet_bundle,
    extract_fragments_from_content_literal,
)


def test_validate_pet_bundle_integrity() -> None:
    """Valida que la integridad SHA-256 de un PET se verifica correctamente."""
    content_literal = "FRAGMENTO: F001\nHASH_SHA256: abc123\n\nFIN_FRAGMENTO"
    claims_csv = "claim_id,afirmacion,tipo_afirmacion\nC001,Test,hecho_verificado"
    decisions_md = "# Decisiones\n- D001 | test | aprobada"
    metadata = {"source": "test"}

    payload = {
        "content_literal": content_literal.strip(),
        "claims_matrix_csv": claims_csv.strip(),
        "decisions_log_md": decisions_md.strip(),
        "metadata": metadata,
    }
    expected_hash = sha256_dict(payload)

    is_valid, error = validate_pet_bundle_integrity(
        content_literal=content_literal,
        claims_matrix_csv=claims_csv,
        decisions_log_md=decisions_md,
        metadata=metadata,
        expected_integrity_hash=expected_hash,
    )
    assert is_valid, f"Validación falló: {error}"

    # Probar con hash incorrecto
    is_valid, error = validate_pet_bundle_integrity(
        content_literal=content_literal,
        claims_matrix_csv=claims_csv,
        decisions_log_md=decisions_md,
        metadata=metadata,
        expected_integrity_hash="badbadbad",
    )
    assert not is_valid
    assert "mismatch" in error.lower()


def test_ingest_pet_bundle() -> None:
    """Valida que un PET bundle puede ingestarse y auditarse."""
    bundle_id = f"PEB-{uuid4().hex[:12]}"
    package_id = "PKG-EXTERNAL-001"
    source_system = "ResearchLLM-v2"
    source_timestamp = datetime.now(UTC).isoformat()

    # Crear contenido de PET de muestra
    content_literal = """FRAGMENTO: F001
HASH_SHA256: 1234567890abcdef
AUTORIDAD: Paper XYZ
CERTEZA: Alta
FUNDAMENTO: doi:10.1234/test
TEXTO_LITERAL:
La auditoría epistémica valida evidencia.
FIN_FRAGMENTO"""

    claims_csv = """claim_id,afirmacion,tipo_afirmacion,hash_soporte,fuente,autoridad,certeza
C001,La auditoría valida evidencia,hecho_verificado,1234567890abcdef,Paper XYZ,externo,Alta
C002,Esto puede ser hipótesis,hipotesis,,Paper XYZ,externo,Media"""

    decisions_md = """# Decisiones de investigación
- D001 | Usar auditoría epistémica | aprobada | hash_1234"""

    metadata = {"researcher": "test@example.com", "domain": "tesis"}

    # Calcular integrity hash
    payload = {
        "content_literal": content_literal.strip(),
        "claims_matrix_csv": claims_csv.strip(),
        "decisions_log_md": decisions_md.strip(),
        "metadata": metadata,
    }
    integrity_hash = sha256_dict(payload)

    # Ingestar bundle
    record, errors = ingest_pet_bundle(
        bundle_id=bundle_id,
        package_id=package_id,
        source_system=source_system,
        source_timestamp=source_timestamp,
        content_literal=content_literal,
        claims_matrix_csv=claims_csv,
        decisions_log_md=decisions_md,
        metadata=metadata,
        integrity_hash=integrity_hash,
    )

    assert record.status == "validated"
    assert len(errors) == 0, f"Errores durante ingesta: {errors}"
    assert record.claims_count == 2
    assert record.fragments_count == 1


def test_audit_pet_bundle_claims() -> None:
    """Valida la auditoría de claims dentro de un PET."""
    claims_csv = """claim_id,afirmacion,tipo_afirmacion,hash_soporte,fuente,autoridad,certeza
C001,Claim con soporte,hecho_verificado,hash123,Paper,ext,Alta
C002,Claim sin soporte,hecho_verificado,,Paper,ext,Media
C003,Hipótesis,hipotesis,,Paper,ext,Baja"""

    claims, errors = audit_pet_bundle_claims(claims_matrix_csv=claims_csv)

    assert len(claims) == 3
    assert len(errors) == 0

    # Verificar auditoría
    c1 = claims[0]
    assert c1.claim_id == "C001"
    assert c1.estado_auditoria == "aprobado"

    c2 = claims[1]
    assert c2.claim_id == "C002"
    assert c2.estado_auditoria == "bloqueado"

    c3 = claims[2]
    assert c3.claim_id == "C003"
    assert c3.estado_auditoria == "pendiente"


def test_extract_fragments_from_content_literal() -> None:
    """Valida extracción de fragmentos desde contenido literal."""
    content = """FRAGMENTO: F001
HASH_SHA256: hash001
AUTORIDAD: Paper1
CERTEZA: Alta
FUNDAMENTO: doi:10.1111/test1
TEXTO_LITERAL:
Texto del fragmento 1.
FIN_FRAGMENTO

FRAGMENTO: F002
HASH_SHA256: hash002
AUTORIDAD: Paper2
CERTEZA: Media
FUNDAMENTO: doi:10.2222/test2
TEXTO_LITERAL:
Texto del fragmento 2
con múltiples líneas.
FIN_FRAGMENTO"""

    fragments = extract_fragments_from_content_literal(content)

    assert len(fragments) == 2
    assert fragments[0]["fragment_id"] == "F001"
    assert fragments[0]["hash_sha256"] == "hash001"
    assert "Texto del fragmento 1." in fragments[0]["text_literal"]

    assert fragments[1]["fragment_id"] == "F002"
    assert fragments[1]["hash_sha256"] == "hash002"


def test_academic_packet_references_ingested_pet() -> None:
    """Valida que AcademicWorkPacket referencia PETs ingestados."""
    from openclaw_local.engine import build_academic_packet  # noqa: E402
    from openclaw_local.contracts import TaskEnvelope, ClaimRecord, LiteratureRecord  # noqa: E402

    task = TaskEnvelope(
        task_id="T001",
        title="Prueba con PET ingestado",
        objective="Usar contexto de PET externo",
        domain="research",
        target_paths=["output.md"],
        extra_context={"academic_mode": "estado_del_arte"},
    )

    claim = ClaimRecord(
        claim_id="C001",
        claim_text="Claim del análisis local.",
        classification="hipotesis",
        source_refs=[],
        confidence="Media",
        verification_status="pendiente",
        impact_on_thesis="Media",
    )

    lit = LiteratureRecord(
        record_id="LIT001",
        tema="Auditoría",
        pregunta="¿Cómo auditar?",
        fuente="Paper",
        anio=2025,
        doi="10.1234/test",
        nivel_evidencia="Primaria",
        hallazgos_clave=["Hallazgo 1"],
        contradicciones=["Hay contradicción"],
        relacion_con_hipotesis="Directa",
        estado_verificacion="verificado",
    )

    # Build con PETs ingestados
    pet_ids = ["PEB-001", "PEB-002"]
    packet = build_academic_packet(
        task=task,
        question="¿Cómo funciona?",
        scope="Sistema",
        sources=["s1"],
        claims=[claim],
        literature_records=[lit],
        traceability_links=["link1"],
        ingested_pet_bundle_ids=pet_ids,
    )

    assert packet.ingested_pet_bundle_ids == pet_ids
    assert len(packet.ingested_pet_bundle_ids) == 2


def test_storage_ingest_and_retrieve_pet_bundle() -> None:
    """Valida que storage persiste y recupera PETs ingestados."""
    from openclaw_local.storage import OpenClawStore  # noqa: E402

    db_path = Path(tempfile.gettempdir()) / f"test_ingest_pet_{uuid4().hex[:8]}.db"

    bundle_id = f"PEB-{uuid4().hex[:12]}"
    package_id = "PKG-TEST"
    source_system = "TestSystem"

    content_literal = "FRAGMENTO: F001\nHASH: x\nFIN_FRAGMENTO"
    claims_csv = "claim_id,afirmacion,tipo_afirmacion\nC1,Test,hip"
    decisions_md = "# Decisions"
    metadata = {"test": True}

    payload = {
        "content_literal": content_literal,
        "claims_matrix_csv": claims_csv,
        "decisions_log_md": decisions_md,
        "metadata": metadata,
    }
    integrity_hash = sha256_dict(payload)

    store = OpenClawStore(db_path)

    # Ingestar
    store.ingest_pet_bundle(
        bundle_id=bundle_id,
        package_id=package_id,
        source_system=source_system,
        source_timestamp=datetime.now(UTC).isoformat(),
        content_literal=content_literal,
        claims_matrix_csv=claims_csv,
        decisions_log_md=decisions_md,
        metadata=metadata,
        integrity_hash=integrity_hash,
        status="validated",
        claims_count=1,
        fragments_count=1,
    )

    # Recuperar
    retrieved = store.get_pet_bundle_by_id(bundle_id)
    assert retrieved is not None
    assert retrieved["bundle_id"] == bundle_id
    assert retrieved["source_system"] == source_system
    assert retrieved["status"] == "validated"

    # Listar
    bundles = store.list_ingested_pet_bundles(source_system=source_system)
    assert len(bundles) >= 1
    assert any(b["bundle_id"] == bundle_id for b in bundles)

    db_path.unlink()


def sha256_dict(data: dict) -> str:
    """Helper for tests."""
    import hashlib
    normalized = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
