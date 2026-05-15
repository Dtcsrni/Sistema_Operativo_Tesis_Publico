from __future__ import annotations

import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings




# Add runtime/openclaw to sys.path
ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(ROOT / "runtime" / "openclaw"))

from common import dump_json, now_stamp
from openclaw_local.runtime_status import probe_runtime_status


_SERVICE_ENV_KEYS = {
    "OPENCLAW_EDGE_OLLAMA_BASE_URL",
    "OPENCLAW_DESKTOP_COMPUTE_BASE_URL",
    "OPENCLAW_DESKTOP_RUNTIME_BASE_URL",
    "OPENCLAW_DESKTOP_COMPUTE_MODEL",
    "OPENCLAW_DESKTOP_RUNTIME_MODEL",
    "OPENCLAW_DESKTOP_RUNTIME",
    "OPENCLAW_LLAMACPP_LOCAL_FALLBACK",
    "OPENCLAW_FORCE_LLAMACPP_READY",
    "OPENCLAW_FORCE_OLLAMA_READY",
    "OPENCLAW_FORCE_NPU_READY",
}


def _normalize_service_url(value: str) -> str:
    normalized = value.strip().strip('"').strip("'")
    return normalized.replace("ollama-pc", "127.0.0.1") if "ollama-pc" in normalized else normalized


def _load_env_file(env_path: Path) -> None:
    if not env_path.exists():
        return

    with env_path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key in _SERVICE_ENV_KEYS:
                os.environ[key] = _normalize_service_url(value)


def main() -> int:
    try:
        _load_env_file(ROOT / "config" / "env" / "openclaw.env")
        print("[RUN] Probing OpenClaw runtime status...")
        status = probe_runtime_status(repo_root=ROOT)
        
        # Add a timestamp
        status["generated_at"] = now_stamp()
        
        # Save to config
        output_path = "00_sistema_tesis/config/openclaw_status.json"
        dump_json(output_path, status)
        
        print(f"[OK] OpenClaw status saved to {output_path}")
        return 0
    except Exception as e:
        print(f"[ERROR] Failed to probe OpenClaw status: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
