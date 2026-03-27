import subprocess
import sys
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]

AUDITS = [
    {
        "name": "Integridad del Sistema",
        "script": "07_scripts/guardrails.py",
        "args": ["--verify"],
        "critical": True,
        "description": "Verifica que los archivos protegidos no hayan sido alterados sin autorización."
    },
    {
        "name": "Audit Ledger IA",
        "script": "07_scripts/verify_ledger.py",
        "args": [],
        "critical": True,
        "description": "Verifica la integridad criptográfica y la cadena de bloques del Ledger de conversaciones."
    },
    {
        "name": "Cadena de Bitácoras",
        "script": "07_scripts/verify_bitacora_chain.py",
        "args": [],
        "critical": True,
        "description": "Asegura que cada bitácora de sesión esté vinculada a la anterior mediante su hash."
    },
    {
        "name": "Escaneo de Secretos",
        "script": "07_scripts/secret_scanner.py",
        "args": [],
        "critical": True,
        "description": "Busca credenciales o tokens expuestos en el código."
    },
    {
        "name": "Jerarquía de Tareas",
        "script": "07_scripts/verify_hierarchy.py",
        "args": [],
        "critical": False,
        "description": "Verifica que no se completen tareas padres si sus hijos están pendientes."
    },
    {
        "name": "Autoauditoría Documental",
        "script": "07_scripts/document_audit.py",
        "args": [],
        "critical": False,
        "description": "Verifica la presencia de referencias globales y bloques de pre-checks."
    },
    {
        "name": "Estándares Externos",
        "script": "07_scripts/verify_standards.py",
        "args": [],
        "critical": False,
        "description": "Verifica la alineación con marcos normativos (NIST, ISO, etc.)."
    }
]

def run_audit(audit):
    print(f"[RUNNING] {audit['name']}...")
    cmd = [sys.executable, str(ROOT / audit['script'])] + audit['args']
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
    
    success = result.returncode == 0
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    
    return {
        "name": audit['name'],
        "success": success,
        "critical": audit['critical'],
        "output": f"{stdout.strip()}\n{stderr.strip()}".strip(),
        "timestamp": datetime.now().isoformat()
    }

def main():
    report = {
        "summary": {
            "total": len(AUDITS),
            "passed": 0,
            "failed": 0,
            "critical_failures": 0,
            "timestamp": datetime.now().isoformat()
        },
        "details": []
    }
    
    for audit in AUDITS:
        res = run_audit(audit)
        report["details"].append(res)
        if res["success"]:
            report["summary"]["passed"] += 1
        else:
            report["summary"]["failed"] += 1
            if res["critical"]:
                report["summary"]["critical_failures"] += 1
                
    # Save report
    report_path = ROOT / "00_sistema_tesis" / "config" / "security_report.json"
    if not report_path.parent.exists():
        report_path.parent.mkdir(parents=True, exist_ok=True)
        
    with open(report_path, "w", encoding='utf-8') as f:
        json.dump(report, f, indent=4)
        
    # Save to history
    history_dir = ROOT / "00_sistema_tesis" / "bitacora" / "audit_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    timestamp_fs = datetime.now().strftime("%Y-%m-%d_%H%M")
    history_path = history_dir / f"security_report_{timestamp_fs}.json"
    
    with open(history_path, "w", encoding='utf-8') as f:
        json.dump(report, f, indent=4)
    print(f"[AUDIT] Historial guardado: {history_path.relative_to(ROOT)}")
        
    # Print summary
    print("\n" + "="*40)
    print("RESUMEN DE AUDITORÍA DE SEGURIDAD")
    print("="*40)
    print(f"Total: {report['summary']['total']}")
    print(f"Pasados: {report['summary']['passed']}")
    print(f"Fallidos: {report['summary']['failed']}")
    print(f"FALLOS CRÍTICOS: {report['summary']['critical_failures']}")
    print("="*40)
    
    if report["summary"]["critical_failures"] > 0:
        print("[CRITICAL] Se detectaron violaciones de seguridad críticas. Build rechazado.")
        sys.exit(1)
    
    print("[OK] Auditoría completada con éxito.")
    sys.exit(0)

if __name__ == "__main__":
    main()
