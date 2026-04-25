import sys
from pathlib import Path
sys.path.append('07_scripts')
from guardrails import safe_write

ledger_path = Path('00_sistema_tesis/bitacora/log_sesiones_trabajo_registradas.md')
matrix_path = Path('00_sistema_tesis/bitacora/matriz_trazabilidad.md')

ledger_content = ledger_path.read_text(encoding='utf-8')
matrix_content = matrix_path.read_text(encoding='utf-8')

# 1. Update previous entry in Ledger (VAL-STEP-380)
old_chain = '[Anterior: VAL-STEP-305] | [Siguiente: FIN]'
new_chain = '[Anterior: VAL-STEP-305] | [Siguiente: VAL-STEP-400]'
if old_chain in ledger_content:
    ledger_content = ledger_content.replace(old_chain, new_chain)
else:
    print(f"Warning: Could not find {old_chain}")

# 2. Add new entry to Ledger
new_ledger_entry = """
---

## [VAL-STEP-400]
- **Proveedor:** Google (DeepMind)
- **Modelo/Versión:** Gemini 1.5 Pro / Advanced Agentic Coding v1.0
- **Fecha:** 2026-03-24
- **Vínculo:** [DEC-0014]
- **Hash:** `sha256:31c8cc675b152427feb90a98f68557eac3e4836a017c7734777a2c9a4c460fe7`
- **Audit Level:** MEDIO
- **Cadena:** [Anterior: VAL-STEP-380] | [Siguiente: FIN]
- **Contenido:**
<<<
Objetivo de Sesión: Diagnóstico de completitud arquitectónica para inicio de desarrollo.
Contexto Operativo: El tesista consulta sobre los elementos faltantes en la arquitectura para iniciar el desarrollo. El agente analiza la brecha entre la infraestructura de gobernanza (B0) y el diseño técnico de la tesis (B1/B2), identificando la necesidad de delimitación formal, línea base y diseño detallado de componentes IoT.
Infraestructura: Gemini 1.5 Pro | Sistema Operativo de Tesis v0.1.0.
ID de Sesión: b4fee61f
Diferencial de Plan: Análisis de brechas en [analysis_arch_readiness.md](file:///C:/Users/evega/.gemini/antigravity/brain/b4fee61f-fbc5-4f59-b6a1-2add4cc3cb69/analysis_arch_readiness.md)
---
Tesista (Erick Renato Vega Ceron | Sesion: b4fee61f): "¿que faltaria en la arquitectura para poder empezar el desarrollo de la tesis?"
Agente: "La infraestructura de gestión está completa. Faltan la delimitación formal del caso de estudio (B1), la definición de la línea base de comparación (B2) y el diseño detallado de los componentes de resiliencia (B2) antes de la implementación física." >>>
"""

nav_marker = '\n---' + '\n' + '**Navegación:**'
if nav_marker in ledger_content:
    ledger_content = ledger_content.replace(nav_marker, new_ledger_entry + nav_marker)
else:
    ledger_content += new_ledger_entry

# 3. Update Matrix
matrix_row = '| 2026-03-24 | [VAL-STEP-400] | [BIT-DIAG] | Análisis de preparación arquitectónica | MEDIO | Transparencia (NIST) | [/] Producido | [Log](log_sesiones_trabajo_registradas.md#val-step-400) |'
prev_row = '| 2026-03-24 | [VAL-STEP-380] | [BIT-IMP] | Mejora del sistema de bitácora y cadena | ALTO | Integridad (UNESCO) | [/] En curso | [Log](log_sesiones_trabajo_registradas.md#val-step-380) |'

if prev_row in matrix_content:
    matrix_content = matrix_content.replace(prev_row, prev_row + '\n' + matrix_row)
else:
    print(f"Warning: Could not find {prev_row}")

matrix_link = '[VAL-STEP-400]: log_sesiones_trabajo_registradas.md#val-step-400'
if matrix_link not in matrix_content:
    matrix_content = matrix_content.strip() + '\n' + matrix_link + '\n'

# 4. Save files safely
if safe_write(str(ledger_path), ledger_content, force=True):
    print(f'Ledger updated: {ledger_path}')
else:
    print(f'Failed to update Ledger')

if safe_write(str(matrix_path), matrix_content, force=True):
    print(f'Matrix updated: {matrix_path}')
else:
    print(f'Failed to update Matrix')

