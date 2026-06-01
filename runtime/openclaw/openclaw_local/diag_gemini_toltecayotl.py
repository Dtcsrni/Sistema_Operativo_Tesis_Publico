"""
diag_gemini_toltecayotl.py — Diagnóstico de Integración Gemini 3 Flash + MCT
Versión limpia sin emojis para compatibilidad con Windows.
"""
import sys
import os
from pathlib import Path

# Configurar ROOT para importar módulos locales
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from runtime.openclaw.openclaw_local.motor_calidad_toltecayotl import MotorDeCalidadToltecayotl
from runtime.openclaw.openclaw_local.inference import gemini_api_generate

def validar_integracion_gemini_toltecayotl():
    print("="*70)
    print("DIAGNOSTICO DE INTEGRACION: GEMINI 3 FLASH + MOTOR TOLTECAYOTL")
    print("="*70)
    
    # Prueba 1: Inferencia Pura
    pregunta = "Explica brevemente que es el Neltiliztli en la filosofia Tolteca."
    contexto_referencia = (
        "El Neltiliztli es el concepto de verdad o raiz de la existencia. "
        "En la Toltecayotl, buscar la verdad es buscar aquello que tiene raiz, "
        "aquello que es firme y no cambia caprichosamente."
    )
    
    print(f"\n[PASO 1] Solicitando inferencia a Gemini 3 Flash (Vertex AI)...")
    google_key = os.getenv("OPENCLAW_GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not google_key:
        print("FALLO DE CONFIGURACION: define OPENCLAW_GEMINI_API_KEY o GOOGLE_API_KEY.")
        return
    ok, respuesta = gemini_api_generate(
        prompt=pregunta, 
        model="gemini-3-flash-preview", 
        api_key=google_key,
        timeout_seconds=30
    )
    modelo = "gemini-3-flash-preview"
    
    if not ok:
        print(f"FALLO DE CONEXION: {respuesta}")
        return
    
    print(f"RESPUESTA RECIBIDA ({modelo}):")
    print("-" * 30)
    print(respuesta.strip())
    print("-" * 30)
    
    # Prueba 2: Auditoría de Calidad
    print(f"\n[PASO 2] Ejecutando Auditoria con el Motor de Calidad Toltecayotl (MCT)...")
    mct = MotorDeCalidadToltecayotl()
    
    try:
        informe = mct.evaluar_respuesta(
            id_de_solicitud="diag_test_manual",
            instruccion_original=pregunta,
            contexto_fuente=contexto_referencia,
            respuesta_ia=respuesta
        )
        
        print(f"AUDITORIA EXITOSA:")
        print(f"Puntaje Epistemico Final: {informe.puntaje_epistemico_final}/100")
        print(f"Fidelidad: {informe.fidelidad}")
        print(f"Densidad de Evidencia: {informe.densidad_de_evidencia}")
        print(f"Hallazgos detectados: {len(informe.hallazgos_de_auditoria)}")
        for h in informe.hallazgos_de_auditoria:
            print(f"   - {h}")
            
        if informe.puntaje_epistemico_final >= 85:
            print("\nRESULTADO FINAL: SISTEMA OPERATIVO CONECTADO Y CON ALTA FIDELIDAD.")
        else:
            print("\nRESULTADO FINAL: CONECTADO, PERO REQUIERE AJUSTE DE PROMPT (CALIDAD MEDIA).")
            
    except Exception as ex:
        print(f"ERROR EN EL MOTOR DE CALIDAD: {ex}")

if __name__ == "__main__":
    validar_integracion_gemini_toltecayotl()
