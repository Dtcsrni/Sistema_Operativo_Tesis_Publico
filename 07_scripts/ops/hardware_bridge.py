#!/usr/bin/env python3
# ==============================================================================
# hardware_bridge.py - Puente de Generación y Validación de Hardware a Firmware
# ==============================================================================
# Lee el YAML de especificación del hardware, valida colisiones de pines GPIO,
# y exporta el archivo de cabecera 'config_hardware.h' para PlatformIO/C++.
# ==============================================================================

import os
import sys
import yaml
from pathlib import Path

def validate_pins(spec_data):
    """
    Verifica que ningún pin GPIO esté duplicado o asignado a múltiples funciones,
    lo cual causaría fallos de hardware en el ESP32.
    """
    assigned_pins = {}
    pines_seccion = spec_data.get("pines_fisicos", {})
    colisiones = []

    for component_name, pin_group in pines_seccion.items():
        if not isinstance(pin_group, dict):
            continue
        for function_name, pin_val in pin_group.items():
            if isinstance(pin_val, int):
                if pin_val in assigned_pins:
                    old_component, old_func = assigned_pins[pin_val]
                    colisiones.append(
                        f"¡COLISIÓN DE PIN GPIO {pin_val}! Asignado a: "
                        f"[{old_component}.{old_func}] y [{component_name}.{function_name}]"
                    )
                else:
                    assigned_pins[pin_val] = (component_name, function_name)
    
    return colisiones

def generate_header(spec_data, output_path):
    """
    Genera el archivo C++ de directivas de preprocesador config_hardware.h.
    """
    metadatos = spec_data.get("placa", {})
    pines_seccion = spec_data.get("pines_fisicos", {})
    
    header_content = [
        "// ==============================================================================",
        f"// config_hardware.h - Cabecera Autogenerada por hardware_bridge.py",
        "// ==============================================================================",
        f"// Placa de Desarrollo: {metadatos.get('modelo', 'Desconocida')}",
        f"// SoC/Microcontrolador: {metadatos.get('soc', 'Desconocido')}",
        f"// Enlace de Radio: {metadatos.get('enlace_radio', 'Desconocido')}",
        "// ATENCIÓN: No edites este archivo manualmente; edita heltec_wsl_v3_pins.yaml",
        "// ==============================================================================\n",
        "#ifndef CONFIG_HARDWARE_H",
        "#define CONFIG_HARDWARE_H\n",
        f"// --- Especificaciones del Host SoC ---",
        f"#define SO_PLACA_MODELO \"{metadatos.get('modelo', '')}\"",
        f"#define SO_PLACA_SOC \"{metadatos.get('soc', '')}\"",
        f"#define SO_PLACA_FREQ_MHZ {metadatos.get('frecuencia_mhz', 240)}",
        f"#define SO_PLACA_RADIO \"{metadatos.get('enlace_radio', '')}\"\n"
    ]

    for component_name, pin_group in pines_seccion.items():
        if not isinstance(pin_group, dict):
            continue
        header_content.append(f"// --- Pines para {component_name.upper()} ---")
        for function_name, pin_val in pin_group.items():
            if isinstance(pin_val, int):
                macro_name = f"PIN_{component_name.upper()}_{function_name.upper()}"
                header_content.append(f"#define {macro_name} {pin_val}")
            elif isinstance(pin_val, str):
                macro_name = f"CONFIG_{component_name.upper()}_{function_name.upper()}"
                header_content.append(f"#define {macro_name} \"{pin_val}\"")
        header_content.append("") # Separador
        
    header_content.append("#endif // CONFIG_HARDWARE_H")
    
    # Crear directorios si no existen
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(header_content) + "\n")
        
    print(f"[OK] Cabecera C++ autogenerada con éxito en: {output_path}")

def main():
    # Rutas por defecto del proyecto
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parents[1]
    
    yaml_path = repo_root / "00_sistema_tesis" / "config" / "heltec_wsl_v3_pins.yaml"
    output_path = repo_root / "04_implementacion" / "firmware" / "include" / "config_hardware.h"
    
    if len(sys.argv) > 1:
        yaml_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])
        
    if not yaml_path.exists():
        print(f"[ERROR] No se encuentra el archivo de especificación: {yaml_path}", file=sys.stderr)
        return 1
        
    print(f"[READ] Cargando especificación desde: {yaml_path}")
    with open(yaml_path, "r", encoding="utf-8") as f:
        try:
            spec_data = yaml.safe_load(f)
        except Exception as e:
            print(f"[ERROR] Error al decodificar YAML: {e}", file=sys.stderr)
            return 1
            
    # Validar consistencia física de pines
    print("[VALIDATE] Ejecutando verificación de colisiones GPIO...")
    colisiones = validate_pins(spec_data)
    if colisiones:
        print("[CRITICAL] Se detectaron errores físicos en la asignación de hardware:", file=sys.stderr)
        for col in colisiones:
            print(f"  - {col}", file=sys.stderr)
        print("[NO] El puente de hardware se detiene por seguridad física.", file=sys.stderr)
        return 2
    else:
        print("[OK] Verificación GPIO exitosa: 0 colisiones detectadas.")
        
    # Generar salida para el firmware
    generate_header(spec_data, output_path)
    return 0

if __name__ == "__main__":
    sys.exit(main())
