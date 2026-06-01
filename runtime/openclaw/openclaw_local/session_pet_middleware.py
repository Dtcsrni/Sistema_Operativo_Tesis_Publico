"""Middleware de sesión para enriquecer contexto con PET bundles ingestados."""

from __future__ import annotations

from typing import Any, Callable

from .academic_context import (
    AcademicSessionContext,
    enrich_session_prompt_with_pet_context,
    load_pet_bundles_for_session,
)
from .storage import OpenClawStore


DispatchHandler = Callable[[str, str], dict[str, Any]]


def wrap_dispatcher_with_pet_context(
    original_dispatcher: DispatchHandler,
    *,
    store: OpenClawStore,
    session: dict[str, Any],
) -> DispatchHandler:
    """Crea un dispatcher que enriquece respuestas con contexto de PET bundles.

    Intercepta llamadas al dispatcher original e inyecta evidencia de PETs
    ingestados en el contexto de la sesión si están disponibles.

    Args:
        original_dispatcher: Dispatcher sin enriquecimiento
        store: OpenClawStore para recuperar PET bundles
        session: Diccionario de sesión con session_id, packet_id (si existe)

    Returns:
        Dispatcher envuelto que inyecta contexto PET
    """

    def wrapped_dispatcher(command: str, argument: str) -> dict[str, Any]:
        # Obtener respuesta original
        response = original_dispatcher(command, argument)

        # Cargar PETs asociados a la sesión si existen en payload
        session_id = str(session.get("session_id", ""))
        pet_bundle_ids = session.get("payload", {}).get("pet_bundle_ids", [])

        if not pet_bundle_ids:
            return response

        try:
            # Enriquecer contexto si hay PETs
            academic_context = load_pet_bundles_for_session(
                store=store,
                session_id=session_id,
                packet_id=str(session.get("payload", {}).get("packet_id", "")),
                pet_bundle_ids=pet_bundle_ids,
            )

            # Inyectar contexto en la respuesta si es una sesión académica
            if academic_context.contextual_fragments or academic_context.audited_claims:
                response_text = str(response.get("text", ""))
                enriched_text = enrich_session_prompt_with_pet_context(
                    original_prompt=response_text,
                    context=academic_context,
                    inject_position="suffix",
                )
                response["text"] = enriched_text
                response["academic_context_injected"] = True
                response["pet_fragments_count"] = len(academic_context.contextual_fragments)
                response["pet_claims_count"] = len(academic_context.audited_claims)
        except Exception as e:
            # Si hay error en enriquecimiento, retornar respuesta original sin fallar
            response["academic_context_error"] = str(e)

        return response

    return wrapped_dispatcher


def attach_pet_bundles_to_session(
    *,
    store: OpenClawStore,
    session: dict[str, Any],
    pet_bundle_ids: list[str],
) -> dict[str, Any]:
    """Asocia PET bundles a una sesión académica.

    Args:
        store: OpenClawStore
        session: Diccionario de sesión a actualizar
        pet_bundle_ids: IDs de PETs a asociar

    Returns:
        Sesión actualizada con pet_bundle_ids en payload
    """
    from .session_layer import touch_session

    payload_update = {"pet_bundle_ids": pet_bundle_ids}
    return touch_session(
        store=store,
        session=session,
        payload_update=payload_update,
    )


def query_session_pet_context(
    *,
    store: OpenClawStore,
    session_id: str,
) -> AcademicSessionContext | None:
    """Obtiene el contexto académico enriquecido de una sesión.

    Args:
        store: OpenClawStore
        session_id: ID de la sesión

    Returns:
        AcademicSessionContext si hay PETs asociados, None si no
    """
    session = store.get_session(session_id)
    if session is None:
        return None

    pet_bundle_ids = session.get("payload", {}).get("pet_bundle_ids", [])
    if not pet_bundle_ids:
        return None

    return load_pet_bundles_for_session(
        store=store,
        session_id=session_id,
        packet_id=str(session.get("payload", {}).get("packet_id", "")),
        pet_bundle_ids=pet_bundle_ids,
    )
