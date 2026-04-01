from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from common import ROOT, load_yaml_json
from publication import load_publication_config, sanitize_text, validate_publication_output


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
TEXT_SUFFIXES = {
    ".appcache",
    ".css",
    ".csv",
    ".html",
    ".js",
    ".json",
    ".manifest",
    ".md",
    ".svg",
    ".txt",
    ".webmanifest",
    ".xml",
    ".yml",
    ".yaml",
}
PUBLIC_REPO_NAME = "Dtcsrni/Sistema_Operativo_Tesis_Publico"
PUBLIC_OPERATIONAL_PASSTHROUGH_PATHS = {
    "00_sistema_tesis/config/publicacion.yaml",
}
SEVERE_PRIVATE_LEAK_TOKENS = (
    "00_sistema_tesis/canon/events.jsonl",
    "00_sistema_tesis/canon/",
    "00_sistema_tesis/canon",
    "00_sistema_tesis/bitacora/log_conversaciones_ia.md",
    "00_sistema_tesis/bitacora/indice_fuentes_conversacion.md",
    "00_sistema_tesis/evidencia_privada/",
    "00_sistema_tesis/evidencia_privada",
    "00_sistema_tesis/config/agent_identity.json",
    "00_sistema_tesis/config/sign_offs.json",
)


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

        # Mantener el clon temporal alineado con el remoto evita rechazos non-fast-forward.
        fetched = run_command(["git", "fetch", "origin", branch], cwd=target_dir, check=False)
        if fetched.returncode == 0:
            remote_ref = run_command(["git", "rev-parse", f"origin/{branch}"], cwd=target_dir, check=False)
            if remote_ref.returncode == 0:
                run_command(["git", "checkout", "-B", branch, f"origin/{branch}"], cwd=target_dir)


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


def _sha256_bytes(payload: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(payload)
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


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def _render_payloads(source_map: dict[str, Path], *, sanitize: bool) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    publication = load_publication_config() if sanitize else {}
    for rel_path, source_path in source_map.items():
        if sanitize and rel_path in PUBLIC_OPERATIONAL_PASSTHROUGH_PATHS:
            payload = source_path.read_bytes()
        elif sanitize and _is_text_file(source_path):
            payload = sanitize_text(source_path.read_text(encoding="utf-8"), publication).encode("utf-8")
        else:
            payload = source_path.read_bytes()
        payloads[rel_path] = payload
    return payloads


def validate_sync_payloads(payloads: dict[str, bytes]) -> list[str]:
    errors: list[str] = []
    publication = load_publication_config()

    leaked_private_paths = sorted(rel_path for rel_path in payloads if _is_private_path(rel_path))
    for rel_path in leaked_private_paths:
        errors.append(f"La proyección pública incluye una ruta privada excluida: {rel_path}")

    for rel_path, payload in payloads.items():
        if rel_path.startswith(".git/"):
            errors.append(f"La proyección pública intenta publicar metadatos Git: {rel_path}")
            continue
        if Path(rel_path).suffix.lower() in TEXT_SUFFIXES:
            text = payload.decode("utf-8", errors="ignore")
            if rel_path in PUBLIC_OPERATIONAL_PASSTHROUGH_PATHS:
                try:
                    parsed = load_yaml_json(rel_path)
                    for item in parsed.get("sanitizacion", {}).get("redacciones_regex", []):
                        re.compile(item["patron"], re.IGNORECASE)
                except Exception as exc:  # pragma: no cover - defensive validation
                    errors.append(f"La configuración operativa pública es inválida en {rel_path}: {exc}")
                continue
            if rel_path.startswith("06_dashboard/publico/"):
                errors.extend(validate_publication_output(rel_path, payload, publication))
            else:
                for token in SEVERE_PRIVATE_LEAK_TOKENS:
                    if token in text:
                        errors.append(f"La proyección pública filtró una referencia privada en {rel_path}: {token}")

    pages_payload = payloads.get(".github/workflows/pages.yml")
    if not pages_payload:
        errors.append("Falta `.github/workflows/pages.yml` en la proyección pública.")
    else:
        pages_text = pages_payload.decode("utf-8", errors="ignore")
        if PUBLIC_REPO_NAME not in pages_text:
            errors.append("El workflow de Pages no restringe el despliegue al repo público derivado.")
        if "refs/heads/main" not in pages_text:
            errors.append("El workflow de Pages no fija `main` como rama de despliegue.")

    mkdocs_payload = payloads.get("mkdocs.yml")
    if not mkdocs_payload:
        errors.append("Falta `mkdocs.yml` en la proyección pública.")
    else:
        mkdocs_text = mkdocs_payload.decode("utf-8", errors="ignore")
        if "repo_url: [ruta_local_redactada]" in mkdocs_text:
            errors.append("`mkdocs.yml` redaccionó la URL del repo público en lugar de conservarla.")
        if f"repo_url: https://github.com/{PUBLIC_REPO_NAME}" not in mkdocs_text:
            errors.append("`mkdocs.yml` no apunta al repositorio público derivado.")
        if "Sistema_Operativo_Tesis_Posgrado" in mkdocs_text:
            errors.append("`mkdocs.yml` aún referencia el repo privado en la proyección pública.")

    return errors


def copy_selected_files(payloads: dict[str, bytes], target_dir: Path) -> None:
    for rel_path, payload in payloads.items():
        destination = target_dir / rel_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(payload)


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


def verify_sync(payloads: dict[str, bytes], target_dir: Path) -> None:
    source_inventory = {rel: _sha256_bytes(payload) for rel, payload in payloads.items()}
    target_inventory = _target_inventory(target_dir, set(payloads))
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


def write_sync_provenance(payloads: dict[str, bytes], target_dir: Path, branch: str, mode: str) -> None:
    payload = {
        "synced_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "sync_mode": mode,
        "source_file_count": len(payloads),
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
            json.dumps({rel: _sha256_bytes(blob) for rel, blob in payloads.items()}, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "private_exclusions": {
            "policy": "canonical_private_surfaces_filtered",
            "prefix_rules_count": len(PRIVATE_EXCLUDE_PREFIXES),
            "path_rules_count": len(PRIVATE_EXCLUDE_PATHS),
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
    parser.add_argument("--check", action="store_true", help="Verifica la proyección sin crear commit ni hacer push.")
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
        payloads = _render_payloads(source_map, sanitize=False)
    else:
        source_dir = ROOT
        source_map = _source_map_mirror(ROOT)
        payloads = _render_payloads(source_map, sanitize=True)

    validation_errors = validate_sync_payloads(payloads)
    if validation_errors:
        raise SystemExit(
            "SYNC-PUBLIC: la proyección pública incumple la política de sanitización:\n"
            + json.dumps(validation_errors, ensure_ascii=False, indent=2)
        )

    ensure_target_repo(target_dir, args.branch, args.repo_url)
    reset_content_dir(target_dir)
    copy_selected_files(payloads, target_dir)
    verify_sync(payloads, target_dir)
    write_sync_provenance(payloads, target_dir, args.branch, args.mode)
    write_security_notice(target_dir, contact_email=args.contact_email or _tesista_contact_default())

    if args.check:
        print("SYNC-PUBLIC: CHECK")
        print(f"SOURCE: {source_dir}")
        print(f"MODE: {args.mode}")
        print(f"TARGET: {target_dir}")
        print(f"FILES: {len(payloads)}")
        return 0

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
