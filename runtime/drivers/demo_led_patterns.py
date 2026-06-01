import time
import os
import sys
# Añadir el directorio actual al path
sys.path.append(os.path.dirname(__file__))
from orange_pi_led import OrangePiLED

def run_demo():
    green = OrangePiLED("green")
    blue = OrangePiLED("blue")
    
    print("🎨 Iniciando Demostración de Patrones LED (Hardware Real)...")
    
    try:
        # CASO 1: MODO ECO (IDLE)
        print("\n[1/6] MODO ECO: Bajo consumo / Inactividad")
        print("      -> Verde con respiración lenta (0.2Hz)")
        green.pulse(0.2)
        blue.static(False)
        time.sleep(6)
        
        # CASO 2: STANDBY / OPERATIVO
        print("\n[2/6] STANDBY: Sistema OK, carga mínima")
        print("      -> Verde parpadeo normal (1Hz)")
        green.blink(1)
        time.sleep(6)
        
        # CASO 3: CARGA CPU ALTA
        print("\n[3/6] CARGA CPU: Procesamiento intensivo")
        print("      -> Verde parpadeo rápido (8Hz)")
        green.blink(8)
        time.sleep(6)
        
        # CASO 4: INFERENCIA NPU
        print("\n[4/6] INFERENCIA NPU: IA activa (RKLLM)")
        print("      -> Azul parpadeante")
        green.static(False) # Solo azul para destacar
        blue.blink(5)
        time.sleep(6)
        
        # CASO 5: CARGA TOTAL (CPU + NPU)
        print("\n[5/6] CARGA TOTAL: Nodo al límite")
        print("      -> Cian (Verde + Azul) parpadeo rápido")
        green.blink(10)
        blue.blink(10)
        time.sleep(6)
        
        # CASO 6: ALERTA TÉRMICA / ERROR
        print("\n[6/6] ALERTA: Temperatura crítica (>75°C)")
        print("      -> Estroboscopio (Alternancia G/A)")
        for _ in range(30):
            green.set_brightness(1)
            blue.set_brightness(0)
            time.sleep(0.05)
            green.set_brightness(0)
            blue.set_brightness(1)
            time.sleep(0.05)
        
        print("\n✅ Demostración finalizada. Restaurando LEDs...")
        
    except KeyboardInterrupt:
        print("\n🛑 Demostración interrumpida.")
    finally:
        green.stop()
        blue.stop()

if __name__ == "__main__":
    run_demo()
