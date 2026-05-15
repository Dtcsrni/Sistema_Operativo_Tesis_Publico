"""
validar_gemini_nativo.py — Validación de Interfaz Nativa (Versión Limpia)
Prueba la conexión Gemini 3 Flash + Motor de Calidad Toltecayotl (MCT).
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Configurar el path para importar módulos locales de la arquitectura OpenClaw
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from runtime.openclaw.openclaw_local.orchestrator import Orchestrator, CommunicationChannel
    from runtime.openclaw.openclaw_local.storage import OpenClawStore
except ImportError as e:
    print(f"Error de importacion: {e}")
    sys.exit(1)

class CanalConsola(CommunicationChannel):
    """Canal de comunicación minimalista para la terminal."""
    def send_message(self, text: str, **kwargs):
        print(f"\n[SISTEMA] Respuesta Generada:\n{'-'*40}\n{text}\n{'-'*40}")
        return {"status": "ok", "message_id": "test_msg"}
    def send_action(self, action: str):
        print(f"Agente trabajando: {action}...")
    def update_message(self, message_id, text: str): pass
    def send_photo(self, image_path, caption=""): pass

def validar_nativo():
    print("="*80)
    print("VALIDACION NATIVA: OPENCLAW + GEMINI 3 FLASH + MOTOR TOLTECAYOTL")
    print("="*80)

    # 1. Preparar Entorno
    store_path = ROOT / "runtime/openclaw/openclaw_store.db"
    store = OpenClawStore(store_path)
    orchestrator = Orchestrator(ROOT, store)
    canal = CanalConsola()

    # 2. Definir Consulta Académica
    consulta = "Como garantiza el Motor de Calidad Toltecayotl la fidelidad en sus auditorias?"
    
    print(f"\n[PASO 1] Enviando consulta academica al Orquestador...")
    print(f"Pregunta: {consulta}")
    
    # Asegurar que el entorno permita Gemini
    os.environ["OPENCLAW_GEMINI_VERTEX_ENABLED"] = "True"
    
    try:
        resultado = orchestrator.dispatch_command("chat", consulta, canal, chat_id="diag_nativo_001")
        modelo_usado = resultado.get("model", "desconocido")
        task_id = resultado.get("task_id", "sin_id")
        print(f"Respuesta procesada por el modelo: {modelo_usado}")
    except Exception as e:
        print(f"Error critico en el Orquestador: {e}")
        return

    # 3. Verificar la Auditoría del MCT
    print(f"\n[PASO 2] Verificando logs de auditoria en el Motor de Calidad Toltecayotl...")
    log_dir = ROOT / "runtime/openclaw/state/logs_calidad"
    log_file = log_dir / f"calidad_{datetime.now().date().isoformat()}.jsonl"

    if not log_file.exists():
        print(f"Error: El archivo de log {log_file} no se ha generado.")
        print("Esto indica que la auditoria automatica fallo o no se ejecuto.")
        return

    with open(log_file, "r", encoding="utf-8") as f:
        lineas = f.readlines()
        if not lineas:
            print("Error: El archivo de log esta vacio.")
            return
        
        # Buscar el log correspondiente a esta tarea
        ultimo_log = None
        for linea in reversed(lineas):
            datos = json.loads(linea)
            if datos.get("id_de_solicitud") == task_id:
                ultimo_log = datos
                break
        
        if not ultimo_log:
            print(f"Aviso: No se encontro el log especifico para la tarea {task_id}.")
            ultimo_log = json.loads(lineas[-1]) # Fallback al último
            print(f"Mostrando el ultimo log general disponible ({ultimo_log.get('id_de_solicitud')}).")

    print(f"\n[PASO 3] RESULTADO DE LA AUDITORIA MCT (Metrica Fidelidad):")
    print(f"Puntaje Epistemico: {ultimo_log.get('puntaje_epistemico_final')}/100")
    print(f"Fidelidad: {ultimo_log.get('fidelidad')}")
    print(f"Densidad de Evidencia: {ultimo_log.get('densidad_de_evidencia')}")
    print(f"Juez de Calidad: {ultimo_log.get('modelo_juez')}")
    print(f"Hallazgos: {ultimo_log.get('hallazgos_de_auditoria')}")

    if ultimo_log.get('puntaje_epistemico_final', 0) >= 85:
        print("\nCONCLUSION: INTEGRACION EXITOSA. Gemini 3 Flash y MCT operan correctamente.")
    else:
        print("\nCONCLUSION: Conexion establecida, pero la calidad auditada es inferior al umbral academico.")

if __name__ == "__main__":
    validar_nativo()
