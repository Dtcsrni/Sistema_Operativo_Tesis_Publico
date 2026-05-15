#!/usr/bin/env python3
"""
Checklist de Verificación - Sistema de Optimización de Créditos
Ejecuta este script para validar que todo está configurado correctamente
"""

import sys
import json
from pathlib import Path
from datetime import datetime

def check_file_exists(path: str, description: str) -> tuple[bool, str]:
    """Verifica si un archivo existe"""
    p = Path(path)
    status = "✅" if p.exists() else "❌"
    size = f" ({p.stat().st_size} bytes)" if p.exists() else ""
    return p.exists(), f"{status} {description}{size}"

def check_imports() -> tuple[bool, str]:
    """Verifica si las librerías críticas están disponibles"""
    try:
        import google.genai
        return True, "✅ google-genai instalado"
    except ImportError:
        return False, "❌ google-genai NO instalado"

def check_gcp_creds() -> tuple[bool, str]:
    """Verifica credenciales ADC"""
    creds_path = Path.home() / "AppData" / "Roaming" / "gcloud" / "application_default_credentials.json"
    if creds_path.exists():
        try:
            with open(creds_path) as f:
                data = json.load(f)
                if "type" in data:
                    return True, f"✅ ADC credentials válidas ({data.get('type', 'unknown')})"
        except:
            pass
    return False, "❌ ADC credentials NO encontradas o inválidas"

def check_config_structure() -> list:
    """Verifica estructura de directorios y archivos"""
    checks = []
    
    # Directorios
    dirs = [
        ("config/logs", "Directorio para logs"),
        ("runtime/providers", "Directorio de providers"),
        ("00_sistema_tesis/documentacion_sistema", "Directorio de documentación"),
    ]
    
    for dir_path, desc in dirs:
        exists, msg = check_file_exists(dir_path, desc)
        checks.append((exists, msg))
    
    # Archivos críticos
    files = [
        ("runtime/providers/cost_limiter.py", "Cost limiter"),
        ("runtime/providers/gemini.py", "Gemini provider"),
        ("runtime/providers/ollama_provider.py", "Ollama provider"),
        ("runtime/providers/__init__.py", "Provider factory"),
        ("07_scripts/monitor_costs.py", "Monitor de costos"),
        ("00_sistema_tesis/documentacion_sistema/ESTRATEGIA_OPTIMIZACION_CREDITOS.md", "Estrategia"),
        ("00_sistema_tesis/documentacion_sistema/GUIA_USO_RAPIDA.md", "Guía rápida"),
        ("00_sistema_tesis/documentacion_sistema/INTEGRACION_GEMINI_RESUMEN.md", "Integración resumen"),
    ]
    
    for file_path, desc in files:
        exists, msg = check_file_exists(file_path, desc)
        checks.append((exists, msg))
    
    return checks

def check_docker_setup() -> list:
    """Verifica configuración de Docker"""
    checks = []
    
    compose_file = Path("docker-compose.pc.yml")
    if compose_file.exists():
        with open(compose_file) as f:
            content = f.read()
            
        # Verificar que Gemini está comentado (modo default)
        has_gemini_disabled = "# - GOOGLE_GENAI_USE_VERTEXAI" in content or \
                               "# - GOOGLE_CLOUD_PROJECT" in content
        status = "✅" if has_gemini_disabled else "⚠️ "
        checks.append((has_gemini_disabled, f"{status} Gemini comentado (default seguro)"))
        
        # Verificar que opencode-executor está presente
        has_opencode = "opencode-executor" in content
        status = "✅" if has_opencode else "❌"
        checks.append((has_opencode, f"{status} Servicio opencode-executor configurado"))
    else:
        checks.append((False, "❌ docker-compose.pc.yml NO encontrado"))
    
    return checks

def main():
    """Ejecuta todas las verificaciones"""
    
    print("""
╔═══════════════════════════════════════════════════════════╗
║   ✅ CHECKLIST DE VERIFICACIÓN - SISTEMA DE COSTOS      ║
║      Sistema de Optimización de Créditos Gemini          ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    all_passed = True
    total_checks = 0
    passed_checks = 0
    
    # 1. Importaciones
    print("\n📦 IMPORTACIONES:")
    ok, msg = check_imports()
    print(f"   {msg}")
    total_checks += 1
    if ok:
        passed_checks += 1
    else:
        all_passed = False
    
    # 2. Credenciales GCP
    print("\n🔐 CREDENCIALES GCP:")
    ok, msg = check_gcp_creds()
    print(f"   {msg}")
    total_checks += 1
    if ok:
        passed_checks += 1
    else:
        print("   📍 Ejecuta: gcloud auth application-default login")
    
    # 3. Estructura de archivos
    print("\n📁 ESTRUCTURA DE ARCHIVOS:")
    config_checks = check_config_structure()
    for ok, msg in config_checks:
        print(f"   {msg}")
        total_checks += 1
        if ok:
            passed_checks += 1
        else:
            all_passed = False
    
    # 4. Configuración Docker
    print("\n🐳 CONFIGURACIÓN DOCKER:")
    docker_checks = check_docker_setup()
    for ok, msg in docker_checks:
        print(f"   {msg}")
        total_checks += 1
        if ok:
            passed_checks += 1
        else:
            all_passed = False
    
    # Resumen
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║   RESUMEN                                                ║
╚═══════════════════════════════════════════════════════════╝

   Verificaciones pasadas:  {passed_checks}/{total_checks}
   Estado:                  {'✅ TODO OK' if all_passed else '⚠️ REVISAR'}

    """)
    
    if all_passed:
        print("""
   🎉 SISTEMA LISTO PARA USAR
   
   Próximos pasos:
   1. Ejecutar diariamente: python 07_scripts/monitor_costs.py
   2. En código, usar: from runtime.providers import create_smart_hybrid
   3. Revisar logs en: config/logs/
        """)
    else:
        print("""
   ⚠️ REVISAR LOS ELEMENTOS MARCADOS CON ❌
   
   Si necesitas instalar google-genai:
   → pip install google-genai
   
   Si necesitas crear directorio de logs:
   → mkdir -p config/logs
        """)
    
    print("=" * 61)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
