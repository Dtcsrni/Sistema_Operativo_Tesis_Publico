"""build_runner/cache.py — Caché de fingerprints para builds incrementales.

Detecta qué pasos necesitan re-ejecutarse basándose en si los archivos
que vigilan (campo `watch`) han cambiado desde la última ejecución exitosa.

Estrategia:
  - Por cada paso se computa un fingerprint SHA-256 del conjunto de archivos
    que tiene en su campo `watch` (globs resueltos).
  - El fingerprint se persiste en `.build_cache.json` dentro de audit_history/.
  - Si el fingerprint coincide con el almacenado Y el paso terminó en "ok",
    el paso puede omitirse (cache hit).
  - `--force` o ausencia de campo `watch` → siempre ejecuta.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from build_runner.registry import BuildStep

CACHE_FILE_NAME = ".build_cache.json"


class BuildCache:
    """Gestiona fingerprints SHA-256 de pasos del build para ejecución incremental."""

    def __init__(self, root: Path, cache_dir: Path) -> None:
        self._root = root
        self._path = cache_dir / CACHE_FILE_NAME
        self._data: dict[str, dict] = self._load()

    # ── Persistencia ──────────────────────────────────────────────────────────

    def _load(self) -> dict[str, dict]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    # ── Fingerprint ───────────────────────────────────────────────────────────

    def _resolve_files(self, watch_patterns: list[str]) -> list[Path]:
        """Resuelve globs desde ROOT y retorna lista ordenada de archivos existentes."""
        files: list[Path] = []
        for pattern in watch_patterns:
            matched = sorted(self._root.glob(pattern))
            files.extend(f for f in matched if f.is_file())
        return sorted(set(files))

    def compute_fingerprint(self, step: "BuildStep") -> str | None:
        """Calcula SHA-256 del contenido de todos los archivos vigilados.

        Retorna None si el paso no tiene campo `watch` (siempre se ejecuta).
        """
        if not step.watch:
            return None
        files = self._resolve_files(step.watch)
        if not files:
            # No hay archivos que vigilar → fingerprint vacío constante
            return "empty_watch"
        h = hashlib.sha256()
        for f in files:
            try:
                with f.open("rb") as fd:
                    while chunk := fd.read(65536):
                        h.update(chunk)
            except OSError:
                pass
        return h.hexdigest()

    # ── Hit / Miss ────────────────────────────────────────────────────────────

    def is_hit(self, step: "BuildStep") -> bool:
        """True si el paso puede omitirse (sin cambios desde última ejecución OK)."""
        fp = self.compute_fingerprint(step)
        if fp is None:
            return False  # Sin watch → siempre ejecutar
        entry = self._data.get(step.label, {})
        return entry.get("fingerprint") == fp and entry.get("last_status") == "ok"

    def record(self, step: "BuildStep", status: str) -> None:
        """Guarda el fingerprint y estado tras la ejecución de un paso."""
        fp = self.compute_fingerprint(step)
        self._data[step.label] = {
            "fingerprint": fp,
            "last_status": status,
        }

    def invalidate(self, label: str) -> None:
        """Fuerza re-ejecución de un paso específico eliminando su entrada."""
        self._data.pop(label, None)

    def clear(self) -> None:
        """Invalida toda la caché."""
        self._data.clear()

    def summary(self) -> dict[str, str]:
        """Retorna {label: last_status} para depuración."""
        return {k: v.get("last_status", "?") for k, v in self._data.items()}
