import os
import time
import sys
import re

def test_led_control():
    # Posibles rutas del LED de estado en Orange Pi 5 Plus
    possible_paths = [
        "/sys/class/leds/green_led",
        "/sys/class/leds/blue_led",
        "/sys/class/leds/status_led",
        "/sys/class/leds/green:status",
        "/sys/class/leds/user-led"
    ]
    
    led_path = None
    for path in possible_paths:
        if os.path.exists(path):
            led_path = path
            break
    
    if not led_path:
        print("❌ No se encontró un LED de estado controlable en /sys/class/leds/")
        print("Disponibles:", os.listdir("/sys/class/leds/") if os.path.exists("/sys/class/leds/") else "Ninguno")
        return

    print(f"✅ LED encontrado en: {led_path}")
    
    trigger_path = os.path.join(led_path, "trigger")
    brightness_path = os.path.join(led_path, "brightness")

    try:
        # Guardar trigger original (el que está entre corchetes)
        with open(trigger_path, "r") as f:
            content = f.read().strip()
            match = re.search(r"\[(.*?)\]", content)
            original_trigger = match.group(1) if match else "none"
        
        print(f"Triger actual: {original_trigger}. Cambiando a 'none' para control manual...")
        
        # Cambiar a control manual
        with open(trigger_path, "w") as f:
            f.write("none")
            
        print("Probando parpadeo (3 veces)...")
        for i in range(3):
            print(f"Iteración {i+1}: ON")
            with open(brightness_path, "w") as f:
                f.write("1")
            time.sleep(0.5)
            
            print(f"Iteración {i+1}: OFF")
            with open(brightness_path, "w") as f:
                f.write("0")
            time.sleep(0.5)
            
        # Restaurar trigger
        print(f"Restaurando trigger original: {original_trigger}")
        with open(trigger_path, "w") as f:
            f.write(original_trigger)
            
        print("✅ Prueba completada con éxito.")

    except PermissionError:
        print("❌ Error de permisos. Se requiere ejecutar como root (sudo).")
    except Exception as e:
        print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    test_led_control()
