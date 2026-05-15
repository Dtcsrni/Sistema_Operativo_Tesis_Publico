import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import os
import json
import argparse

# Intentar importar el toolkit. 
# NOTA: Este script está diseñado para ejecutarse en el entorno donde rkllm-toolkit esté instalado.
try:
    from rkllm.api import RKLLM
except ImportError:
    RKLLM = None

def get_root():
    return Path(__file__).parent.parent.parent.absolute()

def create_calibration_data(output_path):
    """Crea un dataset de calibración básico para mejorar la precisión de la cuantización."""
    data = [{"input": q, "target": ""} for q in [
        "¿Qué es la resiliencia en sistemas operativos embebidos?",
        "Explica el funcionamiento de un ruteador adaptativo para IoT.",
        "Resume las ventajas de usar una NPU en el borde para inferencia de LLMs.",
        "¿Cómo se asegura la soberanía humana en sistemas asistidos por IA?",
        "Diferencia entre computación en la nube y computación en el borde (edge computing).",
        "Escribe un código simple en Python para calcular la latencia de una petición HTTP.",
        "¿Cuál es el impacto de la latencia en aplicaciones críticas de telemetría?",
        "Describe el protocolo DEC-0014 de colaboración humano-agente.",
        "¿Qué es el entrenamiento con cuantización para modelos de lenguaje?",
        "Explica el concepto de 'Reflective Phase' en una arquitectura agéntica.",
        "¿Cómo optimizar el uso de memoria CMA en el kernel Linux para RK3588?",
        "Genera un resumen científico sobre el estado del arte en IA soberana.",
        "¿Cuál es el rol de los agentes de IA en la investigación de posgrado?",
        "Define los niveles de auditoría CRÍTICO, ALTO y MEDIO en este sistema.",
        "Explica la importancia de la trazabilidad inmutable en la ciencia.",
        "¿Cómo funciona el mecanismo de atención en un Transformer?",
        "Describe la arquitectura del procesador RK3588 y su NPU de 6 TOPS.",
        "¿Qué es LoRaWAN y cómo se diferencia de LoRa P2P?",
        "Implementa un filtro de Kalman básico en pseudo-código para suavizar datos GPS.",
        "¿Cómo mitigar ataques de inyección de prompts en LLMs locales?",
        "Explica el concepto de 'Zero-copy' en la transferencia de datos a la NPU.",
        "¿Qué es un sistema operativo 'local-first'?",
        "Describe el proceso de cuantización post-entrenamiento (PTQ).",
        "¿Cómo afecta la temperatura en la generación de texto de un LLM?",
        "Analiza la eficiencia energética de la inferencia en el Edge vs Cloud.",
        "¿Qué es el protocolo MQTT y por qué es ideal para IoT?",
        "Explica la técnica de 'Speculative Decoding' para acelerar LLMs.",
        "¿Cómo gestionar el ciclo de vida de un agente de IA autónomo?",
        "Describe el uso de Docker para desplegar microservicios en ARM64.",
        "¿Qué importancia tiene la transparencia algorítmica en la tesis?"
    ]]
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Datos de calibración generados en: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Compilador/Convertidor oficial de modelos para NPU RK3588 (RKLLM).")
    parser.add_argument("--model", type=str, default="runtime/models/edge/qwen2.5_3b/", help="ID de HuggingFace o ruta local.")
    parser.add_argument("--output", type=str, default="runtime/models/edge/qwen2.5_3b_rkllm.rkllm", help="Ruta de salida del modelo .rkllm")
    parser.add_argument("--quant", type=str, default="w8a8", choices=["w8a8", "w4a16"], help="Tipo de cuantización (calidad vs velocidad).")
    parser.add_argument("--calibrate", action="store_true", default=True, help="Usar dataset de calibración para mejorar precisión.")
    
    args = parser.parse_args()
    ROOT = get_root()
    output_abs = ROOT / args.output
    
    print(f"=== Compilador RKLLM - Calidad Premium ===")
    print(f"Modelo origen: {args.model}")
    print(f"Salida:        {args.output}")
    print(f"Cuantización:  {args.quant}")
    print(f"Prioridad:     CALIDAD (W8A8 + Calibración)")
    
    if RKLLM is None:
        print("\n[ERROR] rkllm-toolkit no encontrado en este entorno.")
        print("Asegúrate de ejecutar este script en un entorno x86_64 Linux con el toolkit instalado.")
        print("Instalación sugerida: pip install rkllm-toolkit")
        sys.exit(1)

    model = RKLLM()
    
    # 1. Cargar modelo
    print(f"\n[1/3] Cargando modelo desde {args.model}...")
    # Si es un path local que no existe, intentamos cargar desde HF
    ret = model.load_huggingface(model=args.model)
    if ret != 0:
        print("[ERROR] Fallo al cargar el modelo.")
        sys.exit(1)

    # 2. Construcción con Calibración
    print(f"\n[2/3] Construyendo modelo con cuantización {args.quant}...")
    calib_file = ROOT / "07_scripts/calibration_data.json"
    if args.calibrate:
        if not calib_file.exists():
            create_calibration_data(calib_file)
        
        # Parámetros optimizados para CALIDAD
        # optimization_level 1 o 2 (si está disponible)
        # target_platform rk3588
        ret = model.build(
            do_quantization=True,
            optimization_level=1,
            quantized_dtype=args.quant.upper(),
            quantized_algorithm="normal",
            target_platform="rk3588",
            num_npu_core=3,
            dataset=str(calib_file),
            max_context=512
        )
    else:
        ret = model.build(do_quantization=True, optimization_level=1, quantized_dtype=args.quant)

    if ret != 0:
        print("[ERROR] Fallo en la fase de build.")
        sys.exit(1)

    # 3. Exportación
    print(f"\n[3/3] Exportando modelo a {args.output}...")
    output_abs.parent.mkdir(parents=True, exist_ok=True)
    ret = model.export_rkllm(str(output_abs))
    
    if ret == 0:
        print(f"\n[SUCCESS] Modelo compilado exitosamente: {args.output}")
        print(f"Tamaño final: {os.path.getsize(output_abs) / (1024*1024):.2f} MB")
    else:
        print("[ERROR] Fallo al exportar el modelo.")
        sys.exit(1)

if __name__ == "__main__":
    main()
