---
name: handshake_ledger
description: Protocolo mandatorio de soberanía humana y trazabilidad inmutable.
---

# Protocolo Handshake & Ledger

Este skill define las reglas inquebrantables para la colaboración humano-agente en el **Sistema Operativo de la Tesis**. Su objetivo es garantizar que ninguna decisión técnica sea tomada o validada sin intervención humana explícita y verificable.

## Reglas de Oro

1.  **Soberanía Humana Absoluta**: El Agente tiene PROHIBIDO marcar como completados (`[x]`) los campos de "Criterio de Aceptación Humana". Esta acción es exclusiva del Tesista.
2.  **Vinculación por Step ID**: Toda propuesta sustantiva o validación debe vincularse a un **Step ID** único y registrarse en el `log_sesiones_trabajo_registradas.md`.
3.  **Libro Mayor (Ledger) Inmutable**: Cada entrada en el Ledger debe estar protegida por un delimitador `<<< >>>` y un **Hash SHA-256** de integridad.
4.  **Respeto a Guardrails**: Si un archivo contiene el tag `<!-- SISTEMA_TESIS:PROTEGIDO -->`, el Agente no debe modificarlo sin una instrucción humana explícita y el uso de mecanismos de respaldo.
5.  **Cadenas de Evidencia**: Mantener la continuidad de la cadena en el Ledger (Anterior/Siguiente) para facilitar la auditoría.

## Flujo de Validación

1.  El Agente propone un cambio o decisión.
2.  El Agente solicita validación humana vinculada a un Step ID.
3.  El Tesista valida.
4.  El Agente registra la validación en el Ledger, calcula el Hash y actualiza la Matriz de Trazabilidad.
5.  El Agente vincula el registro de decisión (`DEC`) al Ledger mediante el Hash.

_Última actualización: `2026-04-14`._
