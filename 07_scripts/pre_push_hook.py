import subprocess
import sys

if __name__ == "__main__":
    result = subprocess.run([sys.executable, "07_scripts/governance_gate.py", "--stage", "pre-push"])
    sys.exit(result.returncode)
