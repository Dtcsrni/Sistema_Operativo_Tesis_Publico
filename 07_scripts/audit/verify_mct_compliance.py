import os
import re
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def verify_compliance(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_fre = "### [RAZONAMIENTO]" in content and "### [EVIDENCIA Y TRAZABILIDAD]" in content
    has_ese = "```json" in content and "\"integridad\"" in content
    
    return has_fre, has_ese

def main():
    print("MCT: Verificando cumplimiento de estándares FRE/ESE...")
    target_dirs = [
        ROOT / "00_sistema_tesis/decisiones",
        ROOT / "00_sistema_tesis/pendientes"
    ]
    
    compliance_report = []
    
    for directory in target_dirs:
        if not directory.exists(): continue
        for file in directory.glob("*.md"):
            fre, ese = verify_compliance(file)
            compliance_report.append({
                "file": str(file.relative_to(ROOT)),
                "FRE": fre,
                "ESE": ese
            })
    
    print("\nReporte de Cumplimiento:")
    for item in compliance_report:
        status = "[OK]" if item["FRE"] and item["ESE"] else "[FAIL]"
        print(f"{status} {item['file']} (FRE: {item['FRE']}, ESE: {item['ESE']})")

if __name__ == "__main__":
    main()
