"""Gestión de contexto académico enriquecido con PET bundles ingestados."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .epistemic import ClaimAuditRow, extract_fragments_from_content_literal


@dataclass(slots=True)
class PETContextualFragment:
    """Fragmento PET usado como contexto en sesión académica."""

    fragment_id: str
    hash_sha256: str
    authority: str
    certainty: str
    fundamento: str
    text_literal: str
    source_bundle_id: str  # Referencia al bundle que lo originó

    def to_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)


@dataclass(slots=True)
class AcademicSessionContext:
    """Contexto académico enriquecido de una sesión."""

    session_id: str
    packet_id: str
    pet_bundle_ids: list[str]  # IDs de PETs ingestados a consumir
    contextual_fragments: list[PETContextualFragment] = None  # type: ignore
    audited_claims: list[ClaimAuditRow] = None  # type: ignore
    integrated_evidence: str = ""  # Evidencia integrada para la sesión

    def __post_init__(self) -> None:
        if self.contextual_fragments is None:
            self.contextual_fragments = []
        if self.audited_claims is None:
            self.audited_claims = []

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "packet_id": self.packet_id,
            "pet_bundle_ids": self.pet_bundle_ids,
            "contextual_fragments": [f.to_dict() for f in self.contextual_fragments],
            "audited_claims": [c.to_dict() for c in self.audited_claims],
            "integrated_evidence": self.integrated_evidence,
        }


def load_pet_bundles_for_session(
    *,
    store: Any,
    session_id: str,
    packet_id: str,
    pet_bundle_ids: list[str],
) -> AcademicSessionContext:
    """Carga y prepara PET bundles como contexto de sesión académica.

    Args:
        store: OpenClawStore para recuperar bundles
        session_id: ID de la sesión académica
        packet_id: ID del paquete académico
        pet_bundle_ids: IDs de PETs a cargar

    Returns:
        AcademicSessionContext con fragmentos y claims auditados
    """
    context = AcademicSessionContext(
        session_id=session_id,
        packet_id=packet_id,
        pet_bundle_ids=pet_bundle_ids,
    )

    for bundle_id in pet_bundle_ids:
        bundle = store.get_pet_bundle_by_id(bundle_id)
        if bundle is None:
            continue

        # Extraer fragmentos del contenido literal
        fragments = extract_fragments_from_content_literal(bundle.get("content_literal", ""))
        for frag in fragments:
            ctx_fragment = PETContextualFragment(
                fragment_id=frag.get("fragment_id", ""),
                hash_sha256=frag.get("hash_sha256", ""),
                authority=frag.get("authority", ""),
                certainty=frag.get("certainty", ""),
                fundamento=frag.get("fundamento", ""),
                text_literal=frag.get("text_literal", ""),
                source_bundle_id=bundle_id,
            )
            context.contextual_fragments.append(ctx_fragment)

        # Auditar claims dentro del bundle
        from .epistemic import audit_pet_bundle_claims

        audited, _ = audit_pet_bundle_claims(claims_matrix_csv=bundle.get("claims_matrix_csv", ""))
        context.audited_claims.extend(audited)

    # Integrar evidencia para la sesión
    context.integrated_evidence = _render_integrated_evidence(context)

    return context


def _render_integrated_evidence(context: AcademicSessionContext) -> str:
    """Renderiza evidencia integrada a partir del contexto PET para la sesión."""
    lines = ["# Evidencia Integrada de PET Bundles", ""]

    if context.contextual_fragments:
        lines.append("## Fragmentos de Evidencia (Con Hash)")
        lines.append("")
        for frag in context.contextual_fragments:
            lines.append(f"### {frag.fragment_id}")
            lines.append(f"**Hash:** `{frag.hash_sha256}`")
            lines.append(f"**Autoridad:** {frag.authority}")
            lines.append(f"**Certeza:** {frag.certainty}")
            lines.append(f"**Fundamento:** {frag.fundamento}")
            lines.append("")
            lines.append("> " + "\n> ".join(frag.text_literal.split("\n")))
            lines.append("")

    if context.audited_claims:
        lines.append("## Claims Auditados")
        lines.append("")

        approved = [c for c in context.audited_claims if c.estado_auditoria == "aprobado"]
        if approved:
            lines.append("### Aprobados (Factuales con Soporte)")
            for claim in approved:
                lines.append(f"- {claim.afirmacion} [REF:{claim.hash_soporte}]")
            lines.append("")

        pending = [c for c in context.audited_claims if c.estado_auditoria == "pendiente"]
        if pending:
            lines.append("### Pendientes (Hipótesis o No Factuales)")
            for claim in pending:
                lines.append(f"- **Hipótesis:** {claim.afirmacion}")
            lines.append("")

        blocked = [c for c in context.audited_claims if c.estado_auditoria == "bloqueado"]
        if blocked:
            lines.append("### Bloqueados (Requieren Validación)")
            for claim in blocked:
                lines.append(f"- ⚠️ {claim.afirmacion}")
                if claim.observaciones:
                    lines.append(f"  - Razón: {claim.observaciones}")
            lines.append("")

    return "\n".join(lines)


def enrich_session_prompt_with_pet_context(
    *,
    original_prompt: str,
    context: AcademicSessionContext,
    inject_position: str = "prefix",
) -> str:
    """Enriquece un prompt de sesión con contexto de PETs ingestados.

    Args:
        original_prompt: Prompt original de la sesión
        context: Contexto académico con PET bundles
        inject_position: 'prefix' o 'suffix' para dónde inyectar el contexto

    Returns:
        Prompt enriquecido con evidencia integrada
    """
    if not context.contextual_fragments and not context.audited_claims:
        return original_prompt

    evidence_section = (
        f"--- CONTEXTO ACADÉMICO ENRIQUECIDO ---\n{context.integrated_evidence}\n--- FIN CONTEXTO ---\n\n"
    )

    if inject_position == "prefix":
        return evidence_section + original_prompt
    else:
        return original_prompt + f"\n\n{evidence_section}"
