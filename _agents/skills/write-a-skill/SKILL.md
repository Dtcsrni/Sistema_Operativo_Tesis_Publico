---
name: write-a-skill
description: Create new agent skills with proper structure, progressive disclosure, and bundled resources. Use when user wants to create, write, or build a new skill for the _agents/skills/ directory of this project.
source: https://github.com/mattpocock/skills/blob/main/skills/productivity/write-a-skill/SKILL.md
---

# Writing Skills

## Process

1. **Gather requirements** - ask user about:
   - What task/domain does the skill cover?
   - What specific use cases should it handle?
   - Does it need executable scripts or just instructions?
   - Any reference materials to include?
   - Does it need an "Adaptación OpenClaw" section?

2. **Draft the skill** - create:
   - SKILL.md with concise instructions
   - Additional reference files if content exceeds 500 lines
   - Utility scripts if deterministic operations needed

3. **Review with user** - present draft and ask:
   - Does this cover your use cases?
   - Anything missing or unclear?
   - Should any section be more/less detailed?

## Skill Structure (OpenClaw)

```
_agents/skills/<skill-name>/
├── SKILL.md           # Main instructions (required)
├── REFERENCE.md       # Detailed docs (if needed)
├── EXAMPLES.md        # Usage examples (if needed)
└── scripts/           # Utility scripts (if needed)
    └── helper.py
```

## SKILL.md Template

```md
---
name: skill-name
description: Brief description of capability. Use when [specific triggers].
source: https://github.com/... (if upstream)
---

# Skill Name

## Quick start

[Minimal working example]

## Workflows

[Step-by-step processes with checklists for complex tasks]

## Adaptación OpenClaw

[Mapeo de referencias upstream a equivalentes del proyecto]

## Soberanía Humana

[Si aplica: restricciones de validación autónoma]
```

## Description Requirements

The description is **the only thing your agent sees** when deciding which skill to load.

**Goal**: Give the agent just enough info to know:
1. What capability this skill provides
2. When/why to trigger it (specific keywords, contexts, file types)

**Format**:
- Max 1024 chars
- Write in third person
- First sentence: what it does
- Second sentence: "Use when [specific triggers]"

**Good example**:
```
Debug RKLLM compilation failures and NPU segfaults using a disciplined 6-phase loop. Use when user reports a segfault, OOM error, benchmark failure, or pipeline regression.
```

**Bad example**:
```
Helps with debugging.
```

## When to Add Scripts

Add utility scripts when:
- Operation is deterministic (validation, formatting, hash calculation)
- Same code would be generated repeatedly
- Errors need explicit handling

Scripts save tokens and improve reliability vs generated code.

## When to Split Files

Split into separate files when:
- SKILL.md exceeds 100 lines
- Content has distinct domains
- Advanced features are rarely needed

## Review Checklist

After drafting, verify:

- [ ] Description includes triggers ("Use when...")
- [ ] SKILL.md under 100 lines (or split into reference files)
- [ ] No time-sensitive info
- [ ] Consistent terminology (usa glosario de CONTEXT.md)
- [ ] Concrete examples included
- [ ] References one level deep
- [ ] "Adaptación OpenClaw" section present if upstream skill
- [ ] "Soberanía Humana" section if skill toma decisiones sustantivas

## Registro de Nuevo Skill
Tras crear un skill nuevo, actualizar AGENTS.md §7 con la entrada correspondiente. Si el skill tiene impacto en políticas del sistema, crear DEC-XXXX en `00_sistema_tesis/decisiones/`.

_Última actualización: `2026-04-29`._
