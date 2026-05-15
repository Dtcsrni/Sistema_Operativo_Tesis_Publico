import os
import time
import threading
import math

class OrangePiLED:
    """
    Driver OPTIMIZADO para el control de los LEDs en la Orange Pi 5 Plus.
    Utiliza descriptores de archivo abiertos y Software PWM de alto rendimiento.
    """
    def __init__(self, color="green"):
        self.color = color
        self.base_path = self._discover_led(color)
        self.stop_event = threading.Event()
        self.thread = None
        self.current_pattern = "none"
        self.speed = 1.0
        self.fd = None
        
        if self.base_path:
            self._set_trigger("none")
            # Abrir el descriptor de archivo de forma persistente para maxima eficiencia
            brightness_path = os.path.join(self.base_path, "brightness")
            self.fd = os.open(brightness_path, os.O_WRONLY)
    
    def _discover_led(self, color):
        candidates = [f"{color}_led", f"{color}:status", f"status_{color}"]
        if color == "green": candidates.append("status_led")
        for name in candidates:
            path = f"/sys/class/leds/{name}"
            if os.path.exists(path): return path
        return None

    def _set_trigger(self, trigger):
        if not self.base_path: return
        try:
            with open(os.path.join(self.base_path, "trigger"), "w") as f:
                f.write(trigger)
        except: pass

    def set_brightness(self, value):
        """Escribe al hardware usando el descriptor abierto (ultra-eficiente)."""
        if self.fd is not None:
            os.write(self.fd, b"1" if value > 0.5 else b"0")
            os.lseek(self.fd, 0, 0)

    def _breath_loop(self):
        """Realiza un degradado suave (senoidal)."""
        t = 0
        period = 0.02 
        while not self.stop_event.is_set():
            duty = (math.sin(t) + 1) / 2
            if duty > 0:
                self.set_brightness(1)
                time.sleep(period * duty)
            if duty < 1:
                self.set_brightness(0)
                time.sleep(period * (1 - duty))
            t += 0.1 * self.speed

    def _pattern_loop(self, sequence):
        """Ejecuta una secuencia decodificable (ej. Morse o POST codes)."""
        while not self.stop_event.is_set():
            for on_t, off_t in sequence:
                if self.stop_event.is_set(): break
                self.set_brightness(1)
                time.sleep(on_t)
                self.set_brightness(0)
                time.sleep(off_t)
            time.sleep(1.5)

    def stop(self):
        self.stop_event.set()
        if self.thread: self.thread.join()
        self.set_brightness(0)
        self.stop_event.clear()
        self.current_pattern = "none"

    def static(self, on=True):
        self.stop()
        self.set_brightness(1 if on else 0)
        self.current_pattern = "static"

    def blink(self, frequency):
        if self.current_pattern == "blink" and hasattr(self, 'freq') and self.freq == frequency:
            return
        self.stop()
        self.freq = frequency
        if frequency <= 0: return
        def loop():
            p = 1.0 / frequency
            while not self.stop_event.is_set():
                self.set_brightness(1); time.sleep(p/2)
                self.set_brightness(0); time.sleep(p/2)
        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()
        self.current_pattern = "blink"

    def breathe(self, speed=1.0):
        """Activa o actualiza el modo respiro con DEGRADADO."""
        self.speed = speed
        if self.current_pattern == "breathe": return
        self.stop()
        self.thread = threading.Thread(target=self._breath_loop, daemon=True)
        self.thread.start()
        self.current_pattern = "breathe"

    def signal_code(self, sequence):
        """Emite un codigo de error especifico."""
        self.stop()
        self.thread = threading.Thread(target=self._pattern_loop, args=(sequence,), daemon=True)
        self.thread.start()
        self.current_pattern = "code"

    def __del__(self):
        if self.fd is not None:
            os.close(self.fd)
