import subprocess
import sys

from common import preferred_python_executable

if __name__ == "__main__":
    result = subprocess.run([preferred_python_executable(), "07_scripts/governance_gate.py", "--stage", "pre-push"])
    sys.exit(result.returncode)
