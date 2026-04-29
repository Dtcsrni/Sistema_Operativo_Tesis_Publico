---
name: grill-with-docs
description: Grilling session that challenges your plan against the existing domain model, sharpens terminology, and updates documentation (CONTEXT.md, decisiones DEC-XXXX) inline as decisions crystallise. Use when user wants to stress-test a plan against the project language and documented decisions, or before starting a significant technical change.
source: https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md
disable-model-invocation: true
---

Interview me relentlessly about every aspect of this plan until we reach a shared understanding. Walk down each branch of the design tree, resolving dependencies between decisions one-by-one. For each question, provide your recommended answer.

Ask the questions one at a time, waiting for feedback on each question before continuing.

If a question can be answered by exploring the codebase, explore the codebase instead.

## Domain awareness

During codebase exploration, also look for existing documentation:

### File structure (OpenClaw)

```
/
├── 00_sistema_tesis/
│   ├── CONTEXT.md                  ← glosario de dominio (crear si no existe)
│   └── decisiones/
│       ├── DEC-0001-*.md           ← decisiones técnicas (= ADRs)
│       └── DEC-0014-*.md
├── _agents/
│   └── skills/
└── 07_scripts/
```

Si `CONTEXT.md` no existe en `00_sistema_tesis/`, créalo cuando se resuelva el primer término del dominio.

### Glosario esperado del dominio
Términos clave del proyecto: RKLLM, OpenClaw, NPU/RKNN, VAL-STEP, Ledger, Step ID, Fase Reflexiva, Routing Adaptativo, Tesista Soberano, build_all.py, Serena MCP, Caveman, LID/GOV/AUD.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the existing language in `00_sistema_tesis/CONTEXT.md`, call it out immediately. "Your CONTEXT.md defines 'X' as Y, but you seem to mean Z — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'inference' — do you mean RKLLM inference on NPU or llamacpp inference on CPU? Those are different code paths."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your script does X, but you just said Y is the expected behavior — which is right?"

### Update CONTEXT.md inline

When a term is resolved, update `00_sistema_tesis/CONTEXT.md` right there. Don't batch these up — capture them as they happen.

Format de entrada en CONTEXT.md:
```markdown
### <Término>
<Definición concisa en 1-2 oraciones. Solo términos significativos para expertos del dominio.>
```

Don't couple `CONTEXT.md` to implementation details. Only include terms meaningful to domain experts.

### Offer decisiones (ADRs) sparingly

Only offer to create a DEC-XXXX when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the DEC. File goes in `00_sistema_tesis/decisiones/` with format `YYYY-MM-DD_DEC-XXXX_<slug>.md`.

## Soberanía Humana
No marques ninguna decisión como validada. Toda decisión técnica sustantiva requiere Step ID del Tesista antes de cerrarse.

_Última actualización: `2026-04-29`._
