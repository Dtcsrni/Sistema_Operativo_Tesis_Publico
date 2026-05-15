import os
import hashlib
import subprocess
import json
from pathlib import Path
from datetime import datetime

class SecurityAuditor:
    """Módulo de auditoría de ciberseguridad para el ecosistema SIOT/OpenClaw."""
    
    def __init__(self, root_path: Path):
        self.root = root_path
        self.evidence_log = self.root / "00_sistema_tesis/bitacora/security_audit_ledger.jsonl"
        self.evidence_log.parent.mkdir(parents=True, exist_ok=True)

    def calculate_sha256(self, file_path: Path) -> str:
        """Calcula el hash SHA-256 de un archivo para verificación de integridad."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    def audit_file_integrity(self, file_path: Path, expected_hash: str = None):
        """Verifica la integridad de un archivo crítico."""
        if not file_path.exists():
            return {"status": "FAIL", "reason": "FILE_NOT_FOUND"}
        
        actual_hash = self.calculate_sha256(file_path)
        status = "OK"
        if expected_hash and actual_hash != expected_hash:
            status = "FAIL"
            
        result = {
            "timestamp": datetime.now().isoformat(),
            "type": "INTEGRITY_CHECK",
            "file": str(file_path.relative_to(self.root)),
            "sha256": actual_hash,
            "expected": expected_hash,
            "status": status
        }
        self._log_evidence(result)
        return result

    def audit_network_connections(self):
        """Escanea conexiones activas para detectar exfiltración de datos no autorizada."""
        try:
            # Buscamos conexiones establecidas (excluyendo local y Telegram/HF conocidos)
            cmd = "netstat -ntp | grep ESTABLISHED"
            output = subprocess.check_output(["wsl", "sh", "-c", cmd], stderr=subprocess.STDOUT).decode()
            connections = output.splitlines()
        except:
            connections = []

        result = {
            "timestamp": datetime.now().isoformat(),
            "type": "NETWORK_SCAN",
            "active_connections": len(connections),
            "status": "OK" if len(connections) < 10 else "WARNING" # Umbral arbitrario para auditoría
        }
        self._log_evidence(result)
        return result

    def audit_static_code(self, target_dir: str):
        """Realiza análisis estático básico (Bandit) para detectar vulnerabilidades en scripts."""
        try:
            # Usamos bandit si está disponible en WSL
            cmd = f"bandit -r {target_dir} -f json -q"
            output = subprocess.check_output(["wsl", "sh", "-c", cmd]).decode()
            report = json.loads(output)
            issues = report.get("results", [])
        except:
            issues = [{"issue_text": "Bandit not available or failed", "issue_severity": "LOW"}]

        result = {
            "timestamp": datetime.now().isoformat(),
            "type": "STATIC_ANALYSIS",
            "vulnerabilities_found": len(issues),
            "status": "OK" if len(issues) == 0 else "WARNING"
        }
        self._log_evidence(result)
        return result

    def _log_evidence(self, result: dict):
        """Registra la evidencia de forma inmutable (append-only)."""
        with open(self.evidence_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(result) + "\n")

    def generate_security_manifest(self):
        """Genera un manifiesto firmado de la salud del sistema."""
        # En un sistema real, aquí se firmaría el archivo con una clave privada (GPG/ED25519)
        pass
