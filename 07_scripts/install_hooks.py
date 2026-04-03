from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PRE_COMMIT_HOOK = """#!/bin/sh
PYTHON_BIN="${SISTEMA_TESIS_HOOK_PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if [ -x "./.venv/bin/python.exe" ]; then
    PYTHON_BIN="./.venv/bin/python.exe"
  elif [ -x "./.venv/Scripts/python.exe" ]; then
    PYTHON_BIN="./.venv/Scripts/python.exe"
  else
    PYTHON_BIN="python"
  fi
fi

"$PYTHON_BIN" 07_scripts/governance_gate.py --stage pre-commit
STATUS=$?
if [ $STATUS -ne 0 ]; then
  exit $STATUS
fi

if command -v pre-commit >/dev/null 2>&1; then
  SKIP=governance-gate pre-commit run --hook-stage pre-commit
  exit $?
fi

echo "[WARN] pre-commit no esta instalado; solo se ejecuto governance_gate."
exit 0
"""

PRE_PUSH_HOOK = """#!/bin/sh
PYTHON_BIN="${SISTEMA_TESIS_HOOK_PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if [ -x "./.venv/bin/python.exe" ]; then
    PYTHON_BIN="./.venv/bin/python.exe"
  elif [ -x "./.venv/Scripts/python.exe" ]; then
    PYTHON_BIN="./.venv/Scripts/python.exe"
  else
    PYTHON_BIN="python"
  fi
fi

"$PYTHON_BIN" 07_scripts/governance_gate.py --stage pre-push
"""

POST_COMMIT_SYNC_HOOK = """#!/bin/sh
BRANCH="$(git branch --show-current 2>/dev/null)"
if [ "$BRANCH" != "main" ]; then
  exit 0
fi

PYTHON_BIN="${SISTEMA_TESIS_HOOK_PYTHON:-}"
if [ -z "$PYTHON_BIN" ]; then
  if [ -x "./.venv/bin/python.exe" ]; then
    PYTHON_BIN="./.venv/bin/python.exe"
  elif [ -x "./.venv/Scripts/python.exe" ]; then
    PYTHON_BIN="./.venv/Scripts/python.exe"
  else
    PYTHON_BIN="python"
  fi
fi

"$PYTHON_BIN" 07_scripts/sync_public_repo.py --mode mirror --target-dir ../Sistema_Operativo_Tesis_Publico --branch main --skip-local-mirror
"""

def install_hook(name, content):
    git_hook_dir = ROOT / ".git" / "hooks"
    if not git_hook_dir.parent.exists():
        print("[ERROR] No se detectó un repositorio Git.")
        return

    git_hook_path = git_hook_dir / name
    with open(git_hook_path, "w", newline="\n") as f:
        f.write(content)

    print(f"[SUCCESS] Hook instalado en {git_hook_path}")

if __name__ == "__main__":
    install_hook("pre-commit", PRE_COMMIT_HOOK)
    install_hook("pre-push", PRE_PUSH_HOOK)
    install_hook("post-commit", POST_COMMIT_SYNC_HOOK)
    install_hook("post-merge", POST_COMMIT_SYNC_HOOK)
