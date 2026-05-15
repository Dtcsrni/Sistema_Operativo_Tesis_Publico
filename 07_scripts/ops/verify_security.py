import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = ROOT / "00_sistema_tesis/bitacora/security_audit_ledger.jsonl"

def main():
    print("=== SIOT: Sistema de Verificación de Ciberseguridad (AUDIT-01) ===")
    print(f"Fecha: {datetime.now().isoformat()}")
    print("-" * 65)

    if not LEDGER_PATH.exists():
        print("[!] No se ha encontrado el Ledger de Seguridad. Ejecute el orquestador primero.")
        return

    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        entries = [json.loads(line) for line in f]

    # Resumen de Hallazgos
    print(f"[*] Total de auditorías registradas: {len(entries)}")
    
    integrity_checks = [e for e in entries if e["type"] == "INTEGRITY_CHECK"]
    net_scans = [e for e in entries if e["type"] == "NETWORK_SCAN"]
    
    print(f"[*] Verificaciones de integridad (SHA-256): {len(integrity_checks)}")
    print(f"[*] Escaneos de red: {len(net_scans)}")
    print("-" * 65)

    for entry in entries:
        ts = entry["timestamp"].split("T")[1][:8]
        status = entry["status"]
        status_icon = "✅" if status == "OK" else "❌"
        
        if entry["type"] == "INTEGRITY_CHECK":
            print(f"[{ts}] {status_icon} INTEGRIDAD: {entry['file'][:30]}...")
            print(f"         HASH: {entry['sha256']}")
        elif entry["type"] == "NETWORK_SCAN":
            print(f"[{ts}] {status_icon} RED: {entry['active_connections']} conexiones activas.")

    print("-" * 65)
    print("[OK] Auditoría finalizada. Todos los registros son inmutables en el Ledger.")

if __name__ == "__main__":
    main()
