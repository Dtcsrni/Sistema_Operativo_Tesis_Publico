---
name: to-prd
description: Turn the current conversation context into a PRD and publish it to the project issue tracker. Use when user wants to create a PRD from the current context, plan a new feature of the thesis system, or document a technical requirement formally.
source: https://github.com/mattpocock/skills/blob/main/skills/engineering/to-prd/SKILL.md
---

This skill takes the current conversation context and codebase understanding and produces a PRD. Do NOT interview the user — just synthesize what you already know.

## Process

1. Explore the repo to understand the current state of the codebase, if you haven't already. Use the project's domain glossary vocabulary (`00_sistema_tesis/CONTEXT.md`) throughout the PRD, and respect any decisiones DEC-XXXX in the area you're touching.

2. Sketch out the major modules you will need to build or modify to complete the implementation. Actively look for opportunities to extract deep modules that can be tested in isolation.

   A deep module (as opposed to a shallow module) is one which encapsulates a lot of functionality in a simple, testable interface which rarely changes.

   Check with the user that these modules match their expectations. Check with the user which modules they want tests written for.

3. Write the PRD using the template below, then publish it to the **local issue tracker**: create the file at `00_sistema_tesis/pendientes/PRD-YYYY-MM-DD_<slug>.md`. Apply the `needs-triage` label in the file's frontmatter so it enters the normal triage flow.

<prd-template>

## Problem Statement

The problem that the user is facing, from the user's perspective.

## Solution

The solution to the problem, from the user's perspective.

## User Stories

A LONG, numbered list of user stories. Each user story should be in the format of:

1. As an <actor>, I want a <feature>, so that <benefit>

<user-story-example>
1. As a Tesista, I want the benchmark runner to produce a certified JSON report, so that I can include cryptographically verified metrics in the thesis
</user-story-example>

This list of user stories should be extensive and cover all aspects of the feature.

## Implementation Decisions

A list of implementation decisions that were made. This can include:

- The modules that will be built/modified
- The interfaces of those modules that will be modified
- Technical clarifications from the developer
- Architectural decisions
- Schema changes
- API contracts
- Specific interactions

Do NOT include specific file paths or code snippets. They may end up being outdated very quickly.

## Testing Decisions

A list of testing decisions that were made. Include:

- A description of what makes a good test (only test external behavior, not implementation details)
- Which modules will be tested
- Prior art for the tests (i.e. similar types of tests in the codebase)

## Out of Scope

A description of the things that are out of scope for this PRD.

## Further Notes

Any further notes about the feature.

</prd-template>

## Adaptación OpenClaw
- **Issue tracker**: archivos locales en `00_sistema_tesis/pendientes/`
- **Formato de archivo**: `PRD-YYYY-MM-DD_<slug>.md` con frontmatter YAML
- **Labels disponibles**: `needs-triage`, `ready-for-agent`, `ready-for-human`, `wontfix`, `bug`, `enhancement`
- **Glosario**: `00_sistema_tesis/CONTEXT.md`
- **Decisiones**: `00_sistema_tesis/decisiones/DEC-XXXX*.md`
- **Soberanía**: no marques ningún PRD como aprobado — requiere Step ID del Tesista

Ejemplo de frontmatter:
```yaml
---
title: "PRD: <nombre>"
date: YYYY-MM-DD
status: needs-triage
category: enhancement
---
```

_Última actualización: `2026-05-15`._
