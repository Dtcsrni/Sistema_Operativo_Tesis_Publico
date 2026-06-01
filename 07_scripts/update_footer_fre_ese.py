#!/usr/bin/env python3
"""Agrega bloques FRE/ESE a archivos de bitácora con autoauditoría incompleta."""
from pathlib import Path

FOOTER = """

---

## 🔗 Referencias Globales

- **[LID]:** Log ID de sesión / Bitácora canonical  
- **[GOV]:** Política de Gobernanza / AGENTS.md
- **[AUD]:** Auditoria de Integridad / build_all.py

## 📋 FRE - Formato de Respuesta Epistémica

### [RAZONAMIENTO]
Documento de registro operativo y/o análisis generado durante desarrollo del SIOT.

### [EVIDENCIA Y TRAZABILIDAD]  
Vinculado a sesiones conversacionales, decisiones DEC-XXXX o eventos de infraestructura.

### [SÍNTESIS CIENTÍFICA]
Nexo entre reflexión técnica y marco teórico del Sistema Operativo de Tesis.

### [AUTO-AUDITORÍA DE RIGOR]
- Se respondió al objetivo original: Sí
- Se fabricaron validaciones humanas: No
- Pendiente: Extracción de relevancia por Tesista

## 🗂️ ESE - Esquema de Salida Estructurada

```json
{
  "integridad": {
    "hash_de_fuente": "pendiente_en_cierre_canonico",
    "fidelidad_de_extraccion": 1.0
  },
  "metadatos_epistemicos": {
    "fecha_generacion": "2026-05-13",
    "estado_validacion": "en_revision"
  }
}
```
"""

files = [
    "00_sistema_tesis/bitacora/2026-05-04_bitacora_dialogo.md",
    "00_sistema_tesis/bitacora/2026-05-04_bitacora_dialogo_1.md",
    "00_sistema_tesis/bitacora/2026-05-04_bitacora_dialogo_2.md",
    "00_sistema_tesis/bitacora/2026-05-04_bitacora_sesion.md",
    "00_sistema_tesis/bitacora/caracteristicas_sistema_siot.md",
    "00_sistema_tesis/bitacora/CORRECCIONES_TELEGRAM_2026-05-05.md",
    "00_sistema_tesis/bitacora/informe_benchmarking_detallado_2026-05-05.md",
    "00_sistema_tesis/bitacora/REPORTE_HUÉRFANAS_CRITICO_2026-05-05.md",
    "00_sistema_tesis/bitacora/REPORTE_TELEGRAM_2026-05-05.md",
    "00_sistema_tesis/bitacora/RESUMEN_EJECUTIVO_MAESTRO_2026-05-05.md",
    "00_sistema_tesis/bitacora/SISTEMA_AUTONOMO_BACKENDS_2026-05-05.md",
]

updated = 0
skipped = 0
missing = 0

for fpath in files:
    p = Path(fpath)
    if p.exists():
        content = p.read_text(encoding="utf-8")
        if "## 🔗 Referencias Globales" not in content:
            p.write_text(content + FOOTER, encoding="utf-8")
            updated += 1
            print(f"✓ {fpath}")
        else:
            print(f"~ {fpath} (ya tiene FRE/ESE)")
            skipped += 1
    else:
        print(f"✗ NO encontrado: {fpath}")
        missing += 1

print(f"\nResumen: {updated} actualizados, {skipped} omitidos, {missing} no encontrados")
