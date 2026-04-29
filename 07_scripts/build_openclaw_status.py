from __future__ import annotations

import sys
from pathlib import Path

# Add runtime/openclaw to sys.path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT / "runtime" / "openclaw"))

from common import dump_json, now_stamp
from openclaw_local.runtime_status import probe_runtime_status

def main() -> int:
    try:
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
