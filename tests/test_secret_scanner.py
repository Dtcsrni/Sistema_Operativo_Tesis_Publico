from __future__ import annotations

from secret_scanner import PATTERNS, should_ignore_line


def test_secret_scanner_detects_openai_keys() -> None:
    sample = "token=sk-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    assert "OpenAI API key" in PATTERNS
    assert should_ignore_line(sample) is False


def test_secret_scanner_ignores_example_lines() -> None:
    sample = "example token: sk-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    assert should_ignore_line(sample) is True
