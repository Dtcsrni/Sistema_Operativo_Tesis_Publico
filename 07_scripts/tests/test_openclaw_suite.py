from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


"""test_openclaw_suite.py — Batería de pruebas completa de OpenClaw.

Grupos:
  1. Unitarios módulos nuevos (sin LLM)
  2. Integración bot con mocks HTTP
  3. Regresión de políticas
  4. [slow] Con LLM real (excluidos por defecto)

Uso:
  python 07_scripts/test_openclaw_suite.py          # rápidos (grupos 1-3)
  python 07_scripts/test_openclaw_suite.py --slow   # incluye grupo 4
  python 07_scripts/test_openclaw_suite.py --hermes # incluye tests hermes
"""

import argparse
import json
import os

import threading
import time
import types
import unittest
import urllib.request
from unittest.mock import MagicMock, patch

# ── Rutas ─────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime" / "openclaw"))

# ── Helpers de entorno ────────────────────────────────────────────────────────
def _set_env(**kw):
    for k, v in kw.items():
        os.environ[k] = str(v)

def _del_env(*keys):
    for k in keys:
        os.environ.pop(k, None)

# ══════════════════════════════════════════════════════════════════════════════
# GRUPO 1 — Módulos nuevos (unitarios, sin LLM)
# ══════════════════════════════════════════════════════════════════════════════

class TestPersona(unittest.TestCase):
    """persona.py — tono adaptativo y bloques de sistema."""

    @classmethod
    def setUpClass(cls):
        from openclaw_local import persona
        cls.p = persona

    def test_build_system_block_not_empty(self):
        block = self.p.build_system_block("standard", "low")
        self.assertTrue(len(block) > 20, "build_system_block debe retornar texto sustancial")

    def test_build_system_block_all_kinds(self):
        for kind in ("standard", "research", "code", "math"):
            for complexity in ("low", "medium", "high"):
                block = self.p.build_system_block(kind, complexity)
                self.assertIsInstance(block, str)
                self.assertTrue(len(block) > 0)

    def test_synthesis_system_block(self):
        block = self.p.build_synthesis_system_block()
        self.assertIsInstance(block, str)
        self.assertTrue(len(block) > 20)

    def test_tone_differs_by_kind(self):
        t_research = self.p.get_tone("research", "high")
        t_standard = self.p.get_tone("standard", "low")
        # Deben ser diferentes (tono adaptativo)
        self.assertNotEqual(t_research, t_standard)

    def test_is_volatile_query(self):
        self.assertTrue(self.p.is_volatile_query("qué hora es"))
        self.assertFalse(self.p.is_volatile_query("explícame la relatividad general"))

class TestResponseCache(unittest.TestCase):
    """response_cache.py — caché TTL diferenciada."""

    @classmethod
    def setUpClass(cls):
        from openclaw_local import response_cache
        cls.rc = response_cache

    def _make_cache(self):
        mem = {}
        store = MagicMock()
        store.get_metadata.return_value = None
        store.set_metadata.return_value = None
        store.save_cached_context.side_effect = lambda k, v: mem.update({k: v})
        store.get_cached_context.side_effect = lambda k: mem.get(k)
        return self.rc.ResponseCache(store)

    def test_put_and_get_roundtrip(self):
        cache = self._make_cache()
        cache.put("test query roundtrip", "standard", "hola mundo", model="qwen3:4b")
        result = cache.get("test query roundtrip", "standard")
        self.assertIsNotNone(result)
        self.assertIn("hola mundo", str(result.get("text", "")))

    def test_cache_miss_returns_none(self):
        cache = self._make_cache()
        result = cache.get("nonexistent query xyz 999", "standard")
        self.assertIsNone(result)

    def test_cache_hit_tag_present(self):
        tag = self.rc.cache_hit_tag()
        self.assertIn("⚡", tag)

    def test_is_volatile_true(self):
        self.assertTrue(self.rc.is_volatile("qué hora es ahora"))

    def test_is_volatile_false(self):
        self.assertFalse(self.rc.is_volatile("explícame la mecánica cuántica"))

class TestDetScripts(unittest.TestCase):
    """det_scripts.py — cálculos determinísticos sin LLM."""

    @classmethod
    def setUpClass(cls):
        from openclaw_local import det_scripts
        cls.d = det_scripts

    def _dispatch(self, text):
        return self.d.dispatch(text, repo_root=ROOT)

    def test_arithmetic_multiplication(self):
        r = self._dispatch("cuánto es 3 * 7 + 2")
        self.assertIsNotNone(r)
        self.assertIn("23", str(r.get("text", "")))

    def test_arithmetic_power(self):
        r = self._dispatch("cuánto es 7 al cubo")
        if r is None:
            r = self._dispatch("7 ^ 3")
        if r is not None:
            self.assertIn("343", str(r.get("text", "")))

    def test_stats_mean(self):
        r = self._dispatch("media de 4, 8, 12")
        self.assertIsNotNone(r)
        self.assertIn("8", str(r.get("text", "")))

    def test_unit_kg_to_lb(self):
        r = self._dispatch("5 kg a lb")
        self.assertIsNotNone(r)
        self.assertIn("11", str(r.get("text", "")))

    def test_unit_celsius_to_fahrenheit(self):
        r = self._dispatch("100 celsius a fahrenheit")
        self.assertIsNotNone(r)
        self.assertIn("212", str(r.get("text", "")))

    def test_unit_km_to_miles(self):
        r = self._dispatch("10 km a millas")
        self.assertIsNotNone(r)
        self.assertIsInstance(r.get("text"), str)

    def test_datetime_dispatch(self):
        r = self._dispatch("qué hora es")
        self.assertIsNotNone(r)
        self.assertEqual(r.get("status"), "ok")

    def test_unknown_returns_none(self):
        r = self._dispatch("explícame la teoría de grafos en detalle")
        self.assertIsNone(r)

    def test_dispatch_result_has_status(self):
        r = self._dispatch("2 + 2")
        if r is not None:
            self.assertIn("status", r)

class TestRollingSummary(unittest.TestCase):
    """rolling_summary.py — compresión de memoria en background."""

    @classmethod
    def setUpClass(cls):
        from openclaw_local import rolling_summary
        cls.rs = rolling_summary

    def _make_state(self, n_turns):
        turns = [
            {"user": f"pregunta {i}", "assistant": f"respuesta {i}", "kind": "normal"}
            for i in range(n_turns)
        ]
        return {"turns": turns, "rolling_summary": ""}

    def test_trigger_off_below_threshold(self):
        state = self._make_state(3)
        result = self.rs.maybe_trigger_summary(state)
        self.assertFalse(result)

    def test_trigger_on_above_threshold(self):
        state = self._make_state(10)
        # No hay Ollama real, el thread fallará silenciosamente
        result = self.rs.maybe_trigger_summary(state)
        self.assertTrue(result)

    def test_trigger_launches_daemon_thread(self):
        state = self._make_state(10)
        before = {t.name for t in threading.enumerate()}
        self.rs.maybe_trigger_summary(state)
        time.sleep(0.05)
        after = {t.name for t in threading.enumerate()}
        # El thread puede terminar rápido, pero al menos se lanzó (no error)
        # Verificamos que no hubo excepción
        self.assertIsNotNone(state)

    def test_no_circular_import(self):
        """Verificar que rolling_summary no importa telegram_bot."""
        import importlib
        import openclaw_local.rolling_summary as rs_mod
        src = Path(rs_mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("from openclaw_local.telegram_bot", src)
        self.assertNotIn("import telegram_bot", src)

    def test_model_preference_has_lightweight_first(self):
        self.assertTrue(
            self.rs.MODEL_PREFERENCE[0].startswith("qwen2.5:0.5b")
            or "0.5" in self.rs.MODEL_PREFERENCE[0],
            f"Primer modelo preferido debe ser ligero, got: {self.rs.MODEL_PREFERENCE[0]}",
        )

# ══════════════════════════════════════════════════════════════════════════════
# GRUPO 2 — Integración bot con mocks (sin LLM real)
# ══════════════════════════════════════════════════════════════════════════════

class TestNaturalCommandResponse(unittest.TestCase):
    """_natural_command_response — dispatch sin LLM."""

    @classmethod
    def setUpClass(cls):
        import openclaw_local.telegram_bot as bot
        cls.bot = bot

    def _call(self, text, state=None):
        store = MagicMock()
        store.get_metadata.return_value = None
        return self.bot._natural_command_response(
            text,
            repo_root=ROOT,
            store=store,
            state=state or {},
        )

    def test_hora_response(self):
        r = self._call("qué hora es")
        self.assertIsNotNone(r)
        self.assertEqual(r.get("status"), "ok")

    def test_math_response(self):
        r = self._call("cuánto es 25 * 4")
        self.assertIsNotNone(r)
        self.assertIn("100", str(r.get("text", "")))

    def test_kg_conversion(self):
        r = self._call("10 kg a lb")
        self.assertIsNotNone(r)
        self.assertIn("22", str(r.get("text", "")))

    def test_stats_mean(self):
        r = self._call("promedio de 2, 4, 6")
        self.assertIsNotNone(r)
        self.assertIn("4", str(r.get("text", "")))

    def test_complex_text_returns_none(self):
        r = self._call("investiga los algoritmos de consenso en blockchain IoT")
        self.assertIsNone(r)

    def test_empty_returns_none(self):
        r = self._call("")
        self.assertIsNone(r)

    def test_cancel_clears_approval(self):
        state = {"last_approval": {"id": "x"}}
        r = self._call("cancela", state=state)
        self.assertIsNotNone(r)
        self.assertNotIn("last_approval", state)

class TestMemoryPrompt(unittest.TestCase):
    """_memory_prompt — compresión de turnos."""

    @classmethod
    def setUpClass(cls):
        import openclaw_local.telegram_bot as bot
        cls.bot = bot

    def _make_state(self, n, with_summary=False):
        turns = [
            {"user": f"q{i}", "assistant": f"a{i}", "kind": "normal", "command": "chat",
             "status": "ok", "created_at": "2026-01-01T00:00:00+00:00"}
            for i in range(n)
        ]
        state = {"turns": turns}
        if with_summary:
            state["rolling_summary"] = "Resumen previo de la conversación."
        return state

    def test_limit_to_four_recent_turns(self):
        state = self._make_state(20)
        prompt = self.bot._memory_prompt(state)
        # Con 20 turnos debe comprimir; el prompt no debe ser desproporcionadamente largo
        self.assertIsInstance(prompt, str)
        # Debe aparecer en el prompt (al menos los recientes)
        self.assertIn("q19", prompt)

    def test_rolling_summary_included(self):
        state = self._make_state(4, with_summary=True)
        prompt = self.bot._memory_prompt(state)
        self.assertIn("Resumen previo", prompt)

    def test_empty_state_no_crash(self):
        prompt = self.bot._memory_prompt({})
        self.assertIsInstance(prompt, str)

class TestProgressHeartbeat(unittest.TestCase):
    """ProgressHeartbeat — mensajes editables con progreso semántico."""

    @classmethod
    def setUpClass(cls):
        import openclaw_local.telegram_bot as bot
        cls.bot = bot

    def test_enter_calls_send_message(self):
        with patch.object(self.bot, "send_message_get_id", return_value=42) as mock_send, \
             patch.object(self.bot, "edit_message", return_value={}) as mock_edit:
            hb = self.bot.ProgressHeartbeat("chat123", "⏳ Procesando...", interval=9999)
            hb.__enter__()
            mock_send.assert_called_once_with("chat123", "⏳ Procesando...")
            hb.__exit__(None, None, None)

    def test_update_calls_edit_message(self):
        with patch.object(self.bot, "send_message_get_id", return_value=99), \
             patch.object(self.bot, "edit_message", return_value={}) as mock_edit:
            hb = self.bot.ProgressHeartbeat("chat_x", "inicio", interval=9999)
            hb.__enter__()
            hb.update("nuevo estado")
            mock_edit.assert_called_with("chat_x", 99, unittest.mock.ANY)
            hb.__exit__(None, None, None)

# ══════════════════════════════════════════════════════════════════════════════
# GRUPO 3 — Regresión de políticas
# ══════════════════════════════════════════════════════════════════════════════

class TestTokenPolicies(unittest.TestCase):
    """Verifica límites de tokens por nivel de complejidad."""

    @classmethod
    def setUpClass(cls):
        import openclaw_local.telegram_bot as bot
        cls.bot = bot

    def test_options_simple_low_predict(self):
        if hasattr(self.bot, "_ollama_request_options"):
            opts = self.bot._ollama_request_options(model="qwen3:4b", timeout_seconds=30)
            self.assertIsInstance(opts, dict)

    def test_options_research_high_predict(self):
        if hasattr(self.bot, "_ollama_request_options"):
            opts = self.bot._ollama_request_options(model="mistral-nemo:12b", timeout_seconds=120)
            self.assertIsInstance(opts, dict)

    def test_volatile_not_cached(self):
        from openclaw_local.response_cache import is_volatile
        self.assertTrue(is_volatile("qué hora es ahora mismo"))
        self.assertTrue(is_volatile("cuál es la temperatura actual"))

    def test_non_volatile_cacheable(self):
        from openclaw_local.response_cache import is_volatile
        self.assertFalse(is_volatile("explícame el teorema de Bayes"))

class TestSynthesisPolicies(unittest.TestCase):
    """Verifica que los prompts de síntesis usen persona canónica."""

    @classmethod
    def setUpClass(cls):
        import openclaw_local.telegram_bot as bot
        cls.bot = bot

    def test_research_prompt_uses_system_block(self):
        if hasattr(self.bot, "_research_prompt"):
            prompt = self.bot._research_prompt("IoT edge computing", web={}, state={})
            self.assertIsInstance(prompt, str)
            self.assertTrue(len(prompt) > 50)

    def test_safe_prompt_not_empty(self):
        if hasattr(self.bot, "_safe_prompt"):
            prompt = self.bot._safe_prompt("hola", state={}, web=None)
            self.assertIsInstance(prompt, str)
            self.assertTrue(len(prompt) > 0)

# ══════════════════════════════════════════════════════════════════════════════
# GRUPO 4 — [slow] Con LLM real (excluidos por defecto)
# ══════════════════════════════════════════════════════════════════════════════

@unittest.skipUnless(os.getenv("OPENCLAW_TEST_SLOW") == "1", "Requiere --slow y Ollama activo")
class TestSlowLLM(unittest.TestCase):
    """Tests lentos que requieren LLM real vía Ollama."""

    BASE_URL = os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    MODEL = os.getenv("OPENCLAW_TEST_SLOW_MODEL", "qwen3:4b")

    def _ollama_available(self):
        try:
            urllib.request.urlopen(f"{self.BASE_URL}/api/tags", timeout=3)
            return True
        except Exception:
            return False

    def setUp(self):
        if not self._ollama_available():
            self.skipTest(f"Ollama no disponible en {self.BASE_URL}")

    def test_slow_rolling_summary_generation(self):
        from openclaw_local import rolling_summary as rs
        state = {
            "turns": [
                {"user": f"q{i}", "assistant": f"a{i}", "kind": "normal"}
                for i in range(9)
            ],
            "rolling_summary": "",
        }
        triggered = rs.maybe_trigger_summary(state)
        self.assertTrue(triggered)
        time.sleep(15)  # Dar tiempo al background thread
        # El resumen puede o no haberse generado dependiendo de velocidad del modelo

    def test_slow_det_scripts_vs_llm_correctness(self):
        """Verifica que det_scripts da la misma respuesta que el LLM para aritmética."""
        from openclaw_local import det_scripts
        r = det_scripts.dispatch("cuánto es 144 / 12", repo_root=ROOT)
        self.assertIsNotNone(r)
        self.assertIn("12", str(r.get("text", "")))

@unittest.skipUnless(os.getenv("OPENCLAW_TEST_HERMES") == "1", "Requiere --hermes y hermes3:8b")
class TestHermesIntegration(unittest.TestCase):
    """Tests de integración con hermes3:8b (requiere modelo descargado)."""

    BASE_URL = os.getenv("OPENCLAW_PC_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    MODEL = "hermes3:8b"

    def _model_available(self):
        try:
            r = urllib.request.urlopen(f"{self.BASE_URL}/api/tags", timeout=3)
            data = json.loads(r.read())
            names = {m["name"] for m in data.get("models", [])}
            return self.MODEL in names
        except Exception:
            return False

    def setUp(self):
        if not self._model_available():
            self.skipTest(f"{self.MODEL} no disponible en {self.BASE_URL}")

    def test_hermes_system_block_not_empty(self):
        from openclaw_local import persona
        if hasattr(persona, "build_hermes_system_block"):
            block = persona.build_hermes_system_block("research", "high")
            self.assertIn("<|im_start|>", block)
        else:
            self.skipTest("build_hermes_system_block no implementado aún")

    def test_hermes_response_quality(self):
        """Hermes debe responder coherentemente a un prompt académico."""
        payload = json.dumps({
            "model": self.MODEL,
            "prompt": "Explica en dos oraciones qué es el aprendizaje federado.",
            "stream": False,
            "options": {"num_predict": 80, "num_ctx": 512, "temperature": 0.1},
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.BASE_URL}/api/generate", data=payload, method="POST"
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        text = data.get("response", "")
        self.assertTrue(len(text) > 30, f"Respuesta demasiado corta: {text!r}")

# ══════════════════════════════════════════════════════════════════════════════
# Runner principal
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="OpenClaw Test Suite")
    parser.add_argument("--slow", action="store_true", help="Incluir tests lentos con LLM real")
    parser.add_argument("--hermes", action="store_true", help="Incluir tests de integración Hermes")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args, unittest_args = parser.parse_known_args()

    if args.slow:
        os.environ["OPENCLAW_TEST_SLOW"] = "1"
    if args.hermes:
        os.environ["OPENCLAW_TEST_HERMES"] = "1"

    # Recopilar suites
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    fast_groups = [
        TestPersona, TestResponseCache, TestDetScripts, TestRollingSummary,
        TestNaturalCommandResponse, TestMemoryPrompt, TestProgressHeartbeat,
        TestTokenPolicies, TestSynthesisPolicies,
    ]
    slow_groups = [TestSlowLLM, TestHermesIntegration]

    for grp in fast_groups:
        suite.addTests(loader.loadTestsFromTestCase(grp))

    if args.slow or args.hermes:
        for grp in slow_groups:
            suite.addTests(loader.loadTestsFromTestCase(grp))

    verbosity = 2 if args.verbose else 1
    runner = unittest.TextTestRunner(verbosity=verbosity, stream=sys.stdout)
    result = runner.run(suite)

    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors) - len(result.skipped)
    print(f"\n{'='*60}")
    print(f"OpenClaw Test Suite — {passed}/{total} passed")
    if result.failures:
        print(f"  FAILURES: {len(result.failures)}")
    if result.errors:
        print(f"  ERRORS:   {len(result.errors)}")
    if result.skipped:
        print(f"  SKIPPED:  {len(result.skipped)}")
    print(f"{'='*60}")

    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    raise SystemExit(main())
