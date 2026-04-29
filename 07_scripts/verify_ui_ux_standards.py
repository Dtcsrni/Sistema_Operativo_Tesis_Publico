import sys
import os
import re
from pathlib import Path

ROOT = Path(__file__).parent.parent
CSS_PATH = ROOT / "06_dashboard" / "generado" / "estilos.css"

STANDARDS = {
    "glassmorphism": [
        r"backdrop-filter:\s*blur\(",
        r"border:\s*1px\s*solid",
        r"background:\s*rgba"
    ],
    "contrast_aa": [
        # Check for bright text on dark background markers
        r"--text:\s*#[fF][0-9a-fA-F]{2,5}",
        r"--bg:\s*#0[0-9a-fA-F]{2,5}"
    ],
    "semantic_variety": [
        r"--warning",
        r"--danger",
        r"--purple",
        r"--info",
        r"--chartreuse"
    ]
}

def verify():
    if not CSS_PATH.exists():
        print(f"[FAIL] CSS not found at {CSS_PATH}")
        return 1
    
    content = CSS_PATH.read_text(encoding="utf-8")
    failures = []
    
    for category, patterns in STANDARDS.items():
        for pattern in patterns:
            if not re.search(pattern, content):
                failures.append(f"Missing {category} marker: {pattern}")
    
    if failures:
        print("[FAIL] UI/UX Standards not met:")
        for f in failures:
            print(f"  - {f}")
        return 1
    
    print("[OK] UI/UX Standards verified (Glassmorphism, Contrast, Semantic Variety)")
    return 0

if __name__ == "__main__":
    sys.exit(verify())
