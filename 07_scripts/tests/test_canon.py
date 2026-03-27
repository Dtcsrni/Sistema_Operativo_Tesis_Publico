import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

import canon  # noqa: E402
from canon import (  # noqa: E402
    build_state,
    materialize_events,
    projection_paths,
    render_ledger,
    reseal_events,
    resolve_human_validation_evidence,
    verify_conversation_source_for_step,
    validate_events,
    verbal_confirmation_hash,
)


class TestCanon(unittest.TestCase):
    def test_reseal_events_builds_hash_chain(self):
        events = [
            {
                "event_id": "EVT-0001",
                "event_type": "generic",
                "occurred_at": "2026-03-26 00:00:00",
                "actor": {"type": "system"},
                "session_id": "",
                "risk_level": "MEDIO",
                "links": {},
                "payload": {"value": 1},
                "affected_files": [],
                "human_validation": {"required": False},
                "prev_event_hash": "",
                "content_hash": "",
            },
            {
                "event_id": "EVT-0002",
                "event_type": "generic",
                "occurred_at": "2026-03-26 00:00:01",
                "actor": {"type": "system"},
                "session_id": "",
                "risk_level": "MEDIO",
                "links": {},
                "payload": {"value": 2},
                "affected_files": [],
                "human_validation": {"required": False},
                "prev_event_hash": "",
                "content_hash": "",
            },
        ]
        sealed = reseal_events(events)
        self.assertEqual(sealed[0]["prev_event_hash"], "INICIO")
        self.assertEqual(sealed[1]["prev_event_hash"], sealed[0]["content_hash"])
        self.assertEqual(validate_events(sealed), [])

    def test_projection_paths_include_primary_views(self):
        paths = projection_paths([])
        self.assertIn("00_sistema_tesis/bitacora/log_conversaciones_ia.md", paths)
        self.assertIn("00_sistema_tesis/config/sign_offs.json", paths)
        self.assertIn("00_sistema_tesis/canon/state.json", paths)

    def test_build_state_tracks_latest_step(self):
        events = reseal_events(
            [
                {
                    "event_id": "VAL-STEP-460",
                    "event_type": "human_validation",
                    "occurred_at": "2026-03-26 00:00:00",
                    "actor": {"type": "ai"},
                    "session_id": "codex",
                    "risk_level": "ALTO",
                    "links": {},
                    "payload": {"content_text": 'Agente: "¿Autorizas?"\nTesista: "si. implementa"'},
                    "affected_files": [],
                    "human_validation": {
                        "required": True,
                        "step_id": "VAL-STEP-460",
                        "status": "validated",
                        "validated_at": "2026-03-26",
                        "mode": "Confirmación Verbal",
                        "question_text": '"¿Autorizas?"',
                        "confirmation_text": '"si. implementa"',
                        "confirmation_kind": "respuesta_afirmativa",
                        "confirmation_source_type": "campo_canonico_explicito",
                        "confirmation_source_of_truth": "00_sistema_tesis/canon/events.jsonl :: VAL-STEP-460 :: human_validation.confirmation_text",
                        "confirmation_text_hash": verbal_confirmation_hash('"si. implementa"'),
                    },
                    "prev_event_hash": "",
                    "content_hash": "",
                }
            ]
        )
        state = build_state(events)
        self.assertEqual(state["canon"]["latest_step_id"], "VAL-STEP-460")

    def test_validate_events_accepts_derived_legacy_confirmation(self):
        events = reseal_events(
            [
                {
                    "event_id": "VAL-STEP-470",
                    "event_type": "human_validation",
                    "occurred_at": "2026-03-26 00:00:00",
                    "actor": {"type": "ai"},
                    "session_id": "codex",
                    "risk_level": "ALTO",
                    "links": {},
                    "payload": {
                        "content_text": 'Objetivo\n---\nTesista (Erick Renato Vega Ceron | Sesion: codex): "PLEASE IMPLEMENT THIS PLAN"'
                    },
                    "affected_files": [],
                    "human_validation": {
                        "required": True,
                        "step_id": "VAL-STEP-470",
                        "status": "validated",
                        "validated_at": "2026-03-26",
                        "mode": "Confirmación Verbal",
                    },
                    "prev_event_hash": "",
                    "content_hash": "",
                }
            ]
        )
        self.assertEqual(validate_events(events), [])
        evidence = resolve_human_validation_evidence(events[0])
        self.assertEqual(evidence["confirmation_text"], '"PLEASE IMPLEMENT THIS PLAN"')

    def test_validate_events_rejects_mismatched_confirmation_hash(self):
        events = reseal_events(
            [
                {
                    "event_id": "VAL-STEP-471",
                    "event_type": "human_validation",
                    "occurred_at": "2026-03-26 00:00:00",
                    "actor": {"type": "ai"},
                    "session_id": "codex",
                    "risk_level": "ALTO",
                    "links": {},
                    "payload": {"content_text": 'Tesista: "si"'},
                    "affected_files": [],
                    "human_validation": {
                        "required": True,
                        "step_id": "VAL-STEP-471",
                        "status": "validated",
                        "validated_at": "2026-03-26",
                        "mode": "Confirmación Verbal",
                        "confirmation_text": '"si"',
                        "confirmation_text_hash": "deadbeef",
                    },
                    "prev_event_hash": "",
                    "content_hash": "",
                }
            ]
        )
        errors = validate_events(events)
        self.assertTrue(any("Hash de confirmación verbal inválido" in error for error in errors))

    def test_render_ledger_surfaces_verbal_confirmation_fields(self):
        events = reseal_events(
            [
                {
                    "event_id": "VAL-STEP-472",
                    "event_type": "human_validation",
                    "occurred_at": "2026-03-26 00:00:00",
                    "actor": {"type": "ai"},
                    "session_id": "codex",
                    "risk_level": "ALTO",
                    "links": {},
                    "payload": {
                        "provider": "OpenAI",
                        "model_version": "GPT-5",
                        "date": "2026-03-26",
                        "linked_reference": "[DEC-0014]",
                        "audit_level": "ALTO",
                        "content_text": 'Agente: "¿Autorizas?"\nTesista: "si. implementa"',
                    },
                    "affected_files": [],
                    "human_validation": {
                        "required": True,
                        "step_id": "VAL-STEP-472",
                        "status": "validated",
                        "validated_at": "2026-03-26",
                        "mode": "Confirmación Verbal",
                    },
                    "prev_event_hash": "",
                    "content_hash": "",
                }
            ]
        )
        ledger = render_ledger(events)
        self.assertIn("Confirmación Verbal (Texto Exacto)", ledger)
        self.assertIn("Fuente de Verdad de Confirmación", ledger)
        self.assertIn('"si. implementa"', ledger)

    def test_projection_paths_include_conversation_source_index(self):
        paths = projection_paths([])
        self.assertIn("00_sistema_tesis/bitacora/indice_fuentes_conversacion.md", paths)

    def test_validate_events_requires_source_event_for_new_steps(self):
        events = reseal_events(
            [
                {
                    "event_id": "VAL-STEP-501",
                    "event_type": "human_validation",
                    "occurred_at": "2026-03-26 00:00:00",
                    "actor": {"type": "ai"},
                    "session_id": "codex",
                    "risk_level": "ALTO",
                    "links": {},
                    "payload": {"content_text": 'Agente: "¿Implemento?"\nTesista: "si"'}, 
                    "affected_files": [],
                    "human_validation": {
                        "required": True,
                        "step_id": "VAL-STEP-501",
                        "status": "validated",
                        "validated_at": "2026-03-26",
                        "mode": "Confirmación Verbal",
                        "confirmation_text": '"si"',
                        "confirmation_text_hash": verbal_confirmation_hash('"si"'),
                    },
                    "prev_event_hash": "",
                    "content_hash": "",
                }
            ]
        )
        errors = validate_events(events)
        self.assertTrue(any("requiere source_event_id" in error for error in errors))

    def test_validate_events_accepts_linked_conversation_source(self):
        quote = '"PLEASE IMPLEMENT THIS PLAN:"'
        events = reseal_events(
            [
                {
                    "event_id": "EVT-0001",
                    "event_type": "conversation_source_registered",
                    "occurred_at": "2026-03-26 00:00:00",
                    "actor": {"type": "system"},
                    "session_id": "codex-1",
                    "risk_level": "ALTO",
                    "links": {},
                    "payload": {
                        "platform": "codex",
                        "client_surface": "vscode_codex",
                        "session_id": "codex-1",
                        "captured_at": "2026-03-26 00:00:00",
                        "transcript_path": "00_sistema_tesis/evidencia_privada/conversaciones_codex/codex-1/transcripcion.md",
                        "transcript_sha256": "a" * 64,
                        "screenshot_paths": ["00_sistema_tesis/evidencia_privada/conversaciones_codex/codex-1/captura_001.png"],
                        "screenshot_hashes": ["b" * 64],
                        "quoted_text": quote,
                        "quoted_text_hash": verbal_confirmation_hash(quote),
                        "message_role": "human",
                        "message_locator": "L10-L12",
                        "capture_method": "manual_transcript_plus_screenshot",
                    },
                    "affected_files": [],
                    "human_validation": {"required": False},
                    "prev_event_hash": "",
                    "content_hash": "",
                },
                {
                    "event_id": "VAL-STEP-501",
                    "event_type": "human_validation",
                    "occurred_at": "2026-03-26 00:01:00",
                    "actor": {"type": "ai"},
                    "session_id": "codex-1",
                    "risk_level": "ALTO",
                    "links": {},
                    "payload": {"content_text": f'Agente: "¿Implemento?"\nTesista: {quote}'},
                    "affected_files": [],
                    "human_validation": {
                        "required": True,
                        "step_id": "VAL-STEP-501",
                        "status": "validated",
                        "validated_at": "2026-03-26",
                        "mode": "Confirmación Verbal",
                        "question_text": '"¿Implemento?"',
                        "confirmation_text": quote,
                        "confirmation_kind": "instruccion_directa",
                        "confirmation_source_type": "campo_canonico_explicito",
                        "confirmation_source_of_truth": "00_sistema_tesis/canon/events.jsonl :: VAL-STEP-501 :: human_validation.confirmation_text",
                        "confirmation_text_hash": verbal_confirmation_hash(quote),
                        "source_event_id": "EVT-0001",
                        "provenance_status": "corroborated_conversation_source",
                        "quote_verification_status": "verified_against_source",
                        "source_capture_required": True,
                    },
                    "prev_event_hash": "",
                    "content_hash": "",
                },
            ]
        )
        self.assertEqual(validate_events(events), [])

    def test_verify_conversation_source_checks_local_artifacts(self):
        quote = '"PLEASE IMPLEMENT THIS PLAN:"'
        with TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            transcript = repo / "evidencia" / "transcripcion.md"
            transcript.parent.mkdir(parents=True, exist_ok=True)
            transcript.write_text(f"# Transcript\n\nUsuario: {quote}\n", encoding="utf-8")
            screenshot = repo / "evidencia" / "captura_001.png"
            screenshot.write_bytes(b"fake-png")
            events = reseal_events(
                [
                    {
                        "event_id": "EVT-0001",
                        "event_type": "conversation_source_registered",
                        "occurred_at": "2026-03-26 00:00:00",
                        "actor": {"type": "system"},
                        "session_id": "codex-1",
                        "risk_level": "ALTO",
                        "links": {},
                        "payload": {
                            "platform": "codex",
                            "client_surface": "vscode_codex",
                            "session_id": "codex-1",
                            "captured_at": "2026-03-26 00:00:00",
                            "transcript_path": "evidencia/transcripcion.md",
                            "transcript_sha256": canon.file_sha256_path(transcript),
                            "screenshot_paths": ["evidencia/captura_001.png"],
                            "screenshot_hashes": [canon.file_sha256_path(screenshot)],
                            "quoted_text": quote,
                            "quoted_text_hash": verbal_confirmation_hash(quote),
                            "message_role": "human",
                            "message_locator": "L3",
                            "capture_method": "manual_transcript_plus_screenshot",
                        },
                        "affected_files": [],
                        "human_validation": {"required": False},
                        "prev_event_hash": "",
                        "content_hash": "",
                    },
                    {
                        "event_id": "VAL-STEP-501",
                        "event_type": "human_validation",
                        "occurred_at": "2026-03-26 00:01:00",
                        "actor": {"type": "ai"},
                        "session_id": "codex-1",
                        "risk_level": "ALTO",
                        "links": {},
                        "payload": {"content_text": f'Agente: "¿Implemento?"\nTesista: {quote}'},
                        "affected_files": [],
                        "human_validation": {
                            "required": True,
                            "step_id": "VAL-STEP-501",
                            "status": "validated",
                            "validated_at": "2026-03-26",
                            "mode": "Confirmación Verbal",
                            "question_text": '"¿Implemento?"',
                            "confirmation_text": quote,
                            "confirmation_kind": "instruccion_directa",
                            "confirmation_source_type": "campo_canonico_explicito",
                            "confirmation_source_of_truth": "00_sistema_tesis/canon/events.jsonl :: VAL-STEP-501 :: human_validation.confirmation_text",
                            "confirmation_text_hash": verbal_confirmation_hash(quote),
                            "source_event_id": "EVT-0001",
                            "provenance_status": "corroborated_conversation_source",
                            "quote_verification_status": "verified_against_source",
                            "source_capture_required": True,
                        },
                        "prev_event_hash": "",
                        "content_hash": "",
                    },
                ]
            )
            with patch.object(canon, "ROOT", repo):
                result = verify_conversation_source_for_step("VAL-STEP-501", events, require_local=True)
        self.assertEqual(result["repo_status"], "ok")
        self.assertEqual(result["local_status"], "ok")


if __name__ == "__main__":
    unittest.main()
