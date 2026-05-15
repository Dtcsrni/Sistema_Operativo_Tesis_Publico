from __future__ import annotations

from pathlib import Path

from secret_scanner import PATTERNS, ScannerConfig, scan_repository, should_ignore_line


def _synthetic_openai_key() -> str:
    return "sk-" + ("A" * 31)


def test_secret_scanner_detects_openai_keys() -> None:
    sample = f"token={_synthetic_openai_key()}"
    assert "OpenAI API key" in PATTERNS
    assert should_ignore_line(sample) is False


def test_secret_scanner_ignores_example_lines() -> None:
    sample = f"example token: {_synthetic_openai_key()}"
    assert should_ignore_line(sample) is True


def test_secret_scanner_detects_secret_in_temp_root(tmp_path: Path) -> None:
    source = tmp_path / "app.py"
    source.write_text(f"token='{_synthetic_openai_key()}'\n", encoding="utf-8")

    result = scan_repository(ScannerConfig(root=tmp_path))

    assert result.ok is False
    assert result.findings[0].pattern == "OpenAI API key"
    assert result.findings[0].path == "app.py"
    assert result.findings[0].line == 1


def test_secret_scanner_prunes_excluded_dirs(tmp_path: Path) -> None:
    excluded = tmp_path / "runtime" / "models"
    excluded.mkdir(parents=True)
    (excluded / "weights.txt").write_text(f"token={_synthetic_openai_key()}\n", encoding="utf-8")

    result = scan_repository(ScannerConfig(root=tmp_path))

    assert result.ok is True
    assert result.stats.files_seen == 0


def test_secret_scanner_skips_large_files_by_default(tmp_path: Path) -> None:
    source = tmp_path / "large.txt"
    source.write_text("x" * 40 + f"\n{_synthetic_openai_key()}\n", encoding="utf-8")

    result = scan_repository(ScannerConfig(root=tmp_path, max_scan_bytes=20))

    assert result.ok is True
    assert result.stats.files_skipped == 1
