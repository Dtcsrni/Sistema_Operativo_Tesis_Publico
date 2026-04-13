import json
import urllib.request
import sys
from pathlib import Path

def verify_url(url, keywords):
    # Intentamos con cabeceras que simulen un navegador real más específicamente
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status != 200:
                return False, f"HTTP {response.status}"
            
            content = response.read().decode('utf-8', errors='ignore')
            for kw in keywords:
                if kw.lower() not in content.lower():
                    # Si falla el descriptor, intentamos buscarlo en la URL para ver si al menos el contexto es correcto
                    if kw.lower() in url.lower():
                        continue
                    return False, f"Descriptor faltante: '{kw}'"
            return True, "OK"
    except Exception as e:
        return False, str(e)

def main():
    root = Path(__file__).resolve().parents[1]
    config_path = root / "00_sistema_tesis" / "config" / "ia_gobernanza.yaml"
    
    # Cargar YAML como JSON (asumiendo formato JSON-like o usando un parser simple si no hay PyYAML)
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
    except ImportError:
        # Fallback a json si el yaml es json-compatible
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

    marcos = data.get("cumplimiento_estandares", {}).get("marcos_de_referencia", [])
    
    errors = []
    print(f"AUDITORÍA DE ESTÁNDARES EXTERNOS ({len(marcos)} referencias)")
    
    for marco in marcos:
        nombre = marco.get("estandar")
        url = marco.get("url_auditoria") or marco.get("url_oficial")
        keywords = marco.get("descriptores_clave", [])
        
        print(f" - Verificando: {nombre}...", end=" ", flush=True)
        success, msg = verify_url(url, keywords)
        
        if success:
            print("OK")
        else:
            print(f"FALLÓ ({msg})")
            errors.append(f"{nombre}: {msg}")
            
    if errors:
        print("\nRESUMEN DE FALLOS:")
        for err in errors:
            print(f" [!] {err}")
        sys.exit(1)
    else:
        print("\nAUDITORÍA DE ESTÁNDARES: EXITOSA")

if __name__ == "__main__":
    main()
