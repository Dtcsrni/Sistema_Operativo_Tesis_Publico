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
import re
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
        self._glob_cache: dict[str, list[Path]] = {}
        self._hash_cache: dict[Path, str] = {}

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

    def _glob_to_regex(self, pattern: str) -> re.Pattern:
        """Convierte un patrón de glob a expresión regular compatible con ** y *."""
        p = pattern.replace("\\", "/")
        p = p.replace("/**/", "__SLASH_DOUBLE_STAR_SLASH__")
        if p.endswith("/**"):
            p = p[:-3] + "__SLASH_DOUBLE_STAR_END__"
        if p.startswith("**/"):
            p = "__DOUBLE_STAR_SLASH_START__" + p[3:]
        p = p.replace("**", "__DOUBLE_STAR__")
        p = p.replace("*", "__SINGLE_STAR__")
        p = p.replace("?", "__QUESTION_MARK__")
        
        escaped = re.escape(p)
        
        replacements = {
            "__SLASH_DOUBLE_STAR_SLASH__": r"/(?:.*/)?",
            "__SLASH_DOUBLE_STAR_END__": r"(?:/.*)?",
            "__DOUBLE_STAR_SLASH_START__": r"(?:.*/)?",
            "__DOUBLE_STAR__": r".*",
            "__SINGLE_STAR__": r"[^/]*",
            "__QUESTION_MARK__": r"[^/]",
        }
        
        regex_str = escaped
        for placeholder, regex_val in replacements.items():
            regex_str = regex_str.replace(placeholder, regex_val)
            
        return re.compile("^" + regex_str + "$", re.IGNORECASE)

    def _get_all_files(self) -> list[str]:
        """Obtiene recursivamente todos los archivos del repositorio omitiendo directorios pesados."""
        if hasattr(self, "_all_files_cache"):
            return self._all_files_cache

        ignored_dirs = {
            ".git", ".github", ".venv", "venv", "node_modules", ".next",
            ".pytest_cache", ".serena", "tmp", ".tmp", "brain", "scratch",
            "__pycache__", ".openclaw", ".vscode", "out", "dist", "models", "backups"
        }
        
        all_files: list[str] = []
        root_str = str(self._root)
        
        for root, dirs, files in os.walk(root_str):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_str)
                rel_path_slash = rel_path.replace("\\", "/")
                all_files.append(rel_path_slash)
                
        self._all_files_cache = all_files
        return all_files

    def _resolve_files(self, watch_patterns: list[str]) -> list[Path]:
        """Resuelve globs desde ROOT y retorna lista ordenada de archivos existentes."""
        files: list[Path] = []
        all_repo_files = self._get_all_files()
        
        for pattern in watch_patterns:
            if pattern in self._glob_cache:
                files.extend(self._glob_cache[pattern])
                continue
            
            rx = self._glob_to_regex(pattern)
            matched_rel_paths = [f for f in all_repo_files if rx.match(f)]
            file_paths = [self._root / f for f in matched_rel_paths]
            self._glob_cache[pattern] = file_paths
            files.extend(file_paths)
            
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
            file_hash = self._hash_cache.get(f)
            if file_hash is None:
                try:
                    fh = hashlib.sha256()
                    with f.open("rb") as fd:
                        while chunk := fd.read(65536):
                            fh.update(chunk)
                    file_hash = fh.hexdigest()
                except OSError:
                    file_hash = "error"
                self._hash_cache[f] = file_hash
            h.update(file_hash.encode("ascii"))
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
