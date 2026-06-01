#!/usr/bin/env python3
"""
run_tests_smart.py - Orquestador inteligente de pruebas para SIOT.
Ejecuta selectivamente pruebas de Python (pytest/unittest) y TypeScript (Mission Control)
según los archivos modificados, utilizando la lógica de test_impact_gate.py.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts" / "ops"))

import test_impact_gate as gate


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecutor inteligente de pruebas basado en impacto.")
    parser.add_argument("--all", "--force", action="store_true", help="Forzar la ejecución de toda la suite de pruebas.")
    parser.add_argument("--fast", action="store_true", help="Omitir pruebas marcadas como lenta/slow o de integración.")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Mostrar comandos a ejecutar sin ejecutarlos.")
    args = parser.parse_args()

    python_exe = sys.executable

    # 1. Ejecución completa forzada
    if args.all:
        print("[SMART TEST] Ejecución completa forzada de la suite de pruebas.")
        pytest_args = ["pytest", "-q", "-s"]
        if args.fast:
            pytest_args.extend(["-m", "not slow and not integration and not docker"])
        
        cmd = [python_exe, "-m"] + pytest_args
        print(f"  -> {' '.join(cmd)}")
        if args.dry_run:
            return 0
        
        res = subprocess.run(cmd, cwd=str(ROOT))
        return res.returncode

    # 2. Computar reporte de impacto incremental
    print("[SMART TEST] Calculando impacto incremental de cambios...")
    report = gate.build_report()
    
    changed = report.get("changed_paths", [])
    redundancy = report.get("redundancy_hint", "none")
    selected = report.get("selected_commands", [])

    print(f"  - Archivos modificados detectados: {len(changed)}")
    
    # 3. Verificar si hay un hit en la caché de impacto (redundancia)
    if redundancy == "previous_ok_same_impact" and not args.fast:
        print("[SMART TEST] [CACHE HIT] Los cambios actuales tienen el mismo impacto que la última prueba exitosa. Omitiendo ejecución.")
        return 0

    if not selected:
        print("[SMART TEST] No se detectaron pruebas específicas impactadas y no hay fallbacks. Finalizado.")
        return 0

    print(f"[SMART TEST] Se seleccionaron {len(selected)} comando(s) de prueba por impacto:")
    
    # 4. Ejecutar comandos recomendados
    failed = False
    ran_any = False
    
    for item in selected:
        cmd_id = item["id"]
        cmd_args = list(item["command"])
        reason = item.get("reason", "")
        
        # Normalizar el ejecutable de Python para usar el del entorno actual
        if cmd_args and cmd_args[0] in ("python", "python3"):
            cmd_args[0] = python_exe
        
        # Aplicar filtro fast si se solicita y el comando es pytest
        if args.fast and len(cmd_args) >= 3 and cmd_args[1] == "-m" and cmd_args[2] == "pytest":
            cmd_args.extend(["-m", "not slow and not integration and not docker"])
            
        print(f"\n[RUN TEST: {cmd_id}] debido a: {reason}")
        print(f"  Cmd: {' '.join(cmd_args)}")
        
        if args.dry_run:
            continue
            
        ran_any = True
        # Determinar el directorio de trabajo según la prueba
        cwd = ROOT
        if cmd_id.startswith("mission_control_") or cmd_args[0] in ("npm", "npx"):
            cwd = ROOT / "04_implementacion" / "control_mission"

        try:
            # shell=True es requerido en Windows para comandos como npm/npx
            use_shell = sys.platform == "win32" and cmd_args[0] in ("npm", "npx", "tsx")
            
            # Asegurar entorno de pruebas para Mission Control
            env = dict(os.environ)
            if cmd_id.startswith("mission_control_") or cmd_args[0] in ("npm", "npx"):
                env["NODE_ENV"] = "test"
                test_db = ".tmp/mission-control-test.db"
                env["DATABASE_PATH"] = test_db
                
                # Limpiar base de datos de prueba para evitar contaminación de estado (state leakage)
                db_file = ROOT / "04_implementacion" / "control_mission" / test_db
                for suffix in ("", "-wal", "-shm"):
                    f = Path(str(db_file) + suffix)
                    if f.exists():
                        try:
                            f.unlink()
                        except Exception as e:
                            print(f"[SMART TEST] No se pudo borrar {f.name}: {e}")
                
            res = subprocess.run(cmd_args, cwd=str(cwd), check=True, shell=use_shell, env=env)
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            print(f"\n[FAIL TEST: {cmd_id}] Error o fallo de ejecución: {exc}")
            failed = True
            break

    if args.dry_run:
        return 0

    # 5. Registrar el resultado en el historial de impacto
    if ran_any:
        history_path = Path(report["history_path"]) if "history_path" in report else gate.DEFAULT_HISTORY_PATH
        status = "failed" if failed else "ok"
        try:
            gate.append_history(ROOT / history_path, report, status)
            print(f"\n[SMART TEST] Resultado '{status}' registrado en el historial de impacto.")
        except Exception as e:
            print(f"\n[SMART TEST] [WARN] No se pudo guardar historial de impacto: {e}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
