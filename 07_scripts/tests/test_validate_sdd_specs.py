import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "audit")) # audit scripts

import tempfile
import unittest

from validate_sdd_specs import validate_specs  # noqa: E402


VALID_SPEC = """---
title: "PRD: Demo"
date: 2026-05-06
category: enhancement
status: needs-triage
reporter: "Codex"
---

# PRD: Demo

## Problem Statement
Texto.

## Solution
Texto.

## User Stories
1. Como Tesista, quiero una spec, para probar.

## Implementation Decisions
- Mantener alcance.

## Testing Decisions
- Probar comportamiento.

## Out of Scope
- Validacion humana automatica.
"""

VALID_AGENT_OPS_SPEC = """---
title: "SPEC: Agent Ops Core"
date: 2026-05-13
category: specification
status: implementation-ready
owner: "Tesista Principal"
decisions: ["DEC-0014"]
step_id: "PENDIENTE"
---

# SPEC: Agent Ops Core

## Objetivo
Texto.

## Alcance
Texto.

## Rutas Afectadas
- `07_scripts/ops/`

## Gates Publicos
Texto.

## Pruebas y Aceptacion
Texto.

## Rollback
Texto.

## Cierre de Trazabilidad
Texto.

## FRE
Texto.

## ESE
Texto.
"""


class TestValidateSddSpecs(unittest.TestCase):
    def test_accepts_valid_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "00_sistema_tesis" / "pendientes"
            target.mkdir(parents=True)
            (target / "PRD-demo.md").write_text(VALID_SPEC, encoding="utf-8")

            result = validate_specs(root)
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["checked"], ["00_sistema_tesis/pendientes/PRD-demo.md"])

    def test_rejects_missing_testing_decisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "00_sistema_tesis" / "pendientes"
            target.mkdir(parents=True)
            (target / "PRD-demo.md").write_text(
                VALID_SPEC.replace("\n## Testing Decisions\n- Probar comportamiento.\n", "\n"),
                encoding="utf-8",
            )

            result = validate_specs(root)
            self.assertTrue(any("Testing Decisions" in error for error in result["errors"]))

    def test_rejects_completed_checkboxes_in_specs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "00_sistema_tesis" / "pendientes"
            target.mkdir(parents=True)
            (target / "PRD-demo.md").write_text(VALID_SPEC + "\n- [x] cerrado\n", encoding="utf-8")

            result = validate_specs(root)
            self.assertTrue(any("no debe marcar tareas como completadas" in error for error in result["errors"]))

    def test_accepts_agent_ops_spec_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "00_sistema_tesis" / "pendientes"
            target.mkdir(parents=True)
            (target / "SPEC-agent-ops.md").write_text(VALID_AGENT_OPS_SPEC, encoding="utf-8")

            result = validate_specs(root)
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["checked"], ["00_sistema_tesis/pendientes/SPEC-agent-ops.md"])

    def test_rejects_spec_without_pending_step_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "00_sistema_tesis" / "pendientes"
            target.mkdir(parents=True)
            (target / "SPEC-agent-ops.md").write_text(
                VALID_AGENT_OPS_SPEC.replace('step_id: "PENDIENTE"', 'step_id: "VAL-STEP-999"'),
                encoding="utf-8",
            )

            result = validate_specs(root)
            self.assertTrue(any("step_id como PENDIENTE" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
