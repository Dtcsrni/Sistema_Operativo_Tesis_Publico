import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "00_sistema_tesis" / "config" / "security_report.json"
OUTPUT_DIR = ROOT / "06_dashboard" / "generado" / "badges"

def generate_svg(label, status):
    color = "#10b981" if status.lower() == "passing" else "#ef4444"
    if status.lower() == "warning": color = "#f59e0b"
    
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="120" height="20">
  <linearGradient id="b" x2="0" y2="100%"><stop offset="0" stop-color="#bbb" stop-opacity=".1"/><stop offset="1" stop-opacity=".1"/></linearGradient>
  <mask id="a"><rect width="120" height="20" rx="3" fill="#fff"/></mask>
  <g mask="url(#a)">
    <path fill="#555" d="M0 0h60v20H0z"/>
    <path fill="{color}" d="M60 0h60v20H60z"/>
    <path fill="url(#b)" d="M0 0h120v20H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="30" y="15" fill="#010101" fill-opacity=".3">{label}</text>
    <text x="30" y="14">{label}</text>
    <text x="90" y="15" fill="#010101" fill-opacity=".3">{status}</text>
    <text x="90" y="14">{status}</text>
  </g>
</svg>"""

def main():
    if not REPORT_PATH.exists():
        print("[ERROR] No se encontró security_report.json")
        return

    with open(REPORT_PATH, "r", encoding='utf-8') as f:
        report = json.load(f)

    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    summary = report["summary"]
    details = {d["name"]: d for d in report["details"]}
    
    # Global Badge
    status = "passing" if summary["failed"] == 0 else "failing"
    if summary["critical_failures"] == 0 and summary["failed"] > 0:
         status = "warning"
    
    (OUTPUT_DIR / "security_status.svg").write_text(generate_svg("security", status), encoding='utf-8')
    
    # Specific Badges
    integrity_status = "passing" if details.get("Integridad del Sistema", {}).get("success") else "failing"
    (OUTPUT_DIR / "integrity.svg").write_text(generate_svg("integrity", integrity_status), encoding='utf-8')
    
    ledger_status = "passing" if details.get("Audit Ledger IA", {}).get("success") else "failing"
    (OUTPUT_DIR / "ledger.svg").write_text(generate_svg("ledger", ledger_status), encoding='utf-8')
    
    print(f"[OK] Badges generados en {OUTPUT_DIR.relative_to(ROOT)}")

if __name__ == "__main__":
    main()
