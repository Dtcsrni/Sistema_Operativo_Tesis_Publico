import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

import common  # noqa: E402
import ab_pilot  # noqa: E402
from ab_pilot import aggregate_by_task_type, aggregate_route, build_plan_from_csv, default_execution_context, evaluate_plan, write_csv_template  # noqa: E402


class TestABPilot(unittest.TestCase):
    def test_aggregate_route(self):
        tasks = [
            {
                "task_id": "T-1",
                "task_type": "resumen_capitulo",
                "serena": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cost_usd": 0.01,
                    "latency_ms": 1000,
                    "accepted": True,
                    "gate_failures": 0,
                    "rework": False,
                },
            },
            {
                "task_id": "T-2",
                "task_type": "resumen_capitulo",
                "serena": {
                    "input_tokens": 80,
                    "output_tokens": 40,
                    "cost_usd": 0.015,
                    "latency_ms": 900,
                    "accepted": False,
                    "gate_failures": 1,
                    "rework": True,
                },
            },
        ]

        result = aggregate_route(tasks, "serena")
        self.assertEqual(result.tasks, 2)
        self.assertEqual(result.input_tokens, 180)
        self.assertEqual(result.output_tokens, 90)
        self.assertEqual(result.total_tokens, 270)
        self.assertEqual(result.gate_failures, 1)
        self.assertAlmostEqual(result.total_cost_usd, 0.025)
        self.assertAlmostEqual(result.acceptance_rate, 0.5)
        self.assertAlmostEqual(result.rework_rate, 0.5)

    def test_aggregate_by_task_type(self):
        tasks = [
            {
                "task_id": "T-1",
                "task_type": "resumen_capitulo",
                "serena": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cost_usd": 0.01,
                    "latency_ms": 1000,
                    "accepted": True,
                    "gate_failures": 0,
                    "rework": False,
                },
            },
            {
                "task_id": "T-2",
                "task_type": "analisis_datos",
                "serena": {
                    "input_tokens": 60,
                    "output_tokens": 20,
                    "cost_usd": 0.008,
                    "latency_ms": 800,
                    "accepted": True,
                    "gate_failures": 0,
                    "rework": False,
                },
            },
        ]

        summary = aggregate_by_task_type(tasks)
        self.assertEqual(set(summary.keys()), {"analisis_datos", "resumen_capitulo"})
        self.assertEqual(summary["resumen_capitulo"]["serena"].total_tokens, 150)
        self.assertEqual(summary["analisis_datos"]["serena"].total_tokens, 80)

    def test_evaluate_plan_emits_trace(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            (repo / "00_sistema_tesis" / "config").mkdir(parents=True, exist_ok=True)
            (repo / "00_sistema_tesis" / "bitacora" / "audit_history").mkdir(parents=True, exist_ok=True)
            (repo / "06_dashboard" / "generado").mkdir(parents=True, exist_ok=True)

            plan_path = repo / "00_sistema_tesis" / "config" / "ab_pilot_plan.json"
            plan_path.write_text(
                """
                {
                  "metadata": {"experiment_id": "ab-test"},
                  "criteria": {
                    "primary_objective": "reduce_tokens_cost",
                    "min_cost_reduction_pct": 25.0,
                    "min_token_reduction_pct": 20.0,
                    "min_acceptance_rate": 0.9,
                    "max_gate_failures": 0
                  },
                  "tasks": [
                    {
                      "task_id": "T-1",
                      "task_type": "resumen_capitulo",
                      "serena": {"input_tokens": 100, "output_tokens": 50, "cost_usd": 0.01, "latency_ms": 1000, "accepted": true, "gate_failures": 0, "rework": false}
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )

            with patch.object(ab_pilot, "ROOT", repo), patch.object(common, "ROOT", repo):
                report_path, markdown_path, trace_path, report_payload = evaluate_plan(
                    plan_relative_path="00_sistema_tesis/config/ab_pilot_plan.json",
                    report_relative_path="00_sistema_tesis/config/ab_pilot_report.json",
                    markdown_relative_path="06_dashboard/generado/ab_pilot_report.md",
                    trace_relative_path="00_sistema_tesis/bitacora/audit_history/ab_pilot_runs.jsonl",
                    context=ab_pilot.ExecutionContext(session_id="sesion-1", step_id="VAL-STEP-999", source_event_id="EVT-0001"),
                )

            self.assertTrue(report_path.exists())
            self.assertTrue(markdown_path.exists())
            self.assertTrue(trace_path.exists())
            self.assertEqual(report_payload["execution_context"]["session_id"], "sesion-1")
            self.assertIn("resumen_capitulo", report_payload["by_task_type"])
            trace_rows = trace_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertEqual(len(trace_rows), 1)
            self.assertIn("VAL-STEP-999", trace_rows[0])

    def test_default_execution_context(self):
        context = default_execution_context()
        self.assertTrue(context.session_id)

    def test_write_csv_template(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            with patch.object(ab_pilot, "ROOT", repo), patch.object(common, "ROOT", repo):
                csv_path = write_csv_template("00_sistema_tesis/plantillas/ab_pilot_tasks_template.csv")
            self.assertTrue(csv_path.exists())
            content = csv_path.read_text(encoding="utf-8")
            self.assertIn("serena_input_tokens", content)
            self.assertNotIn("modular_", content)
            self.assertNotIn("manual_", content)

    def test_build_plan_from_csv(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            (repo / "input").mkdir(parents=True, exist_ok=True)
            csv_path = repo / "input" / "tasks.csv"
            csv_path.write_text(
                """task_id,task_type,baseline_complexity,serena_input_tokens,serena_output_tokens,serena_cost_usd,serena_latency_ms,serena_accepted,serena_gate_failures,serena_rework
T-1,documentacion,baja,100,50,0.01,1000,true,0,false
T-2,analisis,alta,80,40,0.015,900,true,0,false
""",
                encoding="utf-8",
            )

            with patch.object(ab_pilot, "ROOT", repo), patch.object(common, "ROOT", repo):
                plan_path = build_plan_from_csv(
                    csv_relative_path="input/tasks.csv",
                    plan_relative_path="00_sistema_tesis/config/ab_pilot_plan.json",
                    experiment_id="ab-csv-test",
                    owner="tesista",
                )

            self.assertTrue(plan_path.exists())
            payload = plan_path.read_text(encoding="utf-8")
            self.assertIn("ab-csv-test", payload)
            self.assertIn("documentacion", payload)
            self.assertIn("analisis", payload)
            self.assertNotIn("modular", payload)
            self.assertNotIn("manual", payload)

    def test_build_plan_from_csv_rejects_bad_boolean(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            csv_path = repo / "tasks.csv"
            csv_path.write_text(
                "task_id,task_type,baseline_complexity,serena_input_tokens,serena_output_tokens,serena_cost_usd,serena_latency_ms,serena_accepted,serena_gate_failures,serena_rework\n"
                "T-1,documentacion,baja,100,50,0.01,1000,maybe,0,false\n",
                encoding="utf-8",
            )

            with patch.object(ab_pilot, "ROOT", repo), patch.object(common, "ROOT", repo):
                with self.assertRaises(ab_pilot.ValidationError):
                    build_plan_from_csv(
                        csv_relative_path="tasks.csv",
                        plan_relative_path="plan.json",
                    )


if __name__ == "__main__":
    unittest.main()
