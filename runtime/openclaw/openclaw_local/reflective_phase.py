"""reflective_phase.py -- Propuesta automatica de nuevas skills basada en patrones de uso.

Fase 5 del roadmap Hermes/OpenClaw (D6=B: experimental, validacion humana obligatoria).

Flujo:
  1. Analiza los ultimos N turnos del estado del bot (state["turns"])
  2. Detecta patrones: temas recurrentes, comandos frecuentes, errores repetidos
  3. Para cada patron significativo, genera un borrador SKILL.md en:
     _agents/skills/proposed/<nombre>/SKILL.md
  4. El tesista revisa con /skills_pendientes en Telegram y aprueba/descarta

Nunca crea skills en _agents/skills/ directamente — solo en proposed/.
La aprobacion requiere accion humana explicita (DEC-0014 compatible).
"""
from __future__ import annotations

import json
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSED_DIR = ROOT / "_agents" / "skills" / "proposed"
MIN_OCCURRENCES = int(os.getenv("OPENCLAW_REFLECT_MIN_OCC", "3"))
MAX_TURNS_ANALYZE = int(os.getenv("OPENCLAW_REFLECT_MAX_TURNS", "50"))


# -- Deteccion de patrones ----------------------------------------------------

@dataclass
class SkillCandidate:
    name: str          # snake_case, sin espacios
    title: str         # Titulo legible
    description: str   # Descripcion de la skill propuesta
    trigger_count: int # Cuantas veces se detecto el patron
    examples: list[str]  # Ejemplos de queries que lo activaron


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower().strip())


def _extract_topics(turns: list[dict]) -> Counter:
    """Extrae temas/dominios frecuentes de los turnos recientes."""
    topic_markers = {
        "iot": ["iot", "sensor", "gateway", "mqtt", "nodo", "edge", "rssi", "bateria"],
        "docker": ["docker", "contenedor", "compose", "container"],
        "benchmark": ["benchmark", "tps", "latencia", "rendimiento", "velocidad"],
        "tesis": ["tesis", "capitulo", "investigacion", "metodologia", "hipotesis"],
        "python": ["python", "codigo", "script", "funcion", "clase", "import"],
        "ollama": ["ollama", "modelo", "llm", "inferencia", "prompt"],
        "ssh": ["ssh", "edge", "orange pi", "rk3588", "remoto"],
        "latex": ["latex", "tex", "figura", "tabla", "biblio", "cita"],
    }
    counts: Counter = Counter()
    for turn in turns:
        text = _normalize(turn.get("user", "") + " " + turn.get("assistant", ""))
        for topic, markers in topic_markers.items():
            if any(m in text for m in markers):
                counts[topic] += 1
    return counts


def _extract_command_patterns(turns: list[dict]) -> Counter:
    """Detecta comandos de usuario repetitivos."""
    patterns: Counter = Counter()
    for turn in turns:
        user_text = _normalize(turn.get("user", ""))
        # Detectar patrones de preguntas frecuentes
        if any(w in user_text for w in ["como hago", "como puedo", "como se"]):
            patterns["how_to_patterns"] += 1
        if any(w in user_text for w in ["que es", "explica", "definicion"]):
            patterns["concept_explanation"] += 1
        if any(w in user_text for w in ["error", "fallo", "no funciona", "problema"]):
            patterns["debugging"] += 1
        if any(w in user_text for w in ["escribe", "genera", "crea un", "implementa"]):
            patterns["code_generation"] += 1
        if any(w in user_text for w in ["cuanto es", "calcula", "convierte", "estadistica"]):
            patterns["calculations"] += 1
    return patterns


def detect_skill_candidates(turns: list[dict]) -> list[SkillCandidate]:
    """Analiza turnos y propone skills para patrones frecuentes."""
    if not turns:
        return []

    recent = turns[-MAX_TURNS_ANALYZE:]
    topic_counts = _extract_topics(recent)
    command_counts = _extract_command_patterns(recent)
    candidates: list[SkillCandidate] = []

    # Skill por tema recurrente
    for topic, count in topic_counts.most_common(5):
        if count >= MIN_OCCURRENCES:
            examples = [
                t["user"][:80]
                for t in recent
                if topic in _normalize(t.get("user", ""))
            ][:3]
            candidates.append(SkillCandidate(
                name=f"{topic}_context",
                title=f"Contexto {topic.upper()} para OpenClaw",
                description=(
                    f"Skill de contexto compacto para consultas sobre {topic}. "
                    f"Detectada {count} veces en los ultimos {len(recent)} turnos. "
                    f"Proporciona terminologia, convenciones y referencias clave del dominio."
                ),
                trigger_count=count,
                examples=examples,
            ))

    # Skill por patron de uso de comandos
    for pattern, count in command_counts.most_common(3):
        if count >= MIN_OCCURRENCES * 2:  # Umbral mas alto para patrones de comando
            candidates.append(SkillCandidate(
                name=f"automate_{pattern}",
                title=f"Automatizacion de patron: {pattern.replace('_', ' ')}",
                description=(
                    f"Patron de uso detectado {count} veces: '{pattern}'. "
                    f"Considera crear un comando dedicado o det_script para este flujo."
                ),
                trigger_count=count,
                examples=[],
            ))

    return candidates


# -- Generacion de borradores SKILL.md ----------------------------------------

def _skill_md_template(candidate: SkillCandidate) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    examples_block = ""
    if candidate.examples:
        examples_block = "\n## Ejemplos de uso detectados\n\n"
        for ex in candidate.examples:
            examples_block += f"- `{ex}`\n"

    return f"""---
name: {candidate.name}
description: >
  {candidate.description}
version: "0.1-proposed"
status: PROPOSED  # Requiere aprobacion humana antes de activar
proposed_at: {now}
trigger_count: {candidate.trigger_count}
applies_to:
  - antigravity
  - vscode_agents
agnostic: true
---

# Skill Propuesta: {candidate.title}

> **ESTADO:** PROPUESTA EXPERIMENTAL
> Requiere revision y aprobacion del tesista antes de activar.
> Para aprobar: mover este directorio a `_agents/skills/{candidate.name}/`

## Descripcion

{candidate.description}
{examples_block}
## Contenido sugerido

<!-- TODO: Completar con instrucciones especificas para el dominio -->
<!-- Basarse en los patrones de uso detectados arriba -->

## Criterio de aprobacion

Esta skill sera util si reduce el tiempo de respuesta o mejora la precision
en consultas del tipo detectado. Evaluar despues de 10 sesiones de uso.

## Comando de aprobacion

```powershell
# Desde la raiz del repositorio:
Move-Item "_agents/skills/proposed/{candidate.name}" "_agents/skills/{candidate.name}"
python 07_scripts/build_all.py --group openclaw
```
"""


def write_proposed_skills(candidates: list[SkillCandidate]) -> list[Path]:
    """Escribe borradores de skills en _agents/skills/proposed/."""
    written: list[Path] = []
    PROPOSED_DIR.mkdir(parents=True, exist_ok=True)

    for candidate in candidates:
        skill_dir = PROPOSED_DIR / candidate.name
        skill_dir.mkdir(exist_ok=True)
        skill_path = skill_dir / "SKILL.md"

        # No sobrescribir si ya existe (no queremos perder ediciones manuales)
        if skill_path.exists():
            continue

        skill_path.write_text(
            _skill_md_template(candidate),
            encoding="utf-8",
        )
        written.append(skill_path)

    return written


# -- Reporte de propuestas pendientes -----------------------------------------

def list_proposed_skills() -> list[dict[str, Any]]:
    """Lista las skills propuestas pendientes de aprobacion."""
    if not PROPOSED_DIR.exists():
        return []

    result = []
    for skill_dir in sorted(PROPOSED_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        # Extraer metadata del frontmatter YAML
        content = skill_md.read_text(encoding="utf-8")
        proposed_at = "?"
        trigger_count = "?"
        for line in content.splitlines():
            if line.startswith("proposed_at:"):
                proposed_at = line.split(":", 1)[1].strip()
            if line.startswith("trigger_count:"):
                trigger_count = line.split(":", 1)[1].strip()
        result.append({
            "name": skill_dir.name,
            "proposed_at": proposed_at,
            "trigger_count": trigger_count,
            "path": str(skill_md.relative_to(ROOT)),
        })
    return result


# -- API publica --------------------------------------------------------------

def maybe_reflect(state: dict[str, Any], repo_root: Path = ROOT) -> int:
    """Punto de entrada: analiza el estado y propone skills si hay patrones.

    Args:
        state:     Estado del bot (dict con clave "turns").
        repo_root: Raiz del repositorio (para calcular rutas).

    Returns:
        Numero de nuevas skills propuestas en esta llamada.
    """
    turns = state.get("turns", [])
    if len(turns) < MIN_OCCURRENCES:
        return 0

    candidates = detect_skill_candidates(turns)
    if not candidates:
        return 0

    written = write_proposed_skills(candidates)
    return len(written)


def format_pending_report() -> str:
    """Genera texto legible de skills pendientes para el comando /skills_pendientes."""
    pending = list_proposed_skills()
    if not pending:
        return "No hay skills propuestas pendientes de aprobacion."

    lines = [f"<b>Skills propuestas pendientes ({len(pending)}):</b>\n"]
    for s in pending:
        lines.append(
            f"  <code>{s['name']}</code>  "
            f"(detectada {s['trigger_count']}x el {s['proposed_at']})\n"
            f"  <code>{s['path']}</code>"
        )
    lines.append(
        "\nPara aprobar una skill:\n"
        "<code>Move-Item _agents/skills/proposed/NOMBRE _agents/skills/NOMBRE</code>"
    )
    return "\n".join(lines)
