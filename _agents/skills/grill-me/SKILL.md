---
name: grill-me
description: Interview the user relentlessly about a plan or design until reaching shared understanding, resolving each branch of the decision tree. Use when user wants to stress-test a plan, get grilled on their design, mentions "grill me", or needs to think through a decision before committing. Lightweight version of grill-with-docs (no doc updates).
source: https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time.

If a question can be answered by exploring the codebase, explore the codebase instead.

## Diferencia con grill-with-docs
`grill-me` es la versión ligera: solo entrevista, no actualiza `CONTEXT.md` ni crea DEC-XXXX. Úsalo para decisiones rápidas o exploración informal. Usa `grill-with-docs` cuando quieras que las decisiones queden documentadas en el dominio.

## Soberanía Humana
No marques ninguna decisión como validada durante la sesión. Las decisiones sustantivas requieren Step ID del Tesista.

_Última actualización: `2026-05-15`._
