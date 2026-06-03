<!-- SISTEMA_TESIS:PROTEGIDO -->
<!-- GID: DEC-0048 | 2026-06-01 | v0.1 | Propuesta | pendiente-validacion-humana -->
---
id: DEC-0048
title: Adopción de Harness Engineering Agnóstico para SIOT
date: 2026-06-01
status: propuesta técnica pendiente de validación humana explícita
tags:
  - Harness Engineering
  - Agentes
  - Gobernanza
  - Observabilidad
  - Reproducibilidad
---

# DEC-0048: Adopción de Harness Engineering Agnóstico

## Contexto

SIOT ya cuenta con `build_all.py`, Mission Control, OpenClaw, Toltecayotl, publicación pública y gates de seguridad. La falta de un contrato común dificultaba comparar ejecuciones entre agentes, reproducir trayectorias y producir evidencia uniforme para revisores.

## Decisión

Adoptar una capa transversal de harness engineering para describir, ejecutar, medir y auditar trabajo de agentes de IA diversos en SIOT sin acoplar la gobernanza a un proveedor, modelo o runtime específico.

## Alternativas consideradas

1. Mantener pruebas y auditorías separadas por herramienta.
2. Adoptar un framework externo como fuente de verdad operativa.
3. Crear una capa local-first que envuelva los flujos existentes.

La alternativa elegida es la tercera porque reduce acoplamiento, conserva soberanía documental y permite integrar agentes distintos bajo contratos homogéneos.

## Métricas de éxito

- `python 07_scripts/harness/cli.py verify --json` retorna `ok: true`.
- `python 07_scripts/build_all.py --group harness --force` termina sin fallos.
- `python 07_scripts/build_all.py` conserva cero fallos duros.
- La proyección pública no contiene secretos, prompts completos ni evidencia privada.

## Consecuencias

- Cada agente puede registrar ejecuciones bajo un manifiesto común.
- La preparación técnica se reporta como readiness, no como validación humana.
- Los artefactos públicos se sanitizan antes de publicación.
- Las decisiones humanas siguen gobernadas por `DEC-0014` y requieren Step ID.

## Trazabilidad del trabajo asistido

- **Agente/Rol de asistencia:** agente de apoyo no publicado
- **Proveedor de asistencia:** proveedor de IA no publicado
- **Modelo/Versión de asistencia:** modelo de IA no publicado
- **Nivel de razonamiento:** alto
- **Prompts/Contexto clave:** solicitud humana de aplicar harness engineering agnóstico a todo SIOT y preparar borrador LaTeX para revisores.

## Autoauditoría compacta

- **Pre-checks:** [Integridad][LID] · [Ética][GOV] · [Auditoría][AUD] · Contexto explícito · Confirmación verificable · Reproducibilidad mínima
- **Soporte:** pendiente de Step ID humano para aceptación formal.
- **Integridad:** pendiente de cierre canónico.
- **Nivel de auditoría:** Alto
- **Modo:** propuesta técnica; no validada autónomamente.
- **Fecha:** 2026-06-01
- **Disparador:** instrucción humana directa para implementar harness engineering agnóstico.

## Referencias

[LID]:  ruta local no pública 
[GOV]:  ruta local no pública 
[AUD]:  ruta local no pública 
[REF-DEC-0014]:  ruta local no pública

_Última actualización: `2026-06-03`._
