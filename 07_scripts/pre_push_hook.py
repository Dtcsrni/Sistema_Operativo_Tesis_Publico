import subprocess
import sys
import os

from common import preferred_python_executable

if __name__ == "__main__":
    python_bin = preferred_python_executable()
    gate = subprocess.run([python_bin, "07_scripts/governance_gate.py", "--stage", "pre-push"])
    if gate.returncode != 0:
        sys.exit(gate.returncode)

    step_id = os.environ.get("SISTEMA_TESIS_STEP_ID", "").strip()
    source_event_id = os.environ.get("SISTEMA_TESIS_SOURCE_EVENT_ID", "").strip()
    session_id = os.environ.get("SISTEMA_TESIS_SESSION_ID", "hook-pre-push-autosignoff").strip()
    public_repo_pat = os.environ.get("PUBLIC_REPO_PAT", "").strip()
    public_target_dir = os.environ.get("SISTEMA_TESIS_PUBLIC_TARGET_DIR", "../Sistema_Operativo_Tesis_Publico").strip()
    public_repo_url = os.environ.get(
        "SISTEMA_TESIS_PUBLIC_REPO_URL",
        "https://github.com/Dtcsrni/Sistema_Operativo_Tesis_Publico.git",
    ).strip()
    public_branch = os.environ.get("SISTEMA_TESIS_PUBLIC_BRANCH", "main").strip()

    if not step_id:
        print("[ERROR] Falta SISTEMA_TESIS_STEP_ID para auto-firma en pre-push.", file=sys.stderr)
        sys.exit(1)
    if not source_event_id:
        print("[ERROR] Falta SISTEMA_TESIS_SOURCE_EVENT_ID para auto-firma en pre-push.", file=sys.stderr)
        sys.exit(1)
    if not public_repo_pat:
        print("[ERROR] Falta PUBLIC_REPO_PAT para sincronizar automáticamente el repo público en pre-push.", file=sys.stderr)
        sys.exit(1)

    signoff = subprocess.run(
        [
            python_bin,
            "07_scripts/tesis.py",
            "signoff",
            "sync",
            "--step-id",
            step_id,
            "--source-event-id",
            source_event_id,
            "--session-id",
            session_id,
        ]
    )
    if signoff.returncode != 0:
        sys.exit(signoff.returncode)

    repo_url_with_token = f"https://x-access-token:{public_repo_pat}@{public_repo_url.removeprefix('https://')}"
    sync_public = subprocess.run(
        [
            python_bin,
            "07_scripts/sync_public_repo.py",
            "--mode",
            "mirror",
            "--target-dir",
            public_target_dir,
            "--repo-url",
            repo_url_with_token,
            "--branch",
            public_branch,
            "--push",
            "--allow-dirty",
        ]
    )
    sys.exit(sync_public.returncode)
