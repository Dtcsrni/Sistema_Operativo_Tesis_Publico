#!/usr/bin/env python3
"""Generar entrada para matriz de trazabilidad."""

from pathlib import Path
from datetime import datetime, timezone

repo_root = Path("v:/Sistema_Operativo_Tesis_Posgrado")
matriz_path = repo_root / "00_sistema_tesis/bitacora/matriz_trazabilidad.md"

# Leer matriz existente
with open(matriz_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar la sección de tabla y preparar nueva entrada
now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
nuevo_step = """
| {date} | [VAL-STEP-764] | [DEC-0047] | Diseño Arquitectónico: Maestro Orquestador SIOT | CRÍTICA | Innovación (Auto-orquestación) | ⏳ Pendiente Validación | [Diseño](../../pendientes/ARQUITECTURA_MAESTRO_ORQUESTADOR.md) |
| {date} | [VAL-STEP-765] | [DEC-0047] | Implementación: 5 Subagentes Especializados | ALTA | Escalabilidad | ⏳ Etapa 2 | [Guía](../../pendientes/GUIA_INTEGRACION_MAESTRO.md) |""".format(date=now)

print("📋 ENTRADA PROPUESTA PARA MATRIZ DE TRAZABILIDAD:")
print("=" * 100)
print(nuevo_step)
print("\n✅ Copiar y agregar a:")
print(f"   {matriz_path}")
