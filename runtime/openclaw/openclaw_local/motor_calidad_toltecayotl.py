#!/usr/bin/env python3
"""
motor_calidad_toltecayotl.py — Motor de Calidad Toltecayotl (MCT)
Sistema de evaluación de calidad académica y epistémica para OpenClaw.
Implementa métricas de fidelidad (Neltiliztli), densidad de evidencia y consistencia lógica.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Importar utilidades locales y persona
try:
    from .persona import build_system_block
    from .epistemic import sha256_text
except ImportError:
    # Fallback para ejecución fuera del paquete
    def build_system_block(*args, **kwargs): return "Sistema de Calidad"
    def sha256_text(t): return "hash_placeholder"

logger = logging.getLogger("openclaw.calidad")

@dataclass
class InformeDeCalidadToltecayotl:
    """Informe detallado de la calidad de una respuesta bajo el estándar Toltecayotl."""
    id_de_solicitud: str
    marca_de_tiempo: str
    modelo_evaluado: str
    modelo_juez: str
    
    # Métricas MCT-V1 (Motor de Calidad Toltecayotl)
    fidelidad: float  # 0.0 - 1.0 (Grado de verdad/fidelidad al contexto)
    densidad_de_evidencia: float    # Relación de citaciones por afirmación
    consistencia_logica: float     # 0.0 - 1.0 (Coherencia interna del razonamiento)
    puntaje_epistemico_final: int   # 0 - 100 (Calificación ponderada final)
    
    # Detalle cualitativo
    hallazgos_de_auditoria: List[str]
    inconsistencias_detectadas: bool
    requiere_revision_humana: bool
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class MotorDeCalidadToltecayotl:
    """Motor soberano de evaluación de calidad epistémica integrado en Toltecayotl."""
    
    def __init__(self, directorio_de_logs: str = "runtime/openclaw/state/logs_calidad"):
        import os
        self.directorio_de_logs = Path(directorio_de_logs)
        self.directorio_de_logs.mkdir(parents=True, exist_ok=True)
        self.modelo_juez = os.getenv("OPENCLAW_MCT_LOCAL_JUDGE_MODEL", "heuristica_local_toltecayotl_v1").strip() or "heuristica_local_toltecayotl_v1"

    def evaluar_respuesta(
        self,
        id_de_solicitud: str,
        instruccion_original: str,
        contexto_fuente: str,
        respuesta_ia: str,
        dominio: str = "academico"
    ) -> InformeDeCalidadToltecayotl:
        """
        Ejecuta la auditoría completa de una respuesta bajo los estándares de la Tesis.
        """
        logger.info(f"Iniciando evaluación de calidad Toltecayotl para {id_de_solicitud}...")
        
        # 1. Evaluar Fidelidad y Lógica (Modelo como Juez)
        juez_ok, datos_del_juez = self._ejecutar_auditoria_juez(instruccion_original, contexto_fuente, respuesta_ia)
        
        if not juez_ok:
            logger.error("Fallo en la ejecución del juez de calidad Toltecayotl.")
            informe_error = self._crear_informe_de_error(id_de_solicitud, "Fallo en el juez de calidad")
            self._guardar_informe(informe_error)
            return informe_error

        # 2. Analizar Citaciones y Testimonios (Heurística Local)
        datos_de_citacion = self._analizar_testimonios_y_citas(respuesta_ia, contexto_fuente)
        
        # 3. Consolidar Informe de Calidad
        try:
            auditoria = json.loads(self._extraer_json(datos_del_juez))
        except Exception:
            auditoria = {"fidelidad": 0.5, "logica": 0.5, "hallazgos": ["Error parseando JSON del juez"]}

        fidelidad = auditoria.get("fidelidad", 0.0)
        logica = auditoria.get("logica", 0.0)
        densidad_citas = datos_de_citacion["densidad"]
        
        # Cálculo de Puntaje Epistémico (Pesos: 50% Fidelidad, 30% Evidencia, 20% Lógica)
        puntaje_evidencia = min(densidad_citas, 1.0) 
        puntaje_final = int((fidelidad * 50) + (puntaje_evidencia * 30) + (logica * 20))
        
        informe = InformeDeCalidadToltecayotl(
            id_de_solicitud=id_de_solicitud,
            marca_de_tiempo=datetime.now().isoformat(),
            modelo_evaluado="no_especificado", 
            modelo_juez=self.modelo_juez,
            fidelidad=fidelidad,
            densidad_de_evidencia=densidad_citas,
            consistencia_logica=logica,
            puntaje_epistemico_final=puntaje_final,
            hallazgos_de_auditoria=auditoria.get("hallazgos", []),
            inconsistencias_detectadas=fidelidad < 0.9,
            requiere_revision_humana=puntaje_final < 85
        )
        
        self._guardar_informe(informe)
        return informe

    def _ejecutar_auditoria_juez(self, prompt: str, contexto: str, respuesta: str) -> Tuple[bool, str, str]:
        """Ejecuta auditoría local conservadora, sin Gemini ni servicios cloud."""
        contexto_lower = contexto.lower()
        respuesta_lower = respuesta.lower()
        terminos_contexto = {
            token
            for token in contexto_lower.replace("\n", " ").split()
            if len(token) >= 6
        }
        terminos_respuesta = {
            token
            for token in respuesta_lower.replace("\n", " ").split()
            if len(token) >= 6
        }
        cobertura = len(terminos_contexto & terminos_respuesta) / max(len(terminos_contexto), 1)
        fidelidad = min(1.0, max(0.2, cobertura * 3.0))
        logica = 0.8 if len(respuesta.strip()) >= 120 else 0.5
        hallazgos = [
            "Auditoria local heuristica; no usa Gemini ni cloud pagado.",
            f"Cobertura lexica contexto-respuesta={cobertura:.3f}.",
        ]
        if fidelidad < 0.75:
            hallazgos.append("Cobertura baja; requiere revision humana.")
        payload = {
            "fidelidad": round(fidelidad, 3),
            "logica": round(logica, 3),
            "hallazgos": hallazgos,
            "es_valido": fidelidad >= 0.75,
        }
        return True, json.dumps(payload, ensure_ascii=False), self.modelo_juez

    def _analizar_testimonios_y_citas(self, respuesta: str, contexto: str) -> Dict[str, Any]:
        """Analiza la densidad de evidencia fáctica y citaciones en el texto."""
        import re
        citaciones = re.findall(r'\[[a-zA-Z0-9_-]{3,}\]', respuesta)
        citas_disponibles = re.findall(r'\[[a-zA-Z0-9_-]{3,}\]', contexto)
        conteo_afirmaciones = len([s for s in respuesta.split('.') if len(s.strip()) > 20])
        if not citas_disponibles:
            densidad = 1.0
        else:
            densidad = len(citaciones) / max(conteo_afirmaciones, 1)
        
        return {
            "total_citas": len(citaciones),
            "densidad": round(densidad, 3),
            "formato_valido": True
        }

    def _extraer_json(self, texto: str) -> str:
        """Extrae JSON aun si el juez lo envuelve en Markdown o texto auxiliar."""
        import re
        texto = texto.strip()
        bloque = re.search(r"```(?:json)?\s*(.*?)\s*```", texto, re.DOTALL | re.IGNORECASE)
        if bloque:
            return bloque.group(1).strip()
        inicio = texto.find("{")
        fin = texto.rfind("}")
        if inicio != -1 and fin != -1 and fin > inicio:
            return texto[inicio : fin + 1]
        return texto

    def _guardar_informe(self, informe: InformeDeCalidadToltecayotl):
        """Persiste el informe en el log diario de calidad."""
        archivo_log = self.directorio_de_logs / f"calidad_{datetime.now().date().isoformat()}.jsonl"
        with open(archivo_log, "a", encoding="utf-8") as f:
            f.write(json.dumps(informe.to_dict(), ensure_ascii=False) + "\n")

    def _crear_informe_de_error(self, id_solicitud: str, mensaje_error: str) -> InformeDeCalidadToltecayotl:
        return InformeDeCalidadToltecayotl(
            id_de_solicitud=id_solicitud,
            marca_de_tiempo=datetime.now().isoformat(),
            modelo_evaluado="error",
            modelo_juez=self.modelo_juez,
            fidelidad=0.0,
            densidad_de_evidencia=0.0,
            consistencia_logica=0.0,
            puntaje_epistemico_final=0,
            hallazgos_de_auditoria=[mensaje_error],
            inconsistencias_detectadas=True,
            requiere_revision_humana=True
        )

if __name__ == "__main__":
    motor = MotorDeCalidadToltecayotl()
    print("Motor de Calidad Toltecayotl inicializado con éxito.")
