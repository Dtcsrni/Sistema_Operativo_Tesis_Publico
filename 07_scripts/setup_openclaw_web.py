import os
import sys
import subprocess
from pathlib import Path

def run_cmd(cmd, cwd=None):
    print(f"[RUN] {cmd}")
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[ERR] {result.stderr}")
        return False
    return True

def main():
    root = Path(__file__).resolve().parents[1]
    venv_python = root / ".venv" / "bin" / "python.exe"
    
    if not venv_python.exists():
        # Try Windows style
        venv_python = root / ".venv" / "Scripts" / "python.exe"
        
    if not venv_python.exists():
        print(f"[ERR] No se encontró el entorno virtual en {root / '.venv'}")
        return 1

    # Get python version
    version_out = subprocess.check_output([str(venv_python), "--version"], text=True)
    print(f"[INFO] Detectado: {version_out.strip()}")
    
    is_new_python = "3.13" in version_out or "3.14" in version_out
    
    # Requirements
    reqs = ["jinja2", "uvicorn"]
    if is_new_python:
        print("[INFO] Usando perfiles de compatibilidad para Python 3.13+")
        reqs.extend(["fastapi<0.100", "pydantic<2.0"])
    else:
        reqs.append("fastapi")
        
    print(f"[RUN] Instalando dependencias: {', '.join(reqs)}")
    # Quote each requirement to avoid shell redirection issues with < or >
    quoted_reqs = [f'"{r}"' for r in reqs]
    cmd = f'"{venv_python}" -m pip install ' + " ".join(quoted_reqs)
    
    if run_cmd(cmd):
        print("[OK] Dependencias instaladas correctamente.")
        
        # Verify
        verify_cmd = f'"{venv_python}" -c "import fastapi; import pydantic; print(\'FastAPI \' + fastapi.__version__); print(\'Pydantic \' + pydantic.__version__)\"'
        run_cmd(verify_cmd)
        return 0
    else:
        print("[ERR] Falló la instalación de dependencias.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
