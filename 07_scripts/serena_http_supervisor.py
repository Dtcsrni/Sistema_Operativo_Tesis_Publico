from __future__ import annotations

import sys
import time
import subprocess
import os
from pathlib import Path

# Compatibility wrapper: preserves supervisor path used by .vscode/serena-http scripts.
SCRIPT_ROOT = Path(__file__).resolve().parent
if str(SCRIPT_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPT_ROOT))


def main() -> int:
    module_cmd = [sys.executable, "-m", "serena.serena_http_supervisor"]
    env = os.environ.copy()
    current_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(SCRIPT_ROOT) if not current_pythonpath else f"{SCRIPT_ROOT}{os.pathsep}{current_pythonpath}"
    max_restarts = 12
    attempt = 0
    backoff_base = 2.0
    while True:
        attempt += 1
        print(f"[serena_supervisor_wrapper] starting attempt {attempt}", flush=True)
        proc = subprocess.Popen(module_cmd, env=env)
        try:
            ret = proc.wait()
        except KeyboardInterrupt:
            proc.terminate()
            proc.wait()
            return 0

        if ret == 0:
            print("[serena_supervisor_wrapper] supervisor exited normally.", flush=True)
            return 0

        print(f"[serena_supervisor_wrapper] supervisor exited with code {ret}", flush=True)
        if attempt >= max_restarts:
            print("[serena_supervisor_wrapper] max restart attempts reached; exiting.", flush=True)
            return ret

        sleep_time = backoff_base ** min(attempt, 6)
        print(f"[serena_supervisor_wrapper] restarting in {sleep_time:.1f}s...", flush=True)
        time.sleep(sleep_time)


if __name__ == "__main__":
    raise SystemExit(main())
