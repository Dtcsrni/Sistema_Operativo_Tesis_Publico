import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import http.server
import socketserver
import os

# Configuración
PORT = 8000
ROOT = Path(__file__).resolve().parent.parent.parent
DIRECTORY = ROOT / "06_dashboard" / "generado"

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

def main():
    if not DIRECTORY.exists():
        print(f"Error: No existe el directorio {DIRECTORY}")
        print("Ejecuta primero: python 07_scripts/build_all.py")
        return

    # Cambiar al directorio para que SimpleHTTPRequestHandler funcione correctamente
    os.chdir(DIRECTORY)
    
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print("\n" + "="*50)
        print("SERVIDO WEB SIOT ACTIVADO")
        print("="*50)
        print(f"URL: http://localhost:{PORT}")
        print(f"Directorio: {DIRECTORY}")
        print("Presiona Ctrl+C para detener el servidor.")
        print("="*50 + "\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido por el usuario.")

if __name__ == "__main__":
    main()
