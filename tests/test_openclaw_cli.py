from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "runtime" / "openclaw" / "bin" / "openclaw_local.py"


def _write_domain_envs(tmp_path: Path) -> Path:
    domains_dir = tmp_path / "domains"
    domains_dir.mkdir(parents=True)
    (domains_dir / "personal.env").write_text("", encoding="utf-8")
    (domains_dir / "profesional.env").write_text("GROQ_API_KEY=groq-prof\nOPENAI_API_KEY=openai-prof\n", encoding="utf-8")
    (domains_dir / "academico.env").write_text(
        "GROQ_API_KEY=groq-acad\nGEMINI_API_KEY=gemini-acad\nOPENAI_API_KEY=openai-acad\nOPENCLAW_GEMINI_STUDENT_ENABLED=1\nOPENCLAW_CHATGPT_PLUS_ENABLED=1\n",
        encoding="utf-8",
    )
    (domains_dir / "edge.env").write_text("", encoding="utf-8")
    (domains_dir / "administrativo.env").write_text("", encoding="utf-8")
    return domains_dir


def test_openclaw_doctor_reports_domains_and_store(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path)
    env["OPENCLAW_CACHE_DIR"] = str(tmp_path / "cache")
    env["OPENCLAW_LOG_DIR"] = str(tmp_path / "log")
    env["OPENCLAW_ENV_FILE"] = str(tmp_path / "openclaw.env")
    env["OPENCLAW_DOMAINS_ENV_DIR"] = str(_write_domain_envs(tmp_path))
    env["OPENCLAW_FORCE_ORANGE_PI_MODEL"] = "Orange Pi 5 Plus"
    env["OPENCLAW_FORCE_ROOT_DEVICE"] = "/dev/nvme0n1p1"
    env["OPENCLAW_FORCE_OLLAMA_READY"] = "1"
    Path(env["OPENCLAW_CACHE_DIR"]).mkdir()
    Path(env["OPENCLAW_LOG_DIR"]).mkdir()
    Path(env["OPENCLAW_ENV_FILE"]).write_text("OPENCLAW_PORT=18789\n", encoding="utf-8")
    result = subprocess.run(
        [".venv/bin/python.exe", str(CLI), "doctor"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["deployment_state"] == "ollama_ready"
    assert "academico" in payload["domains"]
    assert "local" in payload["proveedores"]
    assert payload["store"]["db_path"].endswith("openclaw.db")
    assert payload["secretos"]["domains"]["academico"]["providers"]["gemini_api"]["status"] == "ready"
    assert "gemini-acad" not in result.stdout


def test_openclaw_run_dry_run_creates_approval_for_mutation(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path)
    env["OPENCLAW_DOMAINS_ENV_DIR"] = str(_write_domain_envs(tmp_path))
    result = subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "ejecutar",
            "--simulacion",
            "--id-tarea",
            "TASK-CLI-001",
            "--titulo",
            "Borrador arquitectónico",
            "--dominio",
            "academico",
            "--objetivo",
            "Preparar diff sin publicar",
            "--complejidad",
            "high",
            "--nivel-riesgo",
            "high",
            "--muta-estado",
            "--rutas-objetivo",
            "docs/02_arquitectura/openclaw-control-plane.md",
            "--step-id-esperado",
            "VAL-STEP-901",
            "--requiere-evidencia-fuente",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert payload["dry_run"] is True
    assert payload["decision"]["requires_human_gate"] is True
    assert payload["approval_id"].startswith("APR-")
    assert payload["decision"]["provider"] == "gemini_api"
    assert payload["serena"]["status"] == "ok"
    assert "context.fetch_compact" in payload["serena"]["tool_invocations"]
    assert "governance.preflight" in payload["serena"]["tool_invocations"]


def test_openclaw_run_blocks_when_serena_is_required_and_unavailable(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path)
    env["OPENCLAW_DOMAINS_ENV_DIR"] = str(_write_domain_envs(tmp_path))
    env["OPENCLAW_SERENA_TRANSPORT"] = "http"
    env["OPENCLAW_SERENA_URL"] = "http://127.0.0.1:9/mcp"
    env["OPENCLAW_SERENA_TIMEOUT_MS"] = "300"
    result = subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "ejecutar",
            "--id-tarea",
            "TASK-CLI-001B",
            "--titulo",
            "Cambio controlado",
            "--dominio",
            "academico",
            "--objetivo",
            "Preparar cambio con Serena obligatoria",
            "--complejidad",
            "high",
            "--nivel-riesgo",
            "high",
            "--muta-estado",
            "--rutas-objetivo",
            "docs/02_arquitectura/openclaw-control-plane.md",
            "--modo-serena",
            "required",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["serena"]["status"] == "unavailable"
    assert payload["serena"]["blocked"] is True


def test_openclaw_proposal_export_writes_draft_to_canon(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path / "openclaw")
    env["OPENCLAW_DOMAINS_ENV_DIR"] = str(_write_domain_envs(tmp_path))
    result_run = subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "ejecutar",
            "--simulacion",
            "--id-tarea",
            "TASK-CLI-002",
            "--titulo",
            "Propuesta exportable",
            "--dominio",
            "academico",
            "--objetivo",
            "Preparar draft para canon",
            "--complejidad",
            "high",
            "--nivel-riesgo",
            "high",
            "--muta-estado",
            "--rutas-objetivo",
            "docs/02_arquitectura/openclaw-control-plane.md",
            "--step-id-esperado",
            "VAL-STEP-902",
            "--requiere-evidencia-fuente",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    payload_run = json.loads(result_run.stdout)

    result_export = subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "propuesta",
            "exportar",
            "--simulacion",
            "--id-tarea",
            "TASK-CLI-002",
            "--id-sesion",
            "SESSION-CLI-002",
            "--referencia-vinculada",
            "[DEC-0020]",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload_export = json.loads(result_export.stdout)
    assert payload_export["event"]["event_type"] == "openclaw_proposal"
    assert payload_export["event"]["payload"]["proposal_status"] == "draft_pending_human_review"
    assert payload_run["approval_id"].startswith("APR-")


def test_openclaw_prepare_validation_package_contains_canonical_commands(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path / "openclaw")
    env["OPENCLAW_DOMAINS_ENV_DIR"] = str(_write_domain_envs(tmp_path))
    subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "ejecutar",
            "--simulacion",
            "--id-tarea",
            "TASK-CLI-003",
            "--titulo",
            "Preparar validación",
            "--dominio",
            "academico",
            "--objetivo",
            "Preparar paquete de aprobación humana",
            "--complejidad",
            "high",
            "--nivel-riesgo",
            "high",
            "--muta-estado",
            "--rutas-objetivo",
            "docs/02_arquitectura/openclaw-control-plane.md",
            "--step-id-esperado",
            "VAL-STEP-903",
            "--requiere-evidencia-fuente",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    result = subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "propuesta",
            "preparar-validacion",
            "--id-tarea",
            "TASK-CLI-003",
            "--id-sesion",
            "SESSION-CLI-003",
            "--referencia-vinculada",
            "[DEC-0020]",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert payload["step_id"] == "VAL-STEP-903"
    assert "source scaffold" in payload["commands"]["scaffold"]
    assert "finalize-openclaw" in payload["commands"]["finalize"]


def test_openclaw_academic_literature_builds_packet_and_cache(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path / "openclaw")
    env["OPENCLAW_DOMAINS_ENV_DIR"] = str(_write_domain_envs(tmp_path))
    input_path = tmp_path / "literature.json"
    input_path.write_text(
        json.dumps(
            {
                "sources": ["doi:10.1000/test"],
                "traceability_links": ["[DEC-0014]"],
                "claims": [
                    {
                        "claim_id": "CLM-001",
                        "claim_text": "Existe contradicción relevante.",
                        "classification": "inferencia_razonada",
                        "source_refs": ["doi:10.1000/test"],
                        "confidence": "alto",
                        "verification_status": "fuente_primaria",
                        "impact_on_thesis": "Ajusta la hipótesis.",
                    }
                ],
                "literature_records": [
                    {
                        "record_id": "LIT-001",
                        "tema": "Intermitencia",
                        "pregunta": "¿Qué contradicciones hay?",
                        "fuente": "Fuente primaria",
                        "anio": "2025",
                        "doi": "10.1000/test",
                        "nivel_evidencia": "alto",
                        "hallazgos_clave": ["Hallazgo 1"],
                        "contradicciones": ["Contradicción A"],
                        "relacion_con_hipotesis": "Afecta el diseño.",
                        "estado_verificacion": "verificado",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "academico",
            "estado-del-arte",
            "--id-tarea",
            "TASK-ACA-CLI-001",
            "--titulo",
            "Estado del arte",
            "--objetivo",
            "Triage de literatura",
            "--pregunta",
            "¿Qué contradicciones importan?",
            "--alcance",
            "Fuentes primarias",
            "--archivo-entrada-json",
            str(input_path),
            "--id-sesion",
            "SESSION-ACA-001",
            "--step-id-esperado",
            "VAL-STEP-950",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert payload["task"]["extra_context"]["academic_mode"] == "estado_del_arte"
    assert payload["cache_hit"] is False
    assert "matriz-de-literatura.md" in " ".join(payload["artifacts"])
    assert payload["serena"]["status"] == "ok"
    assert payload["serena"]["references"]


def test_openclaw_academic_writing_materializes_parallel_outputs(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path / "openclaw")
    env["OPENCLAW_DOMAINS_ENV_DIR"] = str(_write_domain_envs(tmp_path))
    input_path = tmp_path / "writing.json"
    input_path.write_text(
        json.dumps(
            {
                "sources": ["doi:10.1000/test"],
                "traceability_links": ["[DEC-0020]"],
                "claims": [
                    {
                        "claim_id": "CLM-101",
                        "claim_text": "El problema requiere resiliencia.",
                        "classification": "pendiente_de_validacion",
                        "source_refs": ["doi:10.1000/test"],
                        "confidence": "medio",
                        "verification_status": "pendiente_de_validacion",
                        "impact_on_thesis": "Introduce el problema.",
                    }
                ],
                "writing_draft": {
                    "section_id": "introduccion_openclaw_test",
                    "purpose": "Introducción",
                    "source_refs": ["doi:10.1000/test"],
                    "open_questions": ["Cerrar objetivo específico"],
                    "paragraphs": [
                        {
                            "text": "La tesis aborda resiliencia en telemetría urbana.",
                            "source_refs": ["doi:10.1000/test"],
                        },
                        {
                            "text": "Esta síntesis conecta el problema con la motivación experimental.",
                            "non_factual": True,
                        },
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "academico",
            "redaccion",
            "--id-tarea",
            "TASK-ACA-CLI-002",
            "--titulo",
            "Borrador introducción",
            "--objetivo",
            "Preparar introducción trazable",
            "--pregunta",
            "¿Cómo abrir la tesis?",
            "--alcance",
            "Capítulo de introducción",
            "--archivo-entrada-json",
            str(input_path),
            "--id-sesion",
            "SESSION-ACA-002",
            "--step-id-esperado",
            "VAL-STEP-951",
            "--escribir-artefactos",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    md_path = ROOT / "runtime" / "openclaw" / "state" / "academico" / "drafts" / "introduccion_openclaw_test.md"
    tex_path = ROOT / "05_tesis_latex" / "sections" / "introduccion_openclaw_test.tex"

    try:
        assert payload["approval_id"].startswith("APR-")
        assert md_path.exists()
        assert tex_path.exists()
        assert "Fuentes: doi:10.1000/test" in md_path.read_text(encoding="utf-8")
        assert "\\textit{Fuentes: doi:10.1000/test}." in tex_path.read_text(encoding="utf-8")
    finally:
        if md_path.exists():
            md_path.unlink()
        if tex_path.exists():
            tex_path.unlink()


def test_openclaw_academic_export_proposal_includes_academic_metadata(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path / "openclaw")
    input_path = tmp_path / "methodology.json"
    input_path.write_text(
        json.dumps(
            {
                "sources": ["fuente-a.md"],
                "traceability_links": ["[DEC-0014]"],
                "summary": "Comparación metodológica inicial.",
                "claims": [
                    {
                        "claim_id": "CLM-201",
                        "claim_text": "El enfoque comparativo es adecuado.",
                        "classification": "recomendacion_tentativa",
                        "source_refs": ["fuente-a.md"],
                        "confidence": "medio",
                        "verification_status": "pendiente_de_validacion",
                        "impact_on_thesis": "Ayuda a decidir el marco metodológico.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "academico",
            "metodologia",
            "--id-tarea",
            "TASK-ACA-CLI-003",
            "--titulo",
            "Paquete metodológico",
            "--objetivo",
            "Comparar enfoques",
            "--pregunta",
            "¿Qué enfoque es más defendible?",
            "--alcance",
            "Primera iteración",
            "--archivo-entrada-json",
            str(input_path),
            "--id-sesion",
            "SESSION-ACA-003",
            "--step-id-esperado",
            "VAL-STEP-952",
            "--cambia-metodologia",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    result = subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "academico",
            "exportar-propuesta",
            "--id-tarea",
            "TASK-ACA-CLI-003",
            "--id-sesion",
            "SESSION-ACA-003",
            "--simulacion",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert payload["event"]["payload"]["academic_mode"] == "metodologia"
    assert payload["event"]["payload"]["scientific_support_summary"] == "Comparación metodológica inicial."


def test_openclaw_provider_status_and_benchmark_reflect_local_runtimes(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path / "openclaw")
    env["OPENCLAW_CACHE_DIR"] = str(tmp_path / "cache")
    env["OPENCLAW_LOG_DIR"] = str(tmp_path / "log")
    env["OPENCLAW_ENV_FILE"] = str(tmp_path / "openclaw.env")
    env["OPENCLAW_DOMAINS_ENV_DIR"] = str(_write_domain_envs(tmp_path))
    env["OPENCLAW_FORCE_OLLAMA_READY"] = "1"
    env["OPENCLAW_FORCE_NPU_READY"] = "1"
    env["OPENCLAW_BENCHMARK_SIMULATION"] = "1"
    Path(env["OPENCLAW_CACHE_DIR"]).mkdir(parents=True)
    Path(env["OPENCLAW_LOG_DIR"]).mkdir(parents=True)
    Path(env["OPENCLAW_ENV_FILE"]).write_text("OPENCLAW_PORT=18789\n", encoding="utf-8")

    status = subprocess.run(
        [".venv/bin/python.exe", str(CLI), "proveedor", "estado"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    benchmark = subprocess.run(
        [".venv/bin/python.exe", str(CLI), "proveedor", "medir"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    status_payload = json.loads(status.stdout)
    benchmark_payload = json.loads(benchmark.stdout)

    assert status_payload["runtime_status"]["state"] == "npu_experimental_ready"
    assert benchmark_payload["active_runtime"] == "ollama_local"
    assert benchmark_payload["recommended_runtime"] == "rknn_llm_experimental"
    assert status_payload["secretos"]["domains"]["profesional"]["providers"]["groq_api"]["status"] == "ready"


def test_openclaw_gateway_preflight_fails_without_env_file(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path / "openclaw")
    env["OPENCLAW_DB_PATH"] = str(tmp_path / "openclaw" / "openclaw.db")
    env["OPENCLAW_ENV_FILE"] = str(tmp_path / "missing.env")
    Path(env["OPENCLAW_DATA_DIR"]).mkdir(parents=True)

    result = subprocess.run(
        [".venv/bin/python.exe", str(CLI), "pasarela", "preflight"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert result.returncode == 1
    assert payload["status"] == "fail"


def test_openclaw_secretos_estado_hides_values(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path / "openclaw")
    env["OPENCLAW_DOMAINS_ENV_DIR"] = str(_write_domain_envs(tmp_path))

    result = subprocess.run(
        [".venv/bin/python.exe", str(CLI), "secretos", "estado"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    payload = json.loads(result.stdout)
    assert payload["domains"]["academico"]["providers"]["gemini_api"]["status"] == "ready"
    assert "gemini-acad" not in result.stdout
    assert "openai-prof" not in result.stdout


def test_openclaw_presupuesto_estado_y_simulacion(tmp_path: Path) -> None:
    env = os.environ.copy()
    env["OPENCLAW_DATA_DIR"] = str(tmp_path / "openclaw")
    env["OPENCLAW_DOMAINS_ENV_DIR"] = str(_write_domain_envs(tmp_path))

    status = subprocess.run(
        [".venv/bin/python.exe", str(CLI), "presupuesto", "estado"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    simulate = subprocess.run(
        [
            ".venv/bin/python.exe",
            str(CLI),
            "presupuesto",
            "simular",
            "--dominio",
            "academico",
            "--proveedor",
            "gemini_api",
            "--costo-estimado",
            "0.05",
            "--tokens-estimados",
            "100",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    status_payload = json.loads(status.stdout)
    simulate_payload = json.loads(simulate.stdout)

    assert "global" in status_payload
    assert simulate_payload["domain"] == "academico"
    assert simulate_payload["provider"] == "gemini_api"
