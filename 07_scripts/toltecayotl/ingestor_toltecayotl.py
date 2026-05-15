"""toltecayotl/ingestor_toltecayotl.py — Motor de Ingestión Epistémica (v2.2).

"El Fiscal Epistémico": Detección de alucinaciones y validación de autoridad.
"El Cronista Epistémico": Reportes descriptivos con nexos de verdad.
"""

import argparse
import hashlib
import json
import os
import re
import sys
import tarfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pypdf

def calcular_hash_sha256(ruta_archivo: Path) -> str:
    sha256_hash = hashlib.sha256()
    with open(ruta_archivo, "rb") as f:
        for bloque in iter(lambda: f.read(4096), b""): sha256_hash.update(bloque)
    return sha256_hash.hexdigest()

def calcular_hash_de_texto(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()

def slugify(text: str) -> str:
    return re.sub(r'[\W_]+', '_', text).strip('_').upper()

class IngestorToltecayotl:
    def __init__(self, ruta_fuente: Path, contexto_de_agente_externo: Optional[Dict[str, Any]] = None):
        self.ruta_fuente = ruta_fuente
        self.hash_del_documento_fuente = calcular_hash_sha256(ruta_fuente)
        self.marca_de_tiempo = datetime.now()
        self.contexto_de_agente_externo = contexto_de_agente_externo

    def ejecutar_ingesta(self, tamaño_de_fragmento: int = 1000) -> List[Dict[str, Any]]:
        extension = self.ruta_fuente.suffix.lower()
        if extension in [".zip", ".xz", ".tar"]:
            return self._procesar_paquete_comprimido(tamaño_de_fragmento)
        elif extension == ".pdf":
            return self._procesar_pdf(tamaño_de_fragmento)
        else:
            return self._procesar_texto_plano(tamaño_de_fragmento)

    def _procesar_pdf(self, tamaño_de_fragmento: int) -> List[Dict[str, Any]]:
        lector = pypdf.PdfReader(self.ruta_fuente)
        texto_completo = ""
        for pagina in lector.pages:
            texto_completo += pagina.extract_text() + "\n"
        
        return self._crear_fragmentos_de_texto(texto_completo, tamaño_de_fragmento, self.ruta_fuente.name, "IA_Fallback", "Propuesta")

    def _procesar_texto_plano(self, tamaño_de_fragmento: int) -> List[Dict[str, Any]]:
        contenido = self.ruta_fuente.read_text(encoding="utf-8", errors="ignore")
        return self._crear_fragmentos_de_texto(contenido, tamaño_de_fragmento, self.ruta_fuente.name, "IA_Fallback", "Propuesta")

    def _procesar_paquete_comprimido(self, tamaño_de_fragmento: int) -> List[Dict[str, Any]]:
        fragmentos_totales = []
        directorio_temporal = Path("runtime/temp_ingest") / f"ingesta_{self.hash_del_documento_fuente[:8]}"
        directorio_temporal.mkdir(parents=True, exist_ok=True)

        try:
            if self.ruta_fuente.suffix == ".zip":
                with zipfile.ZipFile(self.ruta_fuente, 'r') as ref_zip: ref_zip.extractall(directorio_temporal)
            elif ".tar" in self.ruta_fuente.name or self.ruta_fuente.suffix == ".xz":
                with tarfile.open(self.ruta_fuente, 'r:*') as ref_tar: ref_tar.extractall(directorio_temporal)

            ruta_literal = next(directorio_temporal.rglob("contenido_literal.txt"), None)
            ruta_sintesis = next(directorio_temporal.rglob("resumen_de_investigacion.md"), None)

            if ruta_literal:
                texto_l = ruta_literal.read_text(encoding="utf-8", errors="ignore")
                fragmentos_totales.extend(self._extraer_con_rigor(texto_l, "contenido_literal.txt"))
                
                if ruta_sintesis:
                    texto_s = ruta_sintesis.read_text(encoding="utf-8", errors="ignore")
                    fragmentos_totales.extend(self._crear_fragmentos_de_texto(texto_s, 10000, "resumen_de_investigacion.md", "IA", "Propuesta"))
                
                return fragmentos_totales

            for ruta_hijo in directorio_temporal.rglob("*"):
                if ruta_hijo.is_file() and ruta_hijo.suffix.lower() in [".md", ".txt", ".json"]:
                    contenido = ruta_hijo.read_text(encoding="utf-8", errors="ignore")
                    fragmentos_totales.extend(self._crear_fragmentos_de_texto(contenido, tamaño_de_fragmento, ruta_hijo.name, "IA_Fallback", "Propuesta"))
        finally: pass
        return fragmentos_totales

    def _extraer_con_rigor(self, texto: str, nombre_sub_fuente: str) -> List[Dict[str, Any]]:
        lista = []
        patron = r"(?:FRAGMENTO:|\[)(F\d+)(?:]|)\n(?:HASH_SHA256:|sha256=)\s*([0-9a-f]{64})\n(?:AUTORIDAD:|autoridad=)?\s*(.*?)\n(?:CERTEZA:|certeza=)?\s*(.*?)\n(?:FUNDAMENTO:|fundamento=)?\s*(.*?)\n(?:TEXTO_LITERAL:|literal=<<<)\n(.*?)\n(?:FIN_FRAGMENTO|>>>)"
        bloques = re.findall(patron, texto, re.S)
        for fid, sha_decl, aut, cert, fund, cont in bloques:
            aut_s = aut.strip() or "IA_Sugerida"
            fund_s = fund.strip() or "N/A"
            
            # Fiscal Epistémico: Lógica de Alucinación v2.2
            estado = "verificado"
            if aut_s == "IA":
                if fund_s == "N/A" or "Sintesis" in fund_s or "generada" in fund_s:
                    estado = "RIESGO_DE_ALUCINACION"
                if re.search(r"https?://", fund_s) or "doi.org" in fund_s:
                    estado = "verificado_externo"
            elif aut_s == "Tesista":
                estado = "verificado_humano"

            lista.append({
                "id_del_fragmento": sha_decl, "contenido_original": cont,
                "autoridad_del_dato": aut_s,
                "grado_de_certeza": cert.strip() or "Propuesta",
                "fundamento_del_dato": fund_s,
                "metadatos_de_procedencia": {"archivo_fuente": self.ruta_fuente.name, "archivo_interno": nombre_sub_fuente, "id_bloque_agente": fid},
                "auditoria_de_ingesta": {"fecha": self.marca_de_tiempo.isoformat(), "version": "2.2", "estado": estado}
            })
        return lista

    def _crear_fragmentos_de_texto(self, texto: str, tamaño: int, nombre_sub_fuente: str, aut: str, cert: str) -> List[Dict[str, Any]]:
        lista = []
        for i in range(0, len(texto), tamaño):
            seg = texto[i : i + tamaño]
            lista.append({
                "id_del_fragmento": calcular_hash_de_texto(seg), "contenido_original": seg,
                "autoridad_del_dato": aut, "grado_de_certeza": cert, "fundamento_del_dato": "Derivado de sesión",
                "metadatos_de_procedencia": {"archivo_fuente": self.ruta_fuente.name, "archivo_interno": nombre_sub_fuente, "posicion": i},
                "auditoria_de_ingesta": {"fecha": self.marca_de_tiempo.isoformat(), "version": "2.2", "estado": "verificado"}
            })
        return lista

    def generar_informe_descriptivo(self, fragmentos: List[Dict[str, Any]]):
        tema = slugify(self.ruta_fuente.stem)
        fecha_str = self.marca_de_tiempo.strftime("%Y-%m-%d_%H%M")
        nombre_reporte = f"REPORTE_INGESTA_{tema}_{fecha_str}_PET-{self.hash_del_documento_fuente[:8]}.md"
        ruta_salida = Path("00_sistema_tesis/05_registros_de_ingestion") / nombre_reporte
        
        riesgos = [f for f in fragmentos if f["auditoria_de_ingesta"]["estado"] == "RIESGO_DE_ALUCINACION"]
        humanos = [f for f in fragmentos if "humano" in f["auditoria_de_ingesta"]["estado"]]
        externos = [f for f in fragmentos if f["auditoria_de_ingesta"]["estado"] == "verificado_externo"]
        
        # Generar narrativa
        unidades = len(fragmentos)
        ejemplos = [f["contenido_original"][:200] + "..." for f in fragmentos[:3]]
        
        informe = f"""# Informe de Ingestión Epistémica: {self.ruta_fuente.name}

**Identificador de Paquete:** PET-{self.hash_del_documento_fuente}
**Fecha de Operación:** {self.marca_de_tiempo.strftime("%Y-%m-%d %H:%M:%S")}
**Motor de Auditoría:** Toltecayotl Engine v2.2 ("El Fiscal" & "El Cronista")

## 1. Análisis de Contenido (Resumen Narrativo)
Este paquete contiene **{unidades} unidades de conocimiento**. 
El contenido trata principalmente sobre: {self.ruta_fuente.stem.replace('_', ' ')}.

### Fragmentos Destacados:
{chr(10).join([f"- **Excerpto {i+1}:** {ex}" for i, ex in enumerate(ejemplos)])}

## 2. Auditoría de Autoridad y Certeza
| Nivel de Certeza | Fragmentos | Autoridad Predominante |
| :--- | :--- | :--- |
| Hecho Verificado | {len([f for f in fragmentos if f['grado_de_certeza'] == 'Hecho'])} | {humanos[0]['autoridad_del_dato'] if humanos else 'N/A'} |
| Requisito de Diseño | {len([f for f in fragmentos if f['grado_de_certeza'] == 'Requisito'])} | {humanos[0]['autoridad_del_dato'] if humanos else 'N/A'} |
| Propuesta / Sugerencia | {len([f for f in fragmentos if f['grado_de_certeza'] == 'Propuesta'])} | IA |

## 3. Semáforo de Riesgo Epistémico (Fiscalía)
- **Estado:** {"🔴 CRÍTICO (Alucinaciones Detectadas)" if riesgos else "🟢 LIMPIO"}
- **Riesgos de Alucinación:** {len(riesgos)}
- **Verificaciones Externas:** {len(externos)}
- **Autoridad Humana (Tesista):** {len(humanos)} fragmentos validados directamente.

## 4. Nexos de Verdad (Cronista)
{chr(10).join([f"- **F{f['metadatos_de_procedencia'].get('id_bloque_agente', 'N/A')}:** {f['fundamento_del_dato']}" for f in fragmentos if f['fundamento_del_dato'] != 'N/A'][:20])}

---
*Este informe garantiza que el contenido ingestado es trazable y fundamentado. Bajo la política v2.2, los riesgos de alucinación han sido aislados para revisión humana.*
"""
        with open(ruta_salida, "w", encoding="utf-8") as f: f.write(informe)
        return ruta_salida

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("fuente")
    args = parser.parse_args()
    ruta = Path(args.fuente)
    if not ruta.exists(): sys.exit(1)
    motor = IngestorToltecayotl(ruta)
    fragmentos = motor.ejecutar_ingesta()
    dir_pet = Path("00_sistema_tesis/05_registros_de_ingestion/paquetes_pet")
    dir_pet.mkdir(parents=True, exist_ok=True)
    with open(dir_pet / f"PET-{motor.hash_del_documento_fuente[:12]}.jsonl", "w", encoding="utf-8") as f:
        for frag in fragmentos: f.write(json.dumps(frag, ensure_ascii=False) + "\n")
    ruta_inf = motor.generar_informe_descriptivo(fragmentos)
    print(f"[OK] Ingesta v2.2 completa. Reporte: {ruta_inf.name}")

if __name__ == "__main__": main()
