from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from typing import Any
from urllib import error, request
from uuid import uuid4


def generate_image_from_prompt(prompt: str, *, timeout_seconds: int = 120) -> dict[str, Any]:
    backend = os.getenv("OPENCLAW_IMAGE_BACKEND", "comfyui").strip().lower()
    if backend != "comfyui":
        return {"status": "error", "error": f"image_backend_not_supported:{backend}"}
    return _generate_with_comfyui(prompt, timeout_seconds=timeout_seconds)


def _generate_with_comfyui(prompt: str, *, timeout_seconds: int) -> dict[str, Any]:
    # El backend operativo de ComfyUI vive en la PC y se expone al edge por el túnel SSH.
    base_url = os.getenv("OPENCLAW_COMFYUI_BASE_URL", "http://127.0.0.1:28000").rstrip("/")
    workflow_path = os.getenv("OPENCLAW_COMFYUI_WORKFLOW_JSON", "").strip()
    output_dir = Path(os.getenv("OPENCLAW_IMAGE_OUTPUT_DIR", "/var/lib/herramientas/openclaw/artifacts/images"))

    if not _comfyui_ready(base_url, timeout_seconds=min(5, timeout_seconds)):
        return {"status": "unavailable", "backend": "comfyui", "base_url": base_url, "error": "comfyui_unreachable"}
    if not workflow_path:
        return {
            "status": "config_required",
            "backend": "comfyui",
            "base_url": base_url,
            "error": "missing_OPENCLAW_COMFYUI_WORKFLOW_JSON",
        }

    template = Path(workflow_path)
    if not template.exists():
        return {"status": "config_required", "backend": "comfyui", "base_url": base_url, "error": f"workflow_not_found:{workflow_path}"}

    workflow = json.loads(template.read_text(encoding="utf-8"))
    workflow = _inject_prompt(workflow, prompt)
    client_id = f"openclaw-{uuid4().hex}"
    payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
    req = request.Request(f"{base_url}/prompt", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            queued = json.loads(response.read().decode("utf-8", errors="replace"))
    except (OSError, error.URLError, json.JSONDecodeError) as exc:
        return {"status": "error", "backend": "comfyui", "base_url": base_url, "error": f"prompt_submit_failed:{exc}"}

    source_output = _latest_output_file()
    if source_output is None:
        return {"status": "queued", "backend": "comfyui", "base_url": base_url, "prompt_id": queued.get("prompt_id", "")}

    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"openclaw-image-{int(time.time())}-{source_output.name}"
    shutil.copy2(source_output, target)
    return {
        "status": "ok",
        "backend": "comfyui",
        "base_url": base_url,
        "prompt_id": queued.get("prompt_id", ""),
        "path": str(target),
    }


def _comfyui_ready(base_url: str, *, timeout_seconds: int) -> bool:
    try:
        with request.urlopen(f"{base_url}/system_stats", timeout=timeout_seconds) as response:
            return 200 <= int(response.status) < 300
    except OSError:
        return False


def _inject_prompt(value: Any, prompt: str) -> Any:
    if isinstance(value, dict):
        return {key: _inject_prompt(item, prompt) for key, item in value.items()}
    if isinstance(value, list):
        return [_inject_prompt(item, prompt) for item in value]
    if isinstance(value, str):
        return value.replace("{prompt}", prompt).replace("{{prompt}}", prompt)
    return value


def _latest_output_file() -> Path | None:
    configured = os.getenv("OPENCLAW_COMFYUI_OUTPUT_DIR", "").strip()
    candidates = []
    if configured:
        candidates.append(Path(configured))
    candidates.append(Path("/mnt/c/Users/evega/Documents/ComfyUI/output"))
    files: list[Path] = []
    for directory in candidates:
        if directory.exists():
            files.extend(path for path in directory.rglob("*") if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"})
    if not files:
        return None
    return max(files, key=lambda path: path.stat().st_mtime)
