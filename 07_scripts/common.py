from __future__ import annotations

import csv
import hashlib
import os
from datetime import datetime
from pathlib import Path

from data_io import dump_structured_path, load_structured_path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "00_sistema_tesis" / "config"
PLANNING_DIR = ROOT / "01_planeacion"
DASHBOARD_DIR = ROOT / "06_dashboard" / "generado"
AGENT_IDENTITY_PATH = "00_sistema_tesis/config/agent_identity.json"


def _load_env_file() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return

    with env_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            if not key or key.startswith("#"):
                continue
            if key in os.environ:
                continue
            os.environ[key] = value.strip().strip('"').strip("'")


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    _load_env_file()
else:
    _load_env_file()

VALID_PRIORITIES = {"baja", "media", "alta", "critica"}
VALID_EVIDENCE = {"ausente", "parcial", "fuerte"}


def load_yaml_json(relative_path: str) -> dict:
    path = ROOT / relative_path
    return load_structured_path(path)


def load_agent_identity() -> dict[str, str]:
    payload = load_yaml_json(AGENT_IDENTITY_PATH)
    identity = dict(payload.get("agent_identity", {}))
    overrides = {
        "agent_role": os.getenv("SISTEMA_TESIS_AGENT_ROLE", "").strip(),
        "provider": os.getenv("SISTEMA_TESIS_AGENT_PROVIDER", "").strip(),
        "model_version": os.getenv("SISTEMA_TESIS_AGENT_MODEL_VERSION", "").strip(),
        "runtime_label": os.getenv("SISTEMA_TESIS_AGENT_RUNTIME", "").strip(),
    }
    for key, value in overrides.items():
        if value:
            identity[key] = value

    required = ("agent_role", "provider", "model_version", "runtime_label")
    missing = [key for key in required if not str(identity.get(key, "")).strip()]
    if missing:
        raise KeyError(f"agent_identity.json incompleto. Faltan campos: {', '.join(missing)}")
    return {key: str(identity[key]).strip() for key in required}


def apply_agent_identity_placeholders(content: str) -> str:
    identity = load_agent_identity()
    replacements = {
        "[AGENTE_ROL_IA]": identity["agent_role"],
        "[PROVEEDOR_IA]": identity["provider"],
        "[MODELO_VERSION_IA]": identity["model_version"],
        "[RUNTIME_IA]": identity["runtime_label"],
    }
    for source, target in replacements.items():
        content = content.replace(source, target)
    return content


def load_csv_rows(relative_path: str) -> list[dict]:
    path = ROOT / relative_path
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def list_markdown_entries(relative_dir: str) -> list[dict]:
    directory = ROOT / relative_dir
    entries = []
    for path in sorted(directory.glob("*.md"), reverse=True):
        title = path.stem
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        date_prefix = path.name[:10] if len(path.name) >= 10 else ""
        entries.append(
            {
                "archivo": str(path.relative_to(ROOT)).replace("\\", "/"),
                "fecha": date_prefix,
                "titulo": title,
            }
        )
    return entries


def extract_markdown_section_bullets(relative_path: str, section_title: str) -> list[str]:
    path = ROOT / relative_path
    bullets: list[str] = []
    in_section = False

    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            stripped = raw_line.strip()

            if stripped == f"## {section_title}":
                in_section = True
                continue

            if in_section and stripped.startswith("## "):
                break

            if in_section and stripped.startswith("- "):
                bullets.append(stripped[2:].strip())

    return bullets


def extract_markdown_labeled_value(relative_path: str, section_title: str, label: str) -> str | None:
    prefix = f"{label}:".lower()
    for bullet in extract_markdown_section_bullets(relative_path, section_title):
        if bullet.lower().startswith(prefix):
            return bullet.split(":", 1)[1].strip()
    return None


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_generated_dir() -> None:
    DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)


def ensure_directory(relative_dir: str) -> Path:
    path = ROOT / relative_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def relative_posix(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def file_sha256(relative_path: str) -> str:
    path = ROOT / relative_path
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def path_timestamp(relative_path: str) -> str:
    path = ROOT / relative_path
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")


def dump_json(relative_path: str, payload: dict) -> Path:
    path = ROOT / relative_path
    return dump_structured_path(path, payload)


def directory_markdown_status(relative_dir: str) -> dict:
    directory = ROOT / relative_dir
    markdown_files = sorted(path for path in directory.rglob("*.md") if path.is_file())
    non_keep_files = sorted(
        path for path in directory.rglob("*") if path.is_file() and path.name != ".gitkeep"
    )
    return {
        "relative_dir": relative_dir,
        "exists": directory.exists(),
        "markdown_files": [relative_posix(path) for path in markdown_files],
        "non_keep_files": [relative_posix(path) for path in non_keep_files],
        "has_operational_content": bool(non_keep_files),
    }


def canonical_file_status() -> list[dict]:
    sistema = load_yaml_json("00_sistema_tesis/config/sistema_tesis.yaml")
    statuses = []
    for label, rel_path in sistema["rutas_canonicas"].items():
        path = ROOT / rel_path
        exists = path.exists()
        statuses.append(
            {
                "clave": label,
                "ruta": rel_path,
                "existe": exists,
                "modificado": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S") if exists else "n/a",
            }
        )
    return statuses
