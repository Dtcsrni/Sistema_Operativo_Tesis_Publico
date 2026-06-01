import json
import re
from pathlib import Path

def auditar_rigor_pet(ruta_jsonl: str):
    ruta = Path(ruta_jsonl)
    if not ruta.exists(): return f"Error: No se encontró {ruta_jsonl}"

    fragmentos = []
    with open(ruta, "r", encoding="utf-8") as f:
        for linea in f:
            if not linea.strip(): continue
            try:
                fragmentos.append(json.loads(linea))
            except json.JSONDecodeError: continue

    total = len(fragmentos)
    riesgos = [f for f in fragmentos if f.get("auditoria_de_ingesta", {}).get("estado") == "RIESGO_DE_ALUCINACION"]
    humanos = [f for f in fragmentos if f.get("autoridad_del_dato") == "Tesista"]
    ia_fundamentada = [f for f in fragmentos if f.get("autoridad_del_dato") == "IA" and f.get("fundamento_del_dato") != "N/A"]

    score = 100
    if total > 0:
        score -= (len(riesgos) / total) * 100
        score += (len(humanos) / total) * 50 # Bonus por autoridad humana
        score = min(100, max(0, score))

    reporte = {
        "paquete": ruta.name,
        "score_confianza": round(score, 2),
        "total_fragmentos": total,
        "riesgos_alucinacion": len(riesgos),
        "autoridad_humana": len(humanos),
        "ia_verificada": len(ia_fundamentada),
        "estado": "APROBADO" if score > 80 and not riesgos else "RECHAZADO"
    }
    return reporte

paquetes = [
    "00_sistema_tesis/05_registros_de_ingestion/paquetes_pet/PET-866d6720b9c2.jsonl",
    "00_sistema_tesis/05_registros_de_ingestion/paquetes_pet/PET-635dd24cc045.jsonl",
    "00_sistema_tesis/05_registros_de_ingestion/paquetes_pet/PET-6656d0e745ba.jsonl",
    "00_sistema_tesis/05_registros_de_ingestion/paquetes_pet/PET-f94acef131af.jsonl",
    "00_sistema_tesis/05_registros_de_ingestion/paquetes_pet/PET-f1d50f9eef09.jsonl"
]

for p in paquetes:
    res = auditar_rigor_pet(p)
    print(json.dumps(res, indent=2))
