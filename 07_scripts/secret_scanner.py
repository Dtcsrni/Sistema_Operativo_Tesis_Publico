from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

TARGET = Path(__file__).resolve().parent / "audit" / "secret_scanner.py"


def _load_scanner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("_audit_secret_scanner", TARGET)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"No se pudo cargar {TARGET}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_scanner = _load_scanner()

PATTERNS = _scanner.PATTERNS
ScannerConfig = _scanner.ScannerConfig
SecretFinding = _scanner.SecretFinding
ScanResult = _scanner.ScanResult
ScanStats = _scanner.ScanStats
scan = _scanner.scan
scan_repository = _scanner.scan_repository
should_ignore_line = _scanner.should_ignore_line


if __name__ == "__main__":
    raise SystemExit(_scanner.main())
