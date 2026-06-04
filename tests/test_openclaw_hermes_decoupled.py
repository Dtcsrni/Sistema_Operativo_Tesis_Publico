import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT / "runtime" / "openclaw"

if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from openclaw_local.orchestrator import Orchestrator, ChatBackendCandidate
from openclaw_local.persona import build_hermes_system_block
from openclaw_local.storage import OpenClawStore

ROOT = Path(__file__).resolve().parents[1]


def test_build_hermes_system_block_agentic_and_reasoning() -> None:
    # 1. Probar el bloque system en modo agéntico
    block_agentic = build_hermes_system_block(agentic_mode=True)
    assert "REGLAS AGÉNTICAS" in block_agentic
    assert "Thought:" in block_agentic
    assert "Action:" in block_agentic
    assert "Final Answer:" in block_agentic

    # 2. Probar en modo no agéntico pero con razonamiento
    block_reasoning = build_hermes_system_block(agentic_mode=False, include_reasoning=True, complexity="high")
    assert "REGLAS AGÉNTICAS" not in block_reasoning
    assert "REGLAS DE RAZONAMIENTO" in block_reasoning


def test_orchestrator_run_agentic_loop_success(tmp_path: Path, monkeypatch) -> None:
    # Preparar el store de OpenClaw temporal
    store = OpenClawStore(tmp_path / "openclaw.db")
    orchestrator = Orchestrator(ROOT, store)

    # Mockear SerenaClient
    mock_serena_client = MagicMock()
    mock_serena_client.list_tools.return_value = [
        {"name": "mock_tool", "description": "A tool for testing", "inputSchema": {}}
    ]

    # Simular una respuesta LLM que ejecuta una herramienta y luego da la respuesta final
    step_calls = []

    def mock_gemini_api_generate(api_key, model, prompt, timeout_seconds):
        step_calls.append(prompt)
        if len(step_calls) == 1:
            # Primer paso: llama a la herramienta mock_tool
            response = (
                "Thought: Necesito consultar mock_tool para obtener datos.\n"
                "Action: mock_tool\n"
                "Action Input: {}\n"
            )
            return True, response
        else:
            # Segundo paso: respuesta final
            response = "Final Answer: El resultado del test es exitoso con base en la evidencia de mock_tool."
            return True, response

    mock_tool_result = {"status": "ok", "data": "evidencia_de_prueba"}

    def mock_call_tool(tool_name, tool_input):
        assert tool_name == "mock_tool"
        return mock_tool_result

    mock_serena_client.call_tool = mock_call_tool

    monkeypatch.setattr("openclaw_local.orchestrator.SerenaClient.from_repo", lambda root: mock_serena_client)
    monkeypatch.setattr("openclaw_local.orchestrator.gemini_api_generate", mock_gemini_api_generate)

    candidate = ChatBackendCandidate(
        provider="gemini_api",
        base_url="https://api.gemini.com",
        model="gemini-2.5-flash",
        timeout_seconds=60,
        label="gemini",
    )

    state = {"turns": []}
    ok, answer = orchestrator._run_agentic_loop(
        prompt="Ejecuta la prueba de loop agéntico",
        channel=MagicMock(),
        chat_id="test-chat",
        candidate=candidate,
        state=state,
    )

    assert ok is True
    assert "El resultado del test es exitoso" in answer
    assert len(step_calls) == 2


def test_orchestrator_chat_request_profile() -> None:
    store = MagicMock()
    orchestrator = Orchestrator(ROOT, store)

    profile_res = orchestrator._chat_request_profile("Investiga el estado del arte de LoRa P2P")
    assert profile_res["intent"] == "research"
    assert profile_res["complexity"] == "high"

    profile_code = orchestrator._chat_request_profile("Corrige el error de Python en script.py")
    assert profile_code["intent"] == "coding"
    assert profile_code["complexity"] == "high"

    profile_casual = orchestrator._chat_request_profile("Hola cómo estás")
    assert profile_casual["intent"] == "general_chat"
    assert profile_casual["complexity"] == "low"


def test_orchestrator_research_mission_success(tmp_path: Path, monkeypatch) -> None:
    # Preparar el store de OpenClaw temporal
    store = OpenClawStore(tmp_path / "openclaw.db")
    
    # Creamos un orchestrator con tmp_path como repo_root para que escriba las cosas ahí
    orchestrator = Orchestrator(tmp_path, store)
    
    # Mockear channel para capturar mensajes y progreso
    captured_messages = []
    class FakeChannel:
        def send_message(self, text: str, **kwargs):
            captured_messages.append(text)
            return {"status": "sent"}
        def send_action(self, action: str):
            pass
        def update_message(self, message_id, text):
            pass
        def send_photo(self, image_path, caption=""):
            pass
            
    channel = FakeChannel()
    
    # Configurar CONTEXT.md temporal en el repo_root
    glossary = tmp_path / "00_sistema_tesis"
    glossary.mkdir(parents=True)
    (glossary / "CONTEXT.md").write_text("PDR, SF, BW, CR, LoRa, MQTT, Pachuca", encoding="utf-8")
    
    payload = orchestrator.dispatch_command("investiga", "redes LoRa Pachuca", channel)
    
    assert payload["status"] == "ok"
    assert "Misión de investigación completada" in payload["text"]
    assert payload["topic_slug"] == "redes_lora_pachuca"
    
    # Validar que los archivos de LaTeX y BibTeX se hayan creado en el tmp_path
    tex_file = Path(payload["tex_path"])
    bib_file = Path(payload["bib_path"])
    
    assert tex_file.exists()
    assert bib_file.exists()
    
    tex_content = tex_file.read_text(encoding="utf-8")
    bib_content = bib_file.read_text(encoding="utf-8")
    
    assert "Estado del Arte: redes LoRa Pachuca" in tex_content
    assert "@article{" in bib_content
    assert "KPI-CUR-01" in payload["text"]
    assert "KPI-ANA-02" in payload["text"]
    assert "KPI-RED-03" in payload["text"]
    assert "KPI-ECO-04" in payload["text"]

