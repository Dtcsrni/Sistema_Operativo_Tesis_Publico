from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import dump_json
from observability_snapshot import SNAPSHOT_PRIVATE_PATH, SNAPSHOT_PUBLIC_PATH, build_snapshot


def main() -> int:
    private_snapshot = build_snapshot(public=False)
    public_snapshot = build_snapshot(public=True)
    dump_json(SNAPSHOT_PRIVATE_PATH, private_snapshot)
    dump_json(SNAPSHOT_PUBLIC_PATH, public_snapshot)
    print(f"[OK] Snapshot privado: {SNAPSHOT_PRIVATE_PATH}")
    print(f"[OK] Snapshot publico: {SNAPSHOT_PUBLIC_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
