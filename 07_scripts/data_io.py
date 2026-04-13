from __future__ import annotations

import json
from pathlib import Path
from typing import Any


try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    yaml = None


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _try_json(text: str) -> Any:
    return json.loads(text)


def _try_yaml(text: str) -> Any:
    if yaml is None:
        raise ValueError("PyYAML no está disponible para interpretar contenido YAML real.")
    return yaml.safe_load(text)


def load_structured_path(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    stripped = text.lstrip("\ufeff").strip()
    if not stripped:
        return {}

    suffix = path.suffix.lower()
    if suffix in {".json", ".yaml", ".yml"}:
        try:
            return _try_json(stripped)
        except json.JSONDecodeError:
            return _try_yaml(text)

    return _try_json(stripped)


def dump_structured_path(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if not path.exists() or path.read_text(encoding="utf-8") != rendered:
        path.write_text(rendered, encoding="utf-8")
    return path


def load_jsonl_path(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    items: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        items.append(json.loads(line))
    return items


def dump_jsonl_path(path: Path, rows: list[dict[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n"
    path.write_text(content, encoding="utf-8")
    return path


def append_jsonl_path(path: Path, row: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
    return path
