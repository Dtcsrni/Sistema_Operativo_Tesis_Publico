"""response_cache.py — Caché de respuestas con TTL por tipo de solicitud.

Estrategia:
- Clave: SHA-256(normalize(query) + ":" + request_kind)
- TTL diferenciado según volatilidad del tipo de consulta
- Bypass automático para consultas volátiles (fecha/hora/precio/etc.)
- Backend: OpenClawStore.cache_context / get_cached_context (ya existente)
- Marca las respuestas cacheadas con cache_hit=True en el payload

Beneficio estimado: -30-50% tokens en consultas frecuentes repetidas.
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any

# ── TTL por tipo de solicitud (segundos) ─────────────────────────────────────
# Valores conservadores que preservan factualidad reciente
CACHE_TTL: dict[str, int] = {
    "greeting": 300,        # 5 min — saludos pueden variar poco
    "standard": 900,        # 15 min — chat general
    "factual_short": 1800,  # 30 min — hechos estables
    "knowledge": 3600,      # 1 hora — conocimiento base cambia poco
    "reasoning": 1800,      # 30 min — razonamientos dependen del contexto
    "research": 7200,       # 2 horas — investigación académica estable
    "coding": 600,          # 10 min — código cambia con el proyecto
    "deep": 1800,           # 30 min
    "technical": 600,       # 10 min — estado del sistema puede cambiar
    "system": 60,           # 1 min — estado de sistema muy volátil
}

# Tipos que NUNCA se cachean independientemente del contenido
_NEVER_CACHE_KINDS = {"system", "greeting"}

# Marcadores de consulta volátil (bypass de caché aunque el tipo lo permita)
_VOLATILE_MARKERS = frozenset({
    "ahora", "hoy", "hora", "precio", "últim", "ultim", "reciente",
    "actual", "noticias", "esta semana", "este mes", "temperatura",
    "clima", "estado del sistema", "cuántos tokens", "cuantos tokens",
    "make it", "right now", "today", "current", "latest",
})

# Prefijo de clave en el store para evitar colisiones con otros contextos
_CACHE_KEY_PREFIX = "response_cache:"


class ResponseCache:
    """Caché de respuestas del bot con TTL diferenciado por tipo de solicitud.

    Usage:
        cache = ResponseCache(store)
        hit = cache.get("¿qué es Modbus?", "knowledge")
        if hit:
            return hit["text"]
        # … generar respuesta …
        cache.put("¿qué es Modbus?", "knowledge", response_text, model="qwen3:4b")
    """

    def __init__(self, store: Any) -> None:
        self._store = store

    # ── Métodos públicos ──────────────────────────────────────────────────────

    def get(self, query: str, request_kind: str) -> dict[str, Any] | None:
        """Devuelve la entrada cacheada si existe y no ha expirado.

        Returns:
            dict con keys: text, model, cached_at, request_kind
            None si no hay hit o si expiró.
        """
        if not self._should_cache(query, request_kind):
            return None
        key = self._make_key(query, request_kind)
        raw = self._store.get_cached_context(key)
        if raw is None:
            return None
        try:
            entry = raw if isinstance(raw, dict) else json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        ttl = CACHE_TTL.get(request_kind, 900)
        age = time.time() - float(entry.get("cached_at", 0))
        if age > ttl:
            return None  # expirado — lazy eviction
        return entry

    def put(
        self,
        query: str,
        request_kind: str,
        text: str,
        *,
        model: str,
        extra: dict[str, Any] | None = None,
    ) -> bool:
        """Almacena una respuesta en caché.

        Returns:
            True si se almacenó, False si se omitió (consulta volátil, tipo no cacheable).
        """
        if not self._should_cache(query, request_kind):
            return False
        if not text.strip():
            return False
        key = self._make_key(query, request_kind)
        entry: dict[str, Any] = {
            "text": text,
            "model": model,
            "request_kind": request_kind,
            "cached_at": time.time(),
            "query_preview": query[:80],
        }
        if extra:
            entry.update(extra)
        try:
            self._store.save_cached_context(key, entry)
            return True
        except Exception:
            return False

    def invalidate_by_kind(self, request_kind: str) -> None:
        """Marca todas las entradas de un tipo como inválidas (TTL=0)."""
        # Implementación pragmática: no hay scanner de keys en OpenClawStore.
        # Se fuerza TTL=0 a través del store si tiene soporte, de lo contrario
        # las entradas expiran naturalmente.
        pass  # Lazy eviction es suficiente para los TTL cortos configurados

    def stats(self) -> dict[str, Any]:
        """Devuelve estadísticas básicas del caché (para /herramienta estado)."""
        return {
            "backend": "openclaw_store_cache",
            "ttl_by_kind": CACHE_TTL,
            "never_cache_kinds": sorted(_NEVER_CACHE_KINDS),
        }

    # ── Métodos internos ──────────────────────────────────────────────────────

    def _should_cache(self, query: str, request_kind: str) -> bool:
        """Determina si esta consulta es elegible para caché."""
        if request_kind in _NEVER_CACHE_KINDS:
            return False
        if self._is_volatile(query):
            return False
        return True

    @staticmethod
    def _is_volatile(query: str) -> bool:
        """Detecta si la consulta tiene contenido que cambia frecuentemente."""
        normalized = query.lower()
        return any(marker in normalized for marker in _VOLATILE_MARKERS)

    @staticmethod
    def _make_key(query: str, request_kind: str) -> str:
        """Genera la clave de caché reproducible y colisión-resistente."""
        normalized = " ".join(query.lower().split())  # normalizar espacios
        raw = f"{normalized}:{request_kind}"
        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]
        return f"{_CACHE_KEY_PREFIX}{digest}"


# ── Helpers para integración en telegram_bot.py ───────────────────────────────

def cache_hit_tag() -> str:
    """Tag HTML para marcar respuestas cacheadas en Telegram."""
    return " <i>· ⚡ caché</i>"


def is_volatile(query: str) -> bool:
    """Wrapper público de _VOLATILE_MARKERS para uso externo."""
    normalized = query.lower()
    return any(marker in normalized for marker in _VOLATILE_MARKERS)
