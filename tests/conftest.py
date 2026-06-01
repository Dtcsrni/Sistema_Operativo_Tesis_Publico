import os
import sys
from pathlib import Path

# Add project roots to PYTHONPATH
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
scripts_dir = ROOT / "07_scripts"
sys.path.insert(0, str(scripts_dir))
for subdir in ["ops", "audit", "utils", "benchmarks", "build_runner", "toltecayotl", "ai_tools"]:
    sys.path.insert(0, str(scripts_dir / subdir))

# Setup dummy environment to isolate test execution
os.environ["TELEGRAM_MODE"] = "TELEMETRY_ONLY"

# Clear any persistent host environment variables that might interfere with tests
for key in [
    "OPENCLAW_DB_PATH", "OPENCLAW_DATA_DIR", "OPENCLAW_SOURCE_JSONL", "TOLTECAYOTL_SYNC_DIR",
    "OPENCLAW_DOMAINS_ENV_DIR", "OPENCLAW_CLOUD_ENABLED", "OPENCLAW_DESKTOP_COMPUTE_ENABLED",
    "OPENCLAW_WEB_ENABLED", "OPENCLAW_DESKTOP_RUNTIME", "OPENCLAW_DESKTOP_RUNTIME_BASE_URL",
    "OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "OPENCLAW_LLAMACPP_BASE_URL",
    "OPENCLAW_EDGE_INFERENCE_BASE_URL", "OPENCLAW_EDGE_OLLAMA_BASE_URL",
    "OPENCLAW_FORCE_EDGE_READY", "OPENCLAW_FORCE_LLAMACPP_READY", "OPENCLAW_FORCE_NPU_READY",
    "OPENCLAW_BENCHMARK_SIMULATION", "OPENCLAW_NPU_AUTO_PROMOTE"
]:
    os.environ.pop(key, None)
