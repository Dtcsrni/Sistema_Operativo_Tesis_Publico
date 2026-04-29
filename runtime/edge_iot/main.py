import time
import os
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EdgeGateway:
    def __init__(self):
        self.node_id = os.getenv("NODE_ID", "unknown_edge")
        self.hub_url = os.getenv("HUB_URL", "http://pc-hub:8080")
        self.running = True

    def poll_sensors(self):
        # Simulación de lectura de sensores (I2C/GPIO)
        # En producción, aquí se usaría smbus2 o RPi.GPIO
        data = {
            "timestamp": time.time(),
            "temp": 24.5,
            "humidity": 45.2,
            "npu_load": 0.1 # Simulado
        }
        return data

    def run(self):
        logging.info(f"SIOT Edge Gateway iniciado en nodo: {self.node_id}")
        logging.info(f"Hub central configurado en: {self.hub_url}")
        
        while self.running:
            try:
                metrics = self.poll_sensors()
                logging.info(f"Telemetría local: {json.dumps(metrics)}")
                
                # Aquí iría el envío al Hub o al Buffer local
                time.sleep(10)
            except KeyboardInterrupt:
                self.running = False

if __name__ == "__main__":
    gw = EdgeGateway()
    gw.run()
