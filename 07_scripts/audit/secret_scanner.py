from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Pattern

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))  # subdirectory siblings


# Patrones comunes de secretos: alto impacto, baja tasa de falsos positivos.
PATTERNS = {
    "GitHub PAT (Classic)": r"\bghp_[A-Za-z0-9]{36}\b",
    "GitHub PAT (Fine-grained)": r"\bgithub_pat_[A-Za-z0-9_]{82}\b",
    "GitHub OAuth token": r"\bgho_[A-Za-z0-9]{36}\b",
    "GitHub App token": r"\bghu_[A-Za-z0-9]{36}\b",
    "OpenAI API key": r"\bsk-[A-Za-z0-9]{20,}\b",
    "Google API key": r"\bAIza[0-9A-Za-z\-_]{35}\b",
    "AWS Access Key ID": r"\bAKIA[0-9A-Z]{16}\b",
    "Slack token": r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b",
    "Telegram bot token": r"\b[0-9]{8,12}:[A-Za-z0-9_-]{30,}\b",
    "JWT token": r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]{10,}\.[A-Za-z0-9._-]{10,}\b",
    "Private key block": r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----",
    "Anthropic API key": r"\bsk-ant-api[0-9a-zA-Z\-_]{70,}\b",
    "HuggingFace token": r"\bhf_[A-Za-z0-9]{34}\b",
    "Supabase Token": r"\bsbp_[0-9a-fA-F]{40}\b",
    "Convex Deploy Key": r"\bprod:[a-zA-Z0-9_\-]{20,}\b",
    "Ngrok Token": r"\b[0-9a-zA-Z]{40,}_[0-9a-zA-Z]{20,}\b",
}

DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "runtime/models",
    "runtime/drivers",
    "runtime/temp_ingest",
    "06_dashboard/generado",
    "06_dashboard/publico",
    "node_modules",
    "scratch",
}
EXCLUDE_DIRS = DEFAULT_EXCLUDE_DIRS
EXCLUDE_FILES = {
    ".env.example",
    "common.py",
    "sign_off.py",
}
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".pyc",
    ".exe",
    ".zip",
    ".tar",
    ".gz",
    ".pdf",
    ".rkllm",
    ".so",
    ".sqlite",
    ".db",
    ".whl",
    ".pkl",
    ".map",
}
SAFE_LINE_MARKERS = (
    "example",
    "ejemplo",
    "placeholder",
    "dummy",
    "sample",
    "test_",
    "fake",
    "redacted",
    "<token>",
    "<secret>",
)
DEFAULT_MAX_SCAN_BYTES = int(os.getenv("SIOT_SECRET_SCANNER_MAX_BYTES", "2000000"))
MAX_SCAN_BYTES = DEFAULT_MAX_SCAN_BYTES


@dataclass(frozen=True)
class SecretFinding:
    pattern: str
    path: str
    line: int

    def format_legacy(self) -> str:
        return f"{self.pattern} encontrado en: {self.path} (linea {self.line})"


@dataclass
class ScanStats:
    files_seen: int = 0
    files_scanned: int = 0
    files_skipped: int = 0
    bytes_scanned: int = 0
    warnings: list[str] = field(default_factory=list)


@dataclass
class ScanResult:
    root: str
    findings: list[SecretFinding]
    stats: ScanStats

    @property
    def ok(self) -> bool:
        return not self.findings


@dataclass(frozen=True)
class ScannerConfig:
    root: Path
    exclude_dirs: frozenset[str] = frozenset(DEFAULT_EXCLUDE_DIRS)
    exclude_files: frozenset[str] = frozenset(EXCLUDE_FILES)
    binary_suffixes: frozenset[str] = frozenset(BINARY_SUFFIXES)
    max_scan_bytes: int = DEFAULT_MAX_SCAN_BYTES
    include_large: bool = False


def should_ignore_line(line: str) -> bool:
    lowered = line.lower()
    return any(marker in lowered for marker in SAFE_LINE_MARKERS)


def _compile_patterns(patterns: dict[str, str]) -> dict[str, Pattern[str]]:
    return {name: re.compile(pattern) for name, pattern in patterns.items()}


COMPILED_PATTERNS = _compile_patterns(PATTERNS)


def _normalize_rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_excluded_dir(rel_dir: str, name: str, config: ScannerConfig) -> bool:
    candidate = f"{rel_dir}/{name}".strip("/")
    return name in config.exclude_dirs or candidate in config.exclude_dirs


def _iter_candidate_files(config: ScannerConfig, stats: ScanStats) -> Iterable[Path]:
    root = config.root.resolve()
    git_files = _git_candidate_files(root)
    if git_files is not None:
        for rel_path in git_files:
            path = root / rel_path
            stats.files_seen += 1
            if _should_skip_file(path, rel_path.as_posix(), config):
                stats.files_skipped += 1
                continue
            yield path
        return

    for current_root, dirs, files in os.walk(root, followlinks=False):
        current = Path(current_root)
        rel_dir = _normalize_rel(current, root) if current != root else ""
        dirs[:] = [
            name
            for name in dirs
            if not _is_excluded_dir(rel_dir, name, config)
            and not (current / name).is_symlink()
        ]
        for file_name in files:
            path = current / file_name
            stats.files_seen += 1
            if path.is_symlink():
                stats.files_skipped += 1
                continue
            rel_path = _normalize_rel(path, root)
            if _should_skip_file(path, rel_path, config):
                stats.files_skipped += 1
                continue
            yield path


def _git_candidate_files(root: Path) -> list[Path] | None:
    if not (root / ".git").exists():
        return None
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return [Path(item) for item in completed.stdout.decode("utf-8", errors="ignore").split("\0") if item]


def _should_skip_file(path: Path, rel_path: str, config: ScannerConfig) -> bool:
    if not path.is_file():
        return True
    if path.is_symlink():
        return True
    if path.name in config.exclude_files:
        return True
    if path.suffix.lower() in config.binary_suffixes:
        return True
    return any(rel_path == exc or rel_path.startswith(f"{exc}/") for exc in config.exclude_dirs)


def _scan_file(
    path: Path,
    root: Path,
    config: ScannerConfig,
    patterns: dict[str, Pattern[str]],
    stats: ScanStats,
) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    rel_path = _normalize_rel(path, root)
    try:
        size = path.stat().st_size
        if size > config.max_scan_bytes and not config.include_large:
            stats.files_skipped += 1
            return findings
        stats.files_scanned += 1
        stats.bytes_scanned += size
        matched_patterns: set[str] = set()
        is_env_file = ".env" in path.name and not path.name.endswith(".example") and not path.name.endswith(".template")
        with path.open("r", encoding="utf-8", errors="ignore") as handle:
            for line_number, line_text in enumerate(handle, start=1):
                if should_ignore_line(line_text):
                    continue
                if is_env_file:
                    line_stripped = line_text.strip()
                    if line_stripped and not line_stripped.startswith("#") and "=" in line_stripped:
                        _, val = line_stripped.split("=", 1)
                        val = val.strip(' "\'')
                        # Heurística: longitud >= 24, sin espacios, sin slashes, sin puntos, alta variedad de caracteres, sin sintaxis bash
                        if len(val) >= 24 and " " not in val and "/" not in val and "." not in val and len(set(val)) > 10 and "$" not in val and "{" not in val:
                            findings.append(SecretFinding("Heurística de alto riesgo (.env real trackeado)", rel_path, line_number))
                            continue
                for name, pattern in patterns.items():
                    if name in matched_patterns:
                        continue
                    if pattern.search(line_text):
                        findings.append(SecretFinding(name, rel_path, line_number))
                        matched_patterns.add(name)
                if len(matched_patterns) == len(patterns) and not is_env_file:
                    break
    except Exception as exc:  # pragma: no cover - defensive path for OS races.
        stats.warnings.append(f"No se pudo escanear {path}: {exc}")
    return findings


def scan_repository(config: ScannerConfig | None = None) -> ScanResult:
    effective_config = config or ScannerConfig(root=Path(__file__).resolve().parents[2])
    root = effective_config.root.resolve()
    stats = ScanStats()
    findings: list[SecretFinding] = []
    for path in _iter_candidate_files(effective_config, stats):
        findings.extend(_scan_file(path, root, effective_config, COMPILED_PATTERNS, stats))
    return ScanResult(root=str(root), findings=findings, stats=stats)


def scan() -> list[str]:
    return [finding.format_legacy() for finding in scan_repository().findings]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Escanea secretos comunes en el repositorio.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--json", action="store_true", help="Emite resultado estructurado JSON.")
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_SCAN_BYTES)
    parser.add_argument("--include-large", action="store_true")
    parser.add_argument("--exclude-dir", action="append", default=[])
    return parser.parse_args(argv)


def _build_config(args: argparse.Namespace) -> ScannerConfig:
    return ScannerConfig(
        root=args.root,
        exclude_dirs=frozenset(DEFAULT_EXCLUDE_DIRS | set(args.exclude_dir)),
        max_scan_bytes=args.max_bytes,
        include_large=args.include_large,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    result = scan_repository(_build_config(args))
    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print("[PROCESS] Escaneando secretos en el repositorio...")
        for warning in result.stats.warnings:
            print(f"[WARN] {warning}")
        if result.findings:
            print("\n[CRITICAL ERROR] Se encontraron potenciales secretos en el código:")
            for finding in result.findings:
                print(f"  - {finding.format_legacy()}")
            print(
                "\nPOR SEGURIDAD, EL BUILD SE HA DETENIDO. "
                "Limpie los secretos y use variables de entorno (.env)"
            )
        else:
            print("[OK] No se detectaron secretos evidentes.")
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
