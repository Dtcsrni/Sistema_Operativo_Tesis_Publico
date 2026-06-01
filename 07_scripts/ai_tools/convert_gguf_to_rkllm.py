import sys
from pathlib import Path
import os
import argparse

# Configurar rutas
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

try:
    from rkllm.api import RKLLM
except ImportError:
    print("[ERROR] rkllm-toolkit no encontrado.")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Convertidor GGUF -> RKLLM (Ahorro de RAM)")
    parser.add_argument("--model", type=str, required=True, help="Ruta al archivo .gguf")
    parser.add_argument("--output", type=str, required=True, help="Ruta de salida .rkllm")
    parser.add_argument("--target", type=str, default="rk3588", help="Plataforma destino")
    
    args = parser.parse_args()
    
    model = RKLLM()
    
    print(f"\n[1/3] Cargando GGUF (Modo bajo consumo): {args.model}")
    ret = model.load_gguf(args.model)
    if ret != 0:
        print("[ERROR] Fallo al cargar GGUF.")
        sys.exit(1)
        
    print(f"\n[2/3] Construyendo modelo RKLLM para {args.target}...")
    # Al usar GGUF ya cuantizado, el toolkit suele manejar la conversión de forma directa.
    # Nota: Algunos parámetros de build pueden variar según la versión del toolkit.
    ret = model.build(
        do_quantization=False, # Ya viene cuantizado en el GGUF
        optimization_level=1,
        target_platform=args.target,
        num_npu_core=3
    )
    if ret != 0:
        print("[ERROR] Fallo en la fase de build.")
        sys.exit(1)
        
    print(f"\n[3/3] Exportando a {args.output}...")
    output_abs = ROOT / args.output
    output_abs.parent.mkdir(parents=True, exist_ok=True)
    ret = model.export_rkllm(str(output_abs))
    
    if ret == 0:
        print(f"\n[SUCCESS] Conversión completada: {args.output}")
    else:
        print("[ERROR] Fallo al exportar.")
        sys.exit(1)

if __name__ == "__main__":
    main()
