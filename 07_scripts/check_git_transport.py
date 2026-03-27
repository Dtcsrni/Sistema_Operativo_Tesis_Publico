from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from common import ROOT


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")


def is_ssh_auth_success(stdout: str, stderr: str, code: int) -> bool:
    combined = f"{stdout}\n{stderr}".lower()
    if "successfully authenticated" in combined:
        return True
    return code == 0 and "permission denied (publickey)" not in combined


def get_git_value(args: list[str]) -> str:
    result = run_command(["git", *args])
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def configure_repo_ssh_command(key_path: Path) -> subprocess.CompletedProcess[str]:
    ssh_command = f"ssh -i {key_path.as_posix()} -o IdentitiesOnly=yes -p 443"
    return run_command(["git", "config", "--local", "core.sshCommand", ssh_command])


def test_ssh_connection(key_path: Path, host: str) -> tuple[bool, str]:
    result = run_command(
        [
            "ssh",
            "-T",
            "-i",
            key_path.as_posix(),
            "-o",
            "IdentitiesOnly=yes",
            "-p",
            "443",
            host,
        ]
    )
    ok = is_ssh_auth_success(result.stdout, result.stderr, result.returncode)
    output = (result.stdout or result.stderr).strip()
    return ok, output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnóstico y configuración del transporte Git por SSH sin ssh-agent.")
    parser.add_argument("--key-path", default=str(Path.home() / ".ssh" / "id_ed25519_github_tesis"))
    parser.add_argument("--host", default="git@ssh.github.com")
    parser.add_argument("--set-local-ssh-command", action="store_true")
    parser.add_argument("--test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    key_path = Path(args.key_path).expanduser()

    print("[GIT-TRANSPORT] Diagnóstico de transporte")
    print(f"- Branch: {get_git_value(['branch', '--show-current']) or 'n/a'}")
    print(f"- Remote origin: {get_git_value(['remote', 'get-url', 'origin']) or 'n/a'}")
    print(f"- core.sshCommand: {get_git_value(['config', '--local', '--get', 'core.sshCommand']) or 'n/a'}")
    print(f"- Key path: {key_path}")

    if args.set_local_ssh_command:
        if not key_path.exists():
            print(f"[ERROR] No existe la llave: {key_path}")
            return 1
        result = configure_repo_ssh_command(key_path)
        if result.returncode != 0:
            print("[ERROR] No se pudo configurar core.sshCommand")
            print(result.stderr.strip())
            return 1
        print("[OK] core.sshCommand local configurado.")

    if args.test:
        if not key_path.exists():
            print(f"[ERROR] No existe la llave para prueba: {key_path}")
            return 1
        ok, output = test_ssh_connection(key_path, args.host)
        if ok:
            print("[OK] Autenticación SSH válida.")
            if output:
                print(output)
            return 0
        print("[ERROR] Falló autenticación SSH.")
        if output:
            print(output)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
