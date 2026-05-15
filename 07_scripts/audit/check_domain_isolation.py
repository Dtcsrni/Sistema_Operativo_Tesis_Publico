import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import yaml

def check_domain_conflicts():
    print("[CHECK] Validando consistencia de polticas de dominio...")
    root = Path(".")
    inference_path = root / "manifests/domains/edge/inference_policy.yaml"
    iot_path = root / "manifests/domains/edge/iot_policy.yaml"

    if not inference_path.exists() or not iot_path.exists():
        print("[FAIL] Faltan manifiestos de dominio.")
        return False

    with open(inference_path) as f:
        inference = yaml.safe_load(f)
    with open(iot_path) as f:
        iot = yaml.safe_load(f)

    # Check for hardware collision
    inf_hardware = inference.get('hardware', {}).get('acceleration', {}).get('device')
    iot_hardware = iot.get('hardware', {}).get('acceleration', {}).get('device')

    if inf_hardware == iot_hardware and inf_hardware is not None:
        print(f"[FAIL] Conflicto de hardware: Ambos dominios intentan acceder a {inf_hardware}")
        return False
    
    # Check for network isolation
    if inference['domain']['network']['internet_access'] or iot['domain']['network']['internet_access']:
        print("[WARNING] Uno de los dominios tiene acceso a internet habilitado (No recomendado en B1).")

    print("[SUCCESS] Polticas de dominio consistentes y aisladas.")
    return True

if __name__ == "__main__":
    if not check_domain_conflicts():
        sys.exit(1)
