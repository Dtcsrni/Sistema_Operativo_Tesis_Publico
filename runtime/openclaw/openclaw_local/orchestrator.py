from __future__ import annotations

import json
import os
import re
import threading
import time
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Protocol, TypeVar
from urllib import error, request
from uuid import uuid4

from .contracts import RequestTrace, TaskEnvelope
from .engine import route_task, default_data_dir
from .persona import (
    build_system_block, 
    build_hermes_system_block, 
    get_tone, 
    is_volatile_query, 
    reasoning_instructions,
    format_model_tag
)
from .policies import load_domain_policies, load_provider_registry
from .response_cache import ResponseCache, cache_hit_tag
from .serena_adapter import SerenaClient
from .storage import OpenClawStore
from .maestro_router import maestro_enabled, maestro_message_hash, maestro_profile_from_decision
from .inference import (
    llamacpp_generate,
    openai_compatible_generate,
    gemini_api_generate
)
from .runtime_status import probe_runtime_status
from .motor_calidad_toltecayotl import MotorDeCalidadToltecayotl
from .agentic_core import build_context_packet

# Constantes de Clasificación
MUTATION_MARKERS = {"aplica", "borra", "cambia", "commit", "deploy", "edita", "elimina", "escribe", "instala", "merge", "modifica", "push", "reinicia", "restart", "systemctl"}
READ_ONLY_TOOLS = {"aprobaciones", "estado", "eventos", "equipo", "logs", "memoria", "modelos", "preflight", "doctor", "presupuesto", "secretos", "servicios"}
AMBIGUOUS_ACTION_MARKERS = {"caracteristicas", "características", "equipo", "genera", "generar", "imagen", "resultado del escaneo", "scan", "scanner", "escaneo"}
MODEL_REQUEST_MARKERS = {"con mistral", "ejecuta con", "modelo", "usa mistral", "usar mistral"}
CLOUD_API_CHAT_PROVIDERS = {"gemini_api"}
PC_INFERENCE_PROVIDERS = {"desktop_compute", "pc_native_llamacpp", "llamacpp_local", "external_llm_router", "openrouter_remote"}
DEFAULT_BLOCKED_CHAT_MODELS = {"mistral", "mistral-nemo", "mistral-nemo:12b"}

@dataclass(frozen=True)
class ChatBackendCandidate:
    provider: str
    base_url: str
    model: str
    timeout_seconds: int
    label: str
    semantic: bool = True

@dataclass(frozen=True)
class ChatExecutionPlan:
    trace_id: str
    request_kind: str
    complexity: str
    deadline_seconds: int
    use_web_assisted: bool
    web_timeout_seconds: int
    api_timeout_seconds: int
    candidates: list[ChatBackendCandidate]
    fallback_policy: str

class CommunicationChannel(Protocol):
    """Interfaz para canales de comunicación."""
    def send_message(self, text: str, **kwargs) -> Any: ...
    def send_action(self, action: str) -> None: ...
    def update_message(self, message_id: Any, text: str) -> None: ...
    def send_photo(self, image_path: Path, caption: str = "") -> Any: ...

class Orchestrator:
    def __init__(self, repo_root: Path, store: OpenClawStore):
        self.repo_root = repo_root
        self.store = store
        self.cache = ResponseCache(repo_root / "runtime/openclaw/cache/chat_responses.json")
        self._semaphores: dict[str, threading.Semaphore] = {}
        self._sem_lock = threading.Lock()

    def _get_semaphore(self, provider: str) -> threading.Semaphore:
        with self._sem_lock:
            if provider not in self._semaphores:
                limit = 1 if provider in {"edge_inference", "pc_native_llamacpp", "local"} else 4
                self._semaphores[provider] = threading.Semaphore(limit)
            return self._semaphores[provider]

    def _load_chat_state(self, chat_id: str) -> dict[str, Any]:
        return self.store.get_cached_context(f"chat:state:{chat_id}") or {"turns": []}

    def _save_chat_state(self, chat_id: str, state: dict[str, Any]):
        self.store.cache_context(f"chat:state:{chat_id}", state)

    def dispatch_command(
        self,
        command: str,
        argument: str,
        channel: CommunicationChannel,
        chat_id: str = "cli",
        operator_identity: str = "human",
        progress_callback: Any | None = None,
    ) -> dict[str, Any]:
        """Despachador central de comandos y chat."""
        state = self._load_chat_state(chat_id)
        
        if command in {"chat", "procesar", "investiga"}:
            return self._chat_response(argument, channel, chat_id, state, operator_identity, progress_callback)
        
        if command in {"start", "help", "ayuda"}:
            return {"status": "ok", "text": self._help_text()}
            
        if command == "estado":
            return {"status": "ok", "text": self._status_text()}
            
        if command == "modelos":
            return {"status": "ok", "text": self._models_text()}
            
        if command in {"modelo", "model", "ruta", "routing"}:
            return self._routing_response(argument)

        return {"status": "error", "text": f"Comando '{command}' no implementado en el orquestador core."}

    def _help_text(self) -> str:
        return (
            "🤖 <b>OpenClaw Mission Control</b>\n\n"
            "Comandos disponibles:\n"
            "/chat &lt;msg&gt; - Chat inteligente con ruteo automático.\n"
            "/estado - Estado de salud del sistema.\n"
            "/modelos - Lista de modelos cargados.\n"
            "/investiga &lt;tema&gt; - Búsqueda y síntesis con evidencia.\n"
            "/aprobar &lt;id&gt; - Aprueba una tarea pendiente."
        )

    def _status_text(self) -> str:
        return "Sistema Operativo de Tesis: ACTIVO\nNodos: Edge/Desktop configurados."

    def _models_text(self) -> str:
        return "Gestión de modelos delegada al motor de inferencia (Docker)."

    def _routing_response(self, argument: str) -> dict[str, Any]:
        return {"status": "ok", "text": "Información de ruteo (en migración)."}

    def _chat_response(
        self,
        argument: str,
        channel: CommunicationChannel,
        chat_id: str,
        state: dict[str, Any],
        operator_identity: str,
        progress_callback: Any | None = None,
    ) -> dict[str, Any]:
        started_at = time.perf_counter()
        
        # 1. Perfilado de intención
        profile = self._chat_request_profile(argument, state=state, chat_id=chat_id)
        
        # 2. Ruteo
        task = TaskEnvelope(
            task_id=f"OC-{uuid4().hex[:8]}",
            title=f"Chat {chat_id}",
            domain="academico",
            objective=argument,
            complexity=profile["complexity"],
            risk_level="low",
            extra_context={
                "chat_id": chat_id,
                "operator": operator_identity,
                "profile": profile,
                "allow_openrouter": profile.get("allow_openrouter") == "true",
                "privacy_class": profile.get("privacy_class", "private_non_sensitive"),
            }
        )
        decision = route_task(task, load_domain_policies(self.repo_root), repo_root=self.repo_root, store=self.store)
        self.store.save_task(task, decision)
        
        # 3. Plan de ejecución
        plan = self._build_chat_execution_plan(argument, profile, decision.provider)
        
        # 4. Inferencia con streaming
        ok = False
        response = ""
        selected_candidate = None
        
        channel.send_action("typing")
        
        for candidate in plan.candidates:
            if ok: break
            
            sem = self._get_semaphore(candidate.provider)
            if not sem.acquire(blocking=False):
                continue
                
            try:
                attempt_started = time.perf_counter()
                if decision.agentic_capability:
                    ok, response = self._run_agentic_loop(
                        argument, channel, chat_id, candidate, state, progress_callback
                    )
                else:
                    prompt = self._safe_prompt(argument, state, profile)
                    
                    if candidate.provider == "gemini_api":
                        api_key = os.getenv("OPENCLAW_GEMINI_API_KEY", "").strip()
                        ok, response = gemini_api_generate(api_key=api_key, prompt=prompt, model=candidate.model, timeout_seconds=candidate.timeout_seconds)
                    elif candidate.provider in {"desktop_compute", "pc_native_llamacpp", "llamacpp_local", "edge_inference"}:
                        # En el nuevo stack Docker, todos estos usan el protocolo OpenAI via llama.cpp
                        ok, response = llamacpp_generate(base_url=candidate.base_url, model=candidate.model, prompt=prompt, timeout_seconds=candidate.timeout_seconds)
                    elif candidate.provider == "openrouter_remote":
                        api_key = os.getenv("OPENROUTER_API_KEY", os.getenv("OPENCLAW_OPENROUTER_API_KEY", "")).strip()
                        ok, response = openai_compatible_generate(
                            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                            model=candidate.model,
                            prompt=prompt,
                            timeout_seconds=candidate.timeout_seconds,
                            api_key=api_key,
                            provider_label="openrouter_remote",
                        )
                    else:
                        # Fallback a OpenAI compatible generico
                        ok, response = openai_compatible_generate(
                            base_url=candidate.base_url,
                            model=candidate.model,
                            prompt=prompt,
                            timeout_seconds=candidate.timeout_seconds
                        )
                
                if ok and response.strip():
                    selected_candidate = candidate
                    break
            finally:
                sem.release()

        if not ok:
            response = "⚠️ No se pudo obtener una respuesta válida de los backends configurados."

        # 5. Auditoría de Calidad (MCT)
        if ok and response.strip():
            try:
                mct = MotorDeCalidadToltecayotl()
                # El contexto fuente se podría expandir en el futuro
                mct.evaluar_respuesta(
                    id_de_solicitud=task.task_id,
                    instruccion_original=argument,
                    contexto_fuente="[Contexto Dinámico Orchestrator]",
                    respuesta_ia=response,
                    dominio=task.domain
                )
            except Exception as e:
                print(f"⚠️ Error en auditoría MCT: {e}")

        # Guardar traza y estado
        self._update_chat_history(chat_id, state, argument, response, selected_candidate)
        
        return {
            "status": "ok",
            "text": response,
            "model": selected_candidate.model if selected_candidate else "none",
            "task_id": task.task_id
        }

    def _run_agentic_loop(
        self,
        prompt: str,
        channel: CommunicationChannel,
        chat_id: str,
        candidate: ChatBackendCandidate,
        state: dict[str, Any],
        progress_callback: Any | None = None
    ) -> tuple[bool, str]:
        """Loop ReAct agéntico desacoplado con validación robusta.
        
        Implementa el protocolo Human-Agent Handshake (DEC-0014):
        - Verifica si herramientas requieren aprobación humana
        - Maneja errores de tool execution
        - Respeta límites de pasos y timeouts
        """
        try:
            client = SerenaClient.from_repo(self.repo_root)
            tools = client.list_tools()
        except Exception as exc:
            error_msg = f"Error inicializando Serena: {exc}"
            if progress_callback:
                progress_callback(0, error_msg, "error")
            return False, error_msg
        
        if "hermes" in candidate.model.lower():
            system_block = build_hermes_system_block(agentic_mode=True)
        else:
            system_block = build_system_block("research", "high", include_tools=True)
            
        tools_desc = "\n".join([
            f"- {t['name']}: {t.get('description', 'Sin descripción')} "
            f"(Schema: {json.dumps(t.get('inputSchema', {}))})"
            for t in tools
        ])
        system_block += f"\n\nHERRAMIENTAS DISPONIBLES:\n{tools_desc}\n"
        
        current_prompt = f"{system_block}\n\nUser: {prompt}"
        max_steps = 5
        
        for step in range(max_steps):
            if progress_callback:
                progress_callback(0, f"\n[Paso {step+1}/{max_steps}] Pensando...", "thinking")
            
            try:
                if candidate.provider == "gemini_api":
                    api_key = os.getenv("OPENCLAW_GEMINI_API_KEY", "").strip()
                    ok, response = gemini_api_generate(
                        api_key=api_key, 
                        model=candidate.model, 
                        prompt=current_prompt,
                        timeout_seconds=candidate.timeout_seconds
                    )
                elif candidate.provider in {"edge_inference", "desktop_compute", "pc_native_llamacpp", "llamacpp_local"}:
                    # Usamos llamacpp_generate (OpenAI compatible) para el loop agentico
                    ok, response = llamacpp_generate(
                        base_url=candidate.base_url, 
                        model=candidate.model, 
                        prompt=current_prompt,
                        timeout_seconds=candidate.timeout_seconds
                    )
                elif candidate.provider == "openrouter_remote":
                    api_key = os.getenv("OPENROUTER_API_KEY", os.getenv("OPENCLAW_OPENROUTER_API_KEY", "")).strip()
                    ok, response = openai_compatible_generate(
                        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                        model=candidate.model,
                        prompt=current_prompt,
                        timeout_seconds=candidate.timeout_seconds,
                        api_key=api_key,
                        provider_label="openrouter_remote",
                    )
            except Exception as exc:
                error_msg = f"Error en generación LLM: {exc}"
                if progress_callback:
                    progress_callback(0, error_msg, "error")
                return False, error_msg
                
            if not ok:
                return False, response
            
            # Asegurar que response está correctamente decodificado
            if isinstance(response, bytes):
                try:
                    response = response.decode("utf-8")
                except UnicodeDecodeError:
                    response = response.decode("utf-8", errors="replace")
            
            action_match = re.search(r"Action:\s*([^\n]+)", response)
            input_match = re.search(r"Action Input:\s*(.*?)(?=\n(?:Observation|Thought|Final Answer)|$)", response, re.DOTALL)
            
            if action_match and input_match:
                tool_name = action_match.group(1).strip()
                try:
                    raw_input = re.sub(r"^```json\s*|\s*```$", "", input_match.group(1).strip())
                    tool_input = json.loads(raw_input) if raw_input else {}
                except json.JSONDecodeError as exc:
                    error_msg = f"Error parsear JSON de tool input: {exc}"
                    if progress_callback:
                        progress_callback(0, error_msg, "error")
                    current_prompt += f"\n{response}\nObservation: {error_msg}\nThought: "
                    continue
                
                if progress_callback:
                    progress_callback(0, f" Ejecutando {tool_name}...", "tool")
                
                try:
                    tool_result = client.call_tool(tool_name, tool_input)
                except Exception as exc:
                    error_msg = f"Error ejecutar {tool_name}: {exc}"
                    if progress_callback:
                        progress_callback(0, error_msg, "error")
                    current_prompt += f"\n{response}\nObservation: {error_msg}\nThought: "
                    continue
                
                # Validar protocolo DEC-0014: verificar si se requiere aprobación humana
                human_action_required = tool_result.get("requires_human_action", False)
                human_action_type = tool_result.get("human_action_type", None)
                
                if human_action_required and human_action_type:
                    msg = f"⚠️ Acción humana requerida: {human_action_type}. Pausando loop."
                    if progress_callback:
                        progress_callback(0, msg, "warning")
                    tool_result["handshake_state"] = "human_required"
                    observation = json.dumps(tool_result, ensure_ascii=False, indent=2)
                    current_prompt += f"\n{response}\nObservation: {observation}\n"
                    return False, f"Handshake humano: {human_action_type}"
                
                # Encodificar resultado de forma segura
                try:
                    observation = json.dumps(tool_result, ensure_ascii=False, indent=2)
                except Exception as exc:
                    observation = f"Error serializar resultado: {exc}"
                
                current_prompt += f"\n{response}\nObservation: {observation}\nThought: "
            else:
                final_answer_match = re.search(r"Final Answer:\s*(.*)", response, re.DOTALL)
                if final_answer_match:
                    answer = final_answer_match.group(1).strip()
                    # Limpiar marcadores de código si existen
                    answer = re.sub(r"^```.*?\n|\n```$", "", answer, flags=re.DOTALL).strip()
                    return True, answer
                # Si no hay Action ni Final Answer, continuar preguntando
                current_prompt += f"\n{response}\nThought: "
                
        return False, "Límite de pasos alcanzado (5 iteraciones)"

    def _update_chat_history(self, chat_id: str, state: dict, user_text: str, assistant_text: str, candidate: ChatBackendCandidate | None):
        turns = state.get("turns", [])
        turns.append({"user": user_text, "assistant": assistant_text, "ts": datetime.now(UTC).isoformat()})
        state["turns"] = turns[-12:] 
        self._save_chat_state(chat_id, state)

    def _chat_request_profile(self, argument: str, state: dict | None = None, chat_id: str = "") -> dict[str, str]:
        # Implementación de perfilado con heurísticas y fallback
        lowered = argument.lower()
        allow_openrouter = "true" if "openrouter" in lowered else "false"
        if any(m in lowered for m in ["investiga", "búsqueda", "fuentes"]):
            return {"intent": "research", "complexity": "high", "request_kind": "knowledge", "allow_openrouter": allow_openrouter}
        if any(m in lowered for m in ["código", "python", "error", "script"]):
            return {"intent": "coding", "complexity": "high", "request_kind": "coding", "allow_openrouter": allow_openrouter}
        if len(argument) > 180:
            return {"intent": "reasoning", "complexity": "high", "request_kind": "reasoning", "allow_openrouter": allow_openrouter}
        return {"intent": "general_chat", "complexity": "low", "request_kind": "standard", "allow_openrouter": allow_openrouter}

    def _chat_request_profile_fallback(self, argument: str) -> dict[str, str]:
        return self._chat_request_profile(argument)

    def _build_chat_execution_plan(self, argument: str, profile: dict, decision_provider: str) -> ChatExecutionPlan:
        edge_base = os.getenv("OPENCLAW_EDGE_INFERENCE_BASE_URL", os.getenv("OPENCLAW_EDGE_OLLAMA_BASE_URL", "http://127.0.0.1:11434"))
        desktop_base = os.getenv("OPENCLAW_DESKTOP_COMPUTE_BASE_URL", "http://127.0.0.1:21434")
        runtime_status = probe_runtime_status(self.repo_root)
        desktop_ready = bool((runtime_status.get("llamacpp") or {}).get("ready"))
        context_packet = build_context_packet(TaskEnvelope(
            task_id=f"CHATCTX-{uuid4().hex[:8]}",
            title="Chat context",
            domain="academico",
            objective=argument,
            complexity=profile.get("complexity", "medium"),
            risk_level="low",
            extra_context={"allow_openrouter": profile.get("allow_openrouter") == "true"},
        ))
        
        candidates = []
        if decision_provider == "openrouter_remote" and "openrouter_remote" in context_packet.allowed_providers:
            candidates.append(ChatBackendCandidate(
                "openrouter_remote",
                os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                os.getenv("OPENROUTER_MODEL", os.getenv("OPENCLAW_OPENROUTER_MODEL", "openrouter/free")),
                int(os.getenv("OPENROUTER_TIMEOUT_SECONDS", "120")),
                "openrouter",
            ))
        prefer_desktop = decision_provider in PC_INFERENCE_PROVIDERS
        if prefer_desktop and desktop_ready:
            model = os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", "deepseek-r1:7b")
            provider = "llamacpp_local" if decision_provider in {"llamacpp_local", "pc_native_llamacpp", "openrouter_remote"} else "desktop_compute"
            candidates.append(ChatBackendCandidate(provider, desktop_base, model, 120, "desktop"))
        
        # Candidato Edge (ahora via inferencia-llamacpp o compatible)
        edge_model = os.getenv("OPENCLAW_TELEGRAM_EDGE_MODEL", "qwen3:4b")
        candidates.append(ChatBackendCandidate("edge_inference", edge_base, edge_model, 60, "edge"))

        if not prefer_desktop and profile["complexity"] == "high" and desktop_ready:
            model = os.getenv("OPENCLAW_DESKTOP_RUNTIME_MODEL", "deepseek-r1:7b")
            candidates.append(ChatBackendCandidate("desktop_compute", desktop_base, model, 120, "desktop"))
        
        return ChatExecutionPlan(
            trace_id=f"CH-{uuid4().hex[:6]}",
            request_kind=profile["request_kind"],
            complexity=profile["complexity"],
            deadline_seconds=180,
            use_web_assisted=False,
            web_timeout_seconds=30,
            api_timeout_seconds=20,
            candidates=candidates,
            fallback_policy="standard"
        )

    def _safe_prompt(self, argument: str, state: dict, profile: dict) -> str:
        turns = state.get("turns", [])
        context = ""
        if turns:
            context = "Contexto previo:\n" + "\n".join([f"U: {t['user']}\nA: {t['assistant']}" for t in turns[-2:]])
        
        system = build_system_block(profile["request_kind"], profile["complexity"])
        return f"{system}\n\n{context}\n\nUsuario: {argument}\nAsistente:"
