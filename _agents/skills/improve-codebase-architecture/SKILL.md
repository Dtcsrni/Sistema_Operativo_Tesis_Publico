---
name: improve-codebase-architecture
description: Find deepening opportunities in a codebase, informed by the domain language in CONTEXT.md and the decisions in decisiones/DEC-XXXX. Use when the user wants to improve architecture, find refactoring opportunities, consolidate tightly-coupled modules, or make a codebase more testable and AI-navigable.
source: https://github.com/mattpocock/skills/blob/main/skills/engineering/improve-codebase-architecture/SKILL.md
---

Surface architectural friction and propose **deepening opportunities** — refactors that turn shallow modules into deep ones. The aim is testability and AI-navigability.

Use these terms exactly in every suggestion:

- **Module** — anything with an interface and an implementation.
- **Depth** — leverage at the interface: a lot of behaviour behind a small interface. **Deep** = high leverage. **Shallow** = interface nearly as complex as the implementation.
- **Seam** — where an interface lives; a place behaviour can be altered without editing in place.
- **Locality** — change, bugs, knowledge concentrated in one place.

Key principles:

- **Deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through. If complexity reappears across N callers, it was earning its keep.
- **The interface is the test surface.**
- **One adapter = hypothetical seam. Two adapters = real seam.**

### 1. Explore
Read `00_sistema_tesis/CONTEXT.md` and decisiones DEC-XXXX in the area you're touching first.

Walk the codebase and note friction:
- Where does understanding one concept require bouncing between many small modules?
- Where are modules **shallow**?
- Where do tightly-coupled modules leak across their seams?
- Which parts are untested or hard to test?

### 2. Present candidates
Numbered list of deepening opportunities. For each:

- **Files** — which files/modules
- **Problem** — why the current architecture causes friction
- **Solution** — plain English description of what would change
- **Benefits** — locality and leverage, plus how tests would improve

**DEC conflicts**: Mark clearly if a candidate contradicts an existing DEC-XXXX. Don't list every theoretical refactor a DEC forbids.

Do NOT propose interfaces yet. Ask: "Which of these would you like to explore?"

### 3. Grilling loop
Walk the design tree with the user. Side effects inline as decisions crystallize:

- New concept not in `CONTEXT.md`? Add it to `00_sistema_tesis/CONTEXT.md`.
- User rejects with load-bearing reason? Offer a DEC-XXXX to record it.

## Adaptación OpenClaw
- Glosario: `00_sistema_tesis/CONTEXT.md`
- Decisiones: `00_sistema_tesis/decisiones/DEC-XXXX*.md`
- Áreas de fricción conocidas: pipeline benchmark, compilación RKLLM, integración Serena MCP, sistema Ledger
- Refactoring mayor requiere Step ID del Tesista antes de ejecutar

_Última actualización: `2026-04-29`._
