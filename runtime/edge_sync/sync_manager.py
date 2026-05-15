import os
import time
import requests
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SyncManager:
    def __init__(self):
        self.hub_url = os.getenv("HUB_URL", "http://pc-hub:4000")
        self.local_buffer_dir = Path(os.getenv("BUFFER_DIR", "/app/buffer"))
        self.local_buffer_dir.mkdir(parents=True, exist_ok=True)
        self.sync_interval = int(os.getenv("SYNC_INTERVAL", "60"))
        self.running = True

    def get_pending_files(self):
        return sorted(list(self.local_buffer_dir.glob("*.jsonl")))

    def sync_file(self, file_path):
        logging.info(f"[*] Sincronizando {file_path.name} con el Hub...")
        try:
            with open(file_path, 'rb') as f:
                # Enviar al endpoint de ingesta del Dashboard/Docs
                response = requests.post(f"{self.hub_url}/api/ingest", files={'file': f}, timeout=10)
                if response.status_code == 200:
                    logging.info(f"[OK] {file_path.name} sincronizado.")
                    # Mover a carpeta de procesados o borrar
                    processed_dir = self.local_buffer_dir / "processed"
                    processed_dir.mkdir(exist_ok=True)
                    file_path.rename(processed_dir / file_path.name)
                    return True
                else:
                    logging.error(f"[FAIL] Error de Hub: {response.status_code}")
        except Exception as e:
            logging.error(f"[ERROR] No se pudo conectar con el Hub: {e}")
        return False

    def run(self):
        logging.info(f"SIOT Edge Sync iniciado. Intervalo: {self.sync_interval}s")
        while self.running:
            files = self.get_pending_files()
            if files:
                logging.info(f"Encontrados {len(files)} archivos pendientes.")
                for f in files:
                    if not self.sync_file(f):
                        break # Parar si falla la conexión
            else:
                logging.info("Sin datos pendientes de sincronización.")
            
            time.sleep(self.sync_interval)

if __name__ == "__main__":
    sync = SyncManager()
    sync.run()
