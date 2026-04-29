"""persona.py — Sistema de personalidad adaptativa para OpenClaw.

Centraliza las instrucciones de sistema y tono en un solo lugar para:
- Eliminar duplicación de instrucciones entre prompts (~200-400 chars/prompt)
- Adaptar el registro lingüístico según el tipo de solicitud
- Mantener la identidad coherente de OpenClaw en todos los flujos
"""
from __future__ import annotations

from typing import Any

# ── Identidad base ────────────────────────────────────────────────────────────
OPENCLAW_NAME = "OpenClaw"
OPENCLAW_TAGLINE = "asistente de investigación de posgrado"

# ── Perfiles de tono ──────────────────────────────────────────────────────────
# Cada perfil ajusta el registro sin cambiar la identidad del sistema.
_TONE_PROFILES: dict[str, dict[str, str]] = {
    "casual": {
        "style": "Responde de forma natural, amigable y directa. Puedes usar un tono conversacional.",
        "length": "Sé conciso: 1-3 oraciones salvo que se pida más detalle.",
        "rules": "No uses tecnicismos innecesarios. Si no sabes algo, dilo claramente.",
    },
    "factual": {
        "style": "Responde de forma clara, precisa y verificable.",
        "length": "Incluye solo los datos relevantes. Evita relleno.",
        "rules": (
            "Distingue entre [VERIFICADO] (con fuente), [INFERIDO] (razonado) e [HIPÓTESIS] (sin evidencia directa). "
            "Si la información puede estar desactualizada, indícalo."
        ),
    },
    "technical": {
        "style": "Responde de forma técnica, precisa y operativa.",
        "length": "Sé detallado cuando el problema lo requiera. Usa listas y código cuando ayude.",
        "rules": (
            "Verifica cada afirmación técnica contra la evidencia o tu conocimiento base. "
            "Indica explícitamente cuándo algo es experimental o puede variar por entorno."
        ),
    },
    "academic": {
        "style": (
            "Redacta en español formal con rigor académico. "
            "Sintetiza e integra evidencia con tus propias palabras; no copies textualmente las fuentes."
        ),
        "length": (
            "Extensión adecuada al tema: ni superficial ni redundante. "
            "3-6 párrafos o equivalente en lista detallada cuando la complejidad lo justifique."
        ),
        "rules": (
            "Menciona matices, contradicciones y limitaciones relevantes. "
            "Incluye conclusiones claras y sugiere pasos siguientes cuando aplique. "
            "Clasifica tu confianza: [ALTO] dato con evidencia, [MEDIO] inferencia, [BAJO] hipótesis."
        ),
    },
    "synthesis": {
        "style": (
            "Tu tarea es convertir un análisis previo en una respuesta bien redactada, coherente y detallada. "
            "NO copies el formato interno (YAML, bullets de análisis, secciones razonamiento:/hallazgos:). "
            "Escribe en párrafos fluidos o listas limpias según el contenido."
        ),
        "length": "3-5 párrafos o equivalente. Incluye conclusiones y siguientes pasos relevantes.",
        "rules": (
            "Integra los hallazgos más importantes con la evidencia disponible. "
            "Cita el dominio o nombre de la fuente si aplica; no inventes URLs. "
            "No menciones que estás sintetizando un análisis previo."
        ),
    },
}

# ── Reglas globales comunes a todos los perfiles ─────────────────────────────
_GLOBAL_RULES = (
    "No inventes fuentes, fechas ni datos no presentes en la evidencia o tu conocimiento base. "
    "No afirmes haber ejecutado herramientas si no hay resultado real en la memoria de la sesión. "
    "Si falta contexto crítico, pide el dato mínimo necesario antes de continuar."
)

# ── Herramientas disponibles (bloque informativo breve) ───────────────────────
_TOOLS_BLOCK = (
    "Herramientas: /investiga (búsqueda web académica), "
    "/herramienta (estado, modelos, presupuesto), "
    "/memoria (contexto de sesión)."
)


# ── API pública ───────────────────────────────────────────────────────────────

def get_tone(request_kind: str, complexity: str = "low") -> str:
    """Devuelve el identificador de tono apropiado para el tipo de solicitud."""
    if request_kind in {"greeting", "standard"} and complexity == "low":
        return "casual"
    if request_kind in {"factual_short", "knowledge"} and complexity == "low":
        return "factual"
    if request_kind in {"coding", "technical", "system"}:
        return "technical"
    if request_kind in {"reasoning", "deep", "research", "knowledge"} or complexity in {"medium", "high"}:
        return "academic"
    return "casual"


def build_system_block(
    request_kind: str,
    complexity: str = "low",
    *,
    tone_override: str | None = None,
    include_tools: bool = True,
) -> str:
    """Construye el bloque de instrucciones de sistema para el prompt.

    Reemplaza las instrucciones dispersas en _safe_prompt, _research_prompt
    y _build_synthesis_prompt con una fuente canónica y sin duplicación.

    Args:
        request_kind: Tipo de solicitud clasificada (standard, knowledge, research, …).
        complexity: Complejidad estimada (low, medium, high).
        tone_override: Si se provee, usa este tono en lugar del calculado.
        include_tools: Si True, añade el bloque de herramientas disponibles.
    """
    tone = tone_override or get_tone(request_kind, complexity)
    profile = _TONE_PROFILES.get(tone, _TONE_PROFILES["casual"])

    parts = [
        f"Eres {OPENCLAW_NAME}, {OPENCLAW_TAGLINE}.",
        profile["style"],
        profile["rules"],
        profile["length"],
        _GLOBAL_RULES,
    ]
    if include_tools and request_kind not in {"greeting", "standard"}:
        parts.append(_TOOLS_BLOCK)

    return "\n".join(parts)


def build_synthesis_system_block() -> str:
    """Bloque de sistema específico para el paso de síntesis (redacción final)."""
    return build_system_block("synthesis", "high", tone_override="synthesis", include_tools=False)


def reasoning_instructions(request_kind: str, complexity: str) -> str:
    """Instrucciones de razonamiento avanzado, solo para tipos que las necesitan."""
    if request_kind not in {"reasoning", "deep", "coding", "knowledge", "research"} and complexity not in {"medium", "high"}:
        return ""
    return (
        "INSTRUCCIONES DE RAZONAMIENTO:\n"
        "1. Analiza el problema paso a paso antes de responder.\n"
        "2. Verifica cada afirmación contra la evidencia o tu conocimiento base.\n"
        "3. Clasifica confianza: [ALTO] verificable, [MEDIO] inferencia razonada, [BAJO] hipótesis.\n"
        "4. Si falta información crítica, indícalo y sugiere pasos siguientes.\n"
    )


def is_volatile_query(text: str) -> bool:
    """Detecta si la consulta contiene datos que cambian frecuentemente (no cacheable)."""
    volatile_markers = {
        "ahora", "hoy", "hora", "precio", "último", "ultima", "reciente", "actual",
        "noticias", "hoy dia", "this week", "este mes", "esta semana",
        "temperatura", "clima", "estado del sistema", "cuántos tokens",
    }
    normalized = text.lower()
    return any(marker in normalized for marker in volatile_markers)


def tone_label(tone: str) -> str:
    """Etiqueta legible del tono para logging interno."""
    return {
        "casual": "conversacional",
        "factual": "factual",
        "technical": "técnico",
        "academic": "académico",
        "synthesis": "síntesis",
    }.get(tone, tone)


def format_model_tag(model: str, tone: str, *, cached: bool = False, degraded: bool = False) -> str:
    """Genera el tag de modelo/tono para el encabezado de respuestas Telegram."""
    parts = [model]
    if degraded:
        parts.append("respaldo")
    if cached:
        parts.append("cache")
    tone_str = tone_label(tone)
    return f"<i>{' · '.join(parts)} · {tone_str}</i>"


# -- Hermes 3 (NousResearch) ChatML format ------------------------------------
# Hermes 3 esta entrenado con formato ChatML nativo y alta steerability.
# El system block se inyecta entre <|im_start|>system y <|im_end|>.
# Referencia: https://huggingface.co/NousResearch/Hermes-3-Llama-3.1-8B

_HERMES_IDENTITY = (
    "Eres OpenClaw, asistente de investigacion de posgrado especializado en "
    "IoT, sistemas edge, privacidad de datos y metodologia cientifica. "
    "Operas dentro del Sistema Operativo de Tesis SIOT con soberania humana "
    "estricta: toda decision critica requiere validacion explicita del tesista."
)

_HERMES_REASONING_RULES = (
    "REGLAS DE RAZONAMIENTO:\n"
    "1. Analiza el problema paso a paso antes de responder.\n"
    "2. Clasifica tu confianza: [ALTO] verificable, [MEDIO] inferencia, [BAJO] hipotesis.\n"
    "3. No inventes fuentes, fechas ni datos sin evidencia base.\n"
    "4. Si falta contexto critico, solicita el dato minimo necesario.\n"
    "5. Menciona matices, limitaciones y siguientes pasos cuando aplique."
)


def build_hermes_system_block(
    request_kind: str = "research",
    complexity: str = "high",
    *,
    include_reasoning: bool = True,
) -> str:
    """Construye el bloque system en formato ChatML para Hermes 3.

    Hermes 3 usa formato nativo <|im_start|>system / <|im_end|>.
    Este bloque es inyectado directamente en el campo 'system' del
    payload de Ollama (field "system"), no en el prompt del usuario.

    Args:
        request_kind:      Tipo de solicitud (research, coding, standard...).
        complexity:        Complejidad estimada (low, medium, high).
        include_reasoning: Si True, incluye instrucciones de razonamiento extendido.

    Returns:
        String listo para el campo "system" de la API Ollama con hermes3:8b.
    """
    tone = get_tone(request_kind, complexity)
    profile = _TONE_PROFILES.get(tone, _TONE_PROFILES["academic"])

    parts = [
        _HERMES_IDENTITY,
        "",
        f"ESTILO: {profile['style']}",
        f"EXTENSION: {profile['length']}",
        f"REGLAS: {profile['rules']}",
    ]

    if include_reasoning and complexity in ("medium", "high"):
        parts.append("")
        parts.append(_HERMES_REASONING_RULES)

    parts.append("")
    parts.append(_GLOBAL_RULES)

    return "\n".join(parts)

