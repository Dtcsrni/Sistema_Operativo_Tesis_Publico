#!/usr/bin/env python3
"""
opencode_executor_run.py — Ejecutor de tareas vía OpenCode subordinado a Mission Control

Uso:
  python opencode_executor_run.py --task-id TASK-001 \
    --task-file /app/runtime/workspaces/task-001/task.json \
    --output-dir /app/runtime/workspaces/task-001/output

Flujo:
  1. Validar preflight RAG si requires_rag=true
  2. Preparar workspace aislado
  3. Inyectar chunks RAG como contexto (si aplica)
  4. Ejecutar task con opencode run
  5. Capturar salida, exit code, archivos entregables
  6. Registrar trazabilidad completa
  7. Reportar a Mission Control
"""

import json
import sys
import subprocess
import hashlib
import os
import tempfile
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Any
import logging
import uuid
from dataclasses import dataclass, asdict

# Config
EXECUTOR_NAME = "opencode-executor"
EXECUTOR_NODE = "pc"
EXECUTOR_MODEL = os.getenv("OPENCODE_MODEL", "deepseek-r1:7b")
EXECUTOR_PROVIDER = os.getenv("OPENCODE_PROVIDER", "ollama")
EXECUTOR_BASE_URL = os.getenv("OPENCODE_BASE_URL", "http://ollama-pc:11434")
EXECUTOR_SERVER_URL = os.getenv("OPENCODE_SERVER_URL", "http://opencode-executor:4096")
EXECUTOR_TIMEOUT_SEC = int(os.getenv("OPENCODE_TIMEOUT_SEC", "180"))
RAG_ENDPOINT = os.getenv("RAG_ENDPOINT", "http://localhost:8080")
MISSION_CONTROL_API = os.getenv("MISSION_CONTROL_API", "http://localhost:4000")

# Rutas
DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(os.getenv("OPENCLAW_REPO_ROOT", str(DEFAULT_REPO_ROOT))).resolve()
if not (REPO_ROOT / "07_scripts").exists():
    REPO_ROOT = DEFAULT_REPO_ROOT
EXECUTION_LOG_PATH = REPO_ROOT / "00_sistema_tesis/bitacora/execution_log.jsonl"

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [EXECUTOR] %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)


@dataclass
class ExecutionTrace:
    """Registro trazable de ejecución."""
    timestamp: str
    session_id: str
    executor: str
    task_id: str
    task_label: str
    requires_rag: bool
    rag_session_id: Optional[str]
    rag_chunks_recovered: int
    rag_source_hash: str
    rag_chunk_hash: str
    model: str
    provider: str
    node: str
    node_hardware: str
    provider_endpoint: str
    commands_allowed: list[str]
    workspace_path: str
    exit_code: int
    stdout_size_bytes: int
    stderr_size_bytes: int
    deliverable_files: list[dict]
    errors: Optional[str]
    duration_seconds: float
    decision: str  # COMPLETED, FAILED, RAG_BLOCKED, etc
    mission_control_checkpoint: str
    created_by: str  # "DEC-0038"
    audit_hash: str


def sha256_hash(data: str | bytes) -> str:
    """Calcula SHA256."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def run_preflight_rag(task_id: str, question: str, context: Optional[str] = None) -> tuple[bool, Optional[dict]]:
    """
    Ejecuta preflight RAG vía script externo.
    Retorna: (ok: bool, result_dict: dict | None)
    """
    try:
        output_path = Path(tempfile.gettempdir()) / f"preflight_{task_id}.json"
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "07_scripts/preflight_rag_mandatory.py"),
                "--task-id", task_id,
                "--question", question,
                "--context", context or "general",
                "--output", str(output_path)
            ],
            timeout=15,
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT)
        )
        
        if result.returncode == 0 and output_path.exists():
            with open(output_path, encoding="utf-8") as f:
                rag_result = json.load(f)
            logger.info(f"Preflight RAG OK: {rag_result['chunks_recovered']} chunks")
            return True, rag_result
        else:
            logger.error(f"Preflight RAG failed: {result.stderr}")
            return False, None
    
    except Exception as e:
        logger.error(f"Error running preflight RAG: {str(e)}")
        return False, None


def prepare_workspace(task_id: str) -> Path:
    """
    Prepara workspace aislado para la tarea.
    Retorna: workspace_path
    """
    ws_path = REPO_ROOT / f"runtime/workspaces/{task_id}"
    
    # Crear si no existe
    ws_path.mkdir(parents=True, exist_ok=True)
    
    # Crear subdirectorios
    (ws_path / "input").mkdir(exist_ok=True)
    (ws_path / "output").mkdir(exist_ok=True)
    (ws_path / "logs").mkdir(exist_ok=True)
    
    logger.info(f"Workspace preparado: {ws_path}")
    return ws_path


def inject_rag_context(workspace: Path, rag_result: dict) -> bool:
    """
    Inyecta chunks RAG en contexto de sistema.
    Crea archivo: workspace/rag_context.md
    """
    try:
        chunks = rag_result.get("chunks_recovered", 0)
        if chunks == 0:
            logger.warning("No chunks para inyectar")
            return False
        
        # Crear archivo de contexto RAG (simulado)
        context_file = workspace / "rag_context.md"
        with open(context_file, "w") as f:
            f.write("# Contexto RAG Recuperado\n\n")
            f.write(f"Session: {rag_result.get('session_id', 'unknown')}\n")
            f.write(f"Chunks: {chunks}\n")
            f.write(f"Source Hash: {rag_result.get('source_hash', 'unknown')}\n")
            f.write(f"Chunk Hash: {rag_result.get('chunk_hash', 'unknown')}\n")
            f.write("\n---\n\n")
            f.write("[Contenido de chunks inyectado aquí]\n")
        
        logger.info(f"RAG context inyectado: {context_file}")
        return True
    
    except Exception as e:
        logger.error(f"Error inyectando RAG context: {str(e)}")
        return False


def execute_task_opencode(workspace: Path, task_json: dict, timeout_sec: int) -> tuple[int, str, str]:
    """
    Ejecuta tarea vía opencode run.
    Retorna: (exit_code, stdout, stderr)
    """
    try:
        task_copy = workspace / "input" / "task.json"
        with open(task_copy, "w", encoding="utf-8") as f:
            json.dump(task_json, f, ensure_ascii=False, indent=2)

        prompt_text = (
            task_json.get("prompt")
            or task_json.get("instruction")
            or task_json.get("description")
            or f"Resuelve la tarea {task_json.get('task_id', 'unknown')} usando el archivo adjunto."
        )
        task_context = json.dumps(task_json, ensure_ascii=False, indent=2)
        full_prompt = (
            f"Tarea OpenCode {task_json.get('task_id', 'unknown')}\n"
            f"Instrucción: {prompt_text}\n\n"
            f"Contexto estructurado:\n{task_context}\n"
            f"\nTrabaja dentro del workspace actual y deja entregables en output/."
        )
        
        # Ejecutar vía opencode (host) o fallback en contenedor si CLI local no está disponible.
        if shutil.which("opencode"):
            cmd = [
                "opencode", "run",
                "--attach", EXECUTOR_SERVER_URL,
                full_prompt,
            ]
        else:
            container_server_url = os.getenv("OPENCODE_SERVER_URL_CONTAINER", "http://127.0.0.1:4096")
            cmd = [
                "docker", "exec", "opencode-executor",
                "opencode", "run",
                "--attach", container_server_url,
                full_prompt,
            ]
        
        logger.info(f"Ejecutando: {cmd[0]} {cmd[1]} --attach {EXECUTOR_SERVER_URL} ...")
        
        result = subprocess.run(
            cmd,
            timeout=timeout_sec + 10,
            capture_output=True,
            text=True,
            cwd=str(workspace)
        )
        
        logger.info(f"Ejecución completada: exit_code={result.returncode}")
        return result.returncode, result.stdout, result.stderr
    
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout ejecutando tarea ({timeout_sec}s)")
        return 124, "", "Timeout"
    except Exception as e:
        logger.error(f"Error ejecutando tarea: {str(e)}")
        return 1, "", str(e)


def collect_deliverables(workspace: Path) -> list[dict]:
    """
    Recolecta archivos entregables del output.
    Retorna: list[{path, size_bytes, hash}]
    """
    deliverables = []
    output_dir = workspace / "output"
    
    if not output_dir.exists():
        logger.warning(f"Output directory no existe: {output_dir}")
        return deliverables
    
    try:
        for file_path in output_dir.rglob("*"):
            if file_path.is_file():
                file_hash = sha256_hash(file_path.read_bytes())
                deliverables.append({
                    "path": str(file_path.relative_to(workspace)),
                    "size_bytes": file_path.stat().st_size,
                    "hash": file_hash
                })
        
        logger.info(f"Recolectados {len(deliverables)} entregables")
        return deliverables
    
    except Exception as e:
        logger.error(f"Error recolectando deliverables: {str(e)}")
        return deliverables


def build_trace(
    task_id: str,
    task_label: str,
    requires_rag: bool,
    rag_result: Optional[dict],
    workspace: Path,
    exit_code: int,
    stdout: str,
    stderr: str,
    deliverables: list[dict],
    duration_sec: float,
    decision: str
) -> ExecutionTrace:
    """
    Construye registro trazable de ejecución.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    session_id = f"exec-session-{uuid.uuid4().hex[:8]}"
    
    # Calcular auditoría
    trace_dict = {
        "task_id": task_id,
        "executor": EXECUTOR_NAME,
        "model": EXECUTOR_MODEL,
        "exit_code": exit_code,
        "timestamp": timestamp
    }
    audit_data = json.dumps(trace_dict, sort_keys=True)
    audit_hash = sha256_hash(audit_data)
    
    return ExecutionTrace(
        timestamp=timestamp,
        session_id=session_id,
        executor=EXECUTOR_NAME,
        task_id=task_id,
        task_label=task_label,
        requires_rag=requires_rag,
        rag_session_id=rag_result.get("session_id") if rag_result else None,
        rag_chunks_recovered=rag_result.get("chunks_recovered", 0) if rag_result else 0,
        rag_source_hash=rag_result.get("source_hash", "") if rag_result else "",
        rag_chunk_hash=rag_result.get("chunk_hash", "") if rag_result else "",
        model=EXECUTOR_MODEL,
        provider=EXECUTOR_PROVIDER,
        node=EXECUTOR_NODE,
        node_hardware="Docker",
        provider_endpoint=EXECUTOR_BASE_URL,
        commands_allowed=["python", "pip install", "edit_file", "read_file", "mkdir", "git", "docker compose"],
        workspace_path=str(workspace),
        exit_code=exit_code,
        stdout_size_bytes=len(stdout),
        stderr_size_bytes=len(stderr),
        deliverable_files=deliverables,
        errors=stderr if exit_code != 0 else None,
        duration_seconds=duration_sec,
        decision=decision,
        mission_control_checkpoint=f"TASK_{decision}",
        created_by="DEC-0038",
        audit_hash=audit_hash
    )


def write_execution_log(trace: ExecutionTrace) -> bool:
    """
    Escribe traza de ejecución en log JSONL.
    """
    try:
        EXECUTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with open(EXECUTION_LOG_PATH, "a") as f:
            f.write(json.dumps(asdict(trace)) + "\n")
        
        logger.info(f"Logged execution: {EXECUTION_LOG_PATH}")
        return True
    
    except Exception as e:
        logger.error(f"Error writing execution log: {str(e)}")
        return False


def run_execution(task_id: str, task_file: Path, requires_rag: bool | None = None) -> int:
    """
    Orquesta la ejecución completa de una tarea.
    Retorna: exit_code (0=ok, 1=error)
    """
    start_time = datetime.now()
    
    # 1. Leer task JSON
    logger.info(f"Iniciando ejecución: {task_id}")
    try:
        with open(task_file) as f:
            task_json = json.load(f)
    except Exception as e:
        logger.error(f"Error leyendo task JSON: {str(e)}")
        return 1
    
    task_label = task_json.get("label", "untitled")
    rag_question = task_json.get("rag_question")
    rag_context = task_json.get("rag_context")
    if requires_rag is None:
        requires_rag = bool(task_json.get("requires_rag", True))
    
    # 2. Preflight RAG (si aplica)
    rag_result = None
    if requires_rag:
        if not rag_question:
            logger.error("Task requires_rag pero no hay rag_question")
            return 1
        
        rag_ok, rag_result = run_preflight_rag(task_id, rag_question, rag_context)
        if not rag_ok:
            logger.error("Preflight RAG falló")
            decision = "RAG_BLOCKED"
            duration = (datetime.now() - start_time).total_seconds()
            trace = build_trace(task_id, task_label, True, None, Path(), 1, "", "Preflight RAG falló", [], duration, decision)
            write_execution_log(trace)
            return 1
    
    # 3. Preparar workspace
    workspace = prepare_workspace(task_id)
    
    # 4. Inyectar RAG context (si aplica)
    if rag_result:
        inject_rag_context(workspace, rag_result)
    
    # 5. Ejecutar tarea
    exit_code, stdout, stderr = execute_task_opencode(
        workspace,
        task_json,
        EXECUTOR_TIMEOUT_SEC
    )
    
    # 6. Recolectar entregables
    deliverables = collect_deliverables(workspace)
    
    # 7. Construir y registrar traza
    duration = (datetime.now() - start_time).total_seconds()
    decision = "COMPLETED" if exit_code == 0 else "FAILED"
    
    trace = build_trace(
        task_id, task_label, requires_rag, rag_result,
        workspace, exit_code, stdout, stderr,
        deliverables, duration, decision
    )
    
    write_execution_log(trace)
    
    # 8. Reportar a Mission Control (simulado)
    logger.info(f"Execution complete: {decision}, {len(deliverables)} deliverables")
    
    return exit_code


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Ejecutor OpenCode subordinado")
    parser.add_argument("--task-id", required=True, help="ID de la tarea")
    parser.add_argument("--task-file", required=True, help="Ruta del archivo task.json")
    parser.add_argument("--requires-rag", dest="requires_rag", action="store_true", default=None, help="Forzar tarea con RAG")
    parser.add_argument("--no-rag", dest="requires_rag", action="store_false", help="Si NO requiere RAG")
    
    args = parser.parse_args()
    
    exit_code = run_execution(
        task_id=args.task_id,
        task_file=Path(args.task_file),
        requires_rag=args.requires_rag
    )
    
    sys.exit(exit_code)
