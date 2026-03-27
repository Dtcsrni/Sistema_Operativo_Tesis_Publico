from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from common import ROOT, load_yaml_json


PRIVATE_EXCLUDE_PREFIXES = (
    "00_sistema_tesis/canon/",
    "00_sistema_tesis/bitacora/",
    "00_sistema_tesis/evidencia_privada/",
    "config/backups/",
)
PRIVATE_EXCLUDE_PATHS = {
    ".env",
    "00_sistema_tesis/ia_journal.json",
    "00_sistema_tesis/config/agent_identity.json",
    "00_sistema_tesis/config/sign_offs.json",
}


def run_command(cmd: list[str], cwd: Path, *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=check)


def ensure_target_repo(target_dir: Path, branch: str, repo_url: str = "") -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    git_dir = target_dir / ".git"
    if not git_dir.exists():
        run_command(["git", "init"], cwd=target_dir)
    current_branch = run_command(["git", "branch", "--show-current"], cwd=target_dir, check=False).stdout.strip()
    if not current_branch:
        run_command(["git", "checkout", "-b", branch], cwd=target_dir)
    elif current_branch != branch:
        switch = run_command(["git", "checkout", branch], cwd=target_dir, check=False)
        if switch.returncode != 0:
            run_command(["git", "checkout", "-b", branch], cwd=target_dir)
    if repo_url:
        existing = run_command(["git", "remote", "get-url", "origin"], cwd=target_dir, check=False)
        if existing.returncode == 0:
            if existing.stdout.strip() != repo_url:
                run_command(["git", "remote", "set-url", "origin", repo_url], cwd=target_dir)
        else:
            run_command(["git", "remote", "add", "origin", repo_url], cwd=target_dir)


def reset_content_dir(target_dir: Path) -> None:
    for child in target_dir.iterdir():
        if child.name == ".git":
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def _tracked_files(root: Path) -> list[str]:
    result = run_command(["git", "ls-files"], cwd=root)
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_map_bundle(source_dir: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(source_dir).as_posix()
        mapping[rel] = path
    return mapping


def _is_private_path(rel_path: str) -> bool:
    if rel_path in PRIVATE_EXCLUDE_PATHS:
        return True
    return any(rel_path.startswith(prefix) for prefix in PRIVATE_EXCLUDE_PREFIXES)


def _source_map_mirror(root: Path) -> dict[str, Path]:
    mapping: dict[str, Path] = {}
    for rel in _tracked_files(root):
        if _is_private_path(rel):
            continue
        path = root / rel
        if path.is_file():
            mapping[rel] = path
    return mapping


def copy_selected_files(source_map: dict[str, Path], target_dir: Path) -> None:
    for rel_path, source_path in source_map.items():
        destination = target_dir / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)


def _git_value(cwd: Path, args: list[str], default: str = "unknown") -> str:
    result = run_command(["git", *args], cwd=cwd, check=False)
    if result.returncode != 0:
        return default
    value = result.stdout.strip()
    return value or default


def _git_is_dirty(cwd: Path) -> bool:
    result = run_command(["git", "status", "--porcelain"], cwd=cwd, check=False)
    if result.returncode != 0:
        return True
    return bool(result.stdout.strip())


def _target_inventory(target_dir: Path, allowed_files: set[str]) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for path in sorted(target_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(target_dir).as_posix()
        if rel.startswith(".git/"):
            continue
        if rel not in allowed_files:
            continue
        inventory[rel] = _sha256(path)
    return inventory


def verify_sync(source_map: dict[str, Path], target_dir: Path) -> None:
    source_inventory = {rel: _sha256(path) for rel, path in source_map.items()}
    target_inventory = _target_inventory(target_dir, set(source_map))
    if source_inventory != target_inventory:
        missing = sorted(set(source_inventory) - set(target_inventory))
        extra = sorted(set(target_inventory) - set(source_inventory))
        changed = sorted(
            rel for rel in set(source_inventory).intersection(target_inventory) if source_inventory[rel] != target_inventory[rel]
        )
        details = {
            "missing_in_target": missing,
            "extra_in_target": extra,
            "changed_hash": changed,
        }
        raise SystemExit("SYNC-PUBLIC: desalineación detectada entre origen canónico y repo público:\n" + json.dumps(details, indent=2))


def _tesista_contact_default() -> str:
    tesista = load_yaml_json("00_sistema_tesis/config/tesista.json").get("tesista", {})
    emails = tesista.get("identidad_digital", {}).get("emails_autorizados", [])
    if emails:
        return str(emails[0]).strip()
    return "contacto_no_configurado"


def write_sync_provenance(source_map: dict[str, Path], target_dir: Path, branch: str, mode: str) -> None:
    payload = {
        "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sync_mode": mode,
        "source_file_count": len(source_map),
        "source_repo": {
            "remote_origin": _git_value(ROOT, ["remote", "get-url", "origin"]),
            "branch": _git_value(ROOT, ["branch", "--show-current"]),
            "commit": _git_value(ROOT, ["rev-parse", "HEAD"]),
        },
        "public_repo": {
            "branch": branch,
            "commit_before_sync": _git_value(target_dir, ["rev-parse", "HEAD"]),
        },
        "bundle_fingerprint": hashlib.sha256(
            json.dumps({rel: _sha256(path) for rel, path in source_map.items()}, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "private_exclusions": {
            "prefixes": list(PRIVATE_EXCLUDE_PREFIXES),
            "paths": sorted(PRIVATE_EXCLUDE_PATHS),
        },
    }
    (target_dir / "_sync_provenance.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_security_notice(target_dir: Path, *, contact_email: str) -> None:
    notice_path = target_dir / "NOTA_SEGURIDAD_Y_ACCESO.md"
    notice_path.write_text(
        "# Nota de Seguridad y Acceso\n\n"
        "Este repositorio es una **proyección pública controlada** del repositorio canónico privado.\n\n"
        "## Política de seguridad aplicada\n\n"
        "- Se excluyen superficies privadas: `canon/`, `bitacora/` y `evidencia_privada/`.\n"
        "- Se omiten artefactos de identidad/operación interna y secretos locales.\n"
        "- La sincronización se valida por hash antes de publicar.\n\n"
        "## Solicitud de detalles adicionales\n\n"
        "Si necesitas acceso a evidencia o contexto no público, solicita revisión directa al tesista:\n\n"
        f"- Contacto: `{contact_email}`\n\n"
        "La entrega de información adicional está sujeta a gobernanza, ética y autorización explícita del tesista.\n",
        encoding="utf-8",
    )


def has_changes(target_dir: Path) -> bool:
    status = run_command(["git", "status", "--porcelain"], cwd=target_dir)
    return bool(status.stdout.strip())


def main() -> int:
    parser = argparse.ArgumentParser(description="Sincroniza un clon filtrado o bundle público hacia un repositorio derivado.")
    parser.add_argument("--mode", choices=("bundle", "mirror"), default="mirror")
    parser.add_argument("--source-dir", default="06_dashboard/publico")
    parser.add_argument("--target-dir", default="../Sistema_Operativo_Tesis_Publico")
    parser.add_argument("--repo-url", default="")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--contact-email", default="")
    parser.add_argument("--commit-message", default="chore: actualizar proyeccion publica sanitizada")
    parser.add_argument("--allow-dirty", action="store_true")
    parser.add_argument("--push", action="store_true")
    args = parser.parse_args()

    if not args.allow_dirty and _git_is_dirty(ROOT):
        raise SystemExit(
            "SYNC-PUBLIC: árbol privado con cambios sin commit. "
            "Confirma y commitea primero para preservar sincronía exacta (o usa --allow-dirty explícitamente)."
        )

    target_dir = (ROOT / args.target_dir).resolve()
    if args.mode == "bundle":
        source_dir = (ROOT / args.source_dir).resolve()
        if not source_dir.exists():
            raise SystemExit(f"No existe el directorio fuente: {source_dir}")
        source_map = _source_map_bundle(source_dir)
    else:
        source_dir = ROOT
        source_map = _source_map_mirror(ROOT)

    ensure_target_repo(target_dir, args.branch, args.repo_url)
    reset_content_dir(target_dir)
    copy_selected_files(source_map, target_dir)
    verify_sync(source_map, target_dir)
    write_sync_provenance(source_map, target_dir, args.branch, args.mode)
    write_security_notice(target_dir, contact_email=args.contact_email or _tesista_contact_default())

    run_command(["git", "add", "-A"], cwd=target_dir)
    if has_changes(target_dir):
        run_command(["git", "commit", "-m", args.commit_message], cwd=target_dir)
        print("SYNC-PUBLIC: commit creado")
    else:
        print("SYNC-PUBLIC: sin cambios")

    if args.push:
        push_result = run_command(["git", "push", "-u", "origin", args.branch], cwd=target_dir, check=False)
        if push_result.returncode != 0:
            print(push_result.stdout.strip())
            print(push_result.stderr.strip())
            raise SystemExit("No fue posible hacer push al remoto público")
        print(f"SYNC-PUBLIC: push completado -> origin/{args.branch}")

    print(f"SOURCE: {source_dir}")
    print(f"MODE: {args.mode}")
    print(f"TARGET: {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
