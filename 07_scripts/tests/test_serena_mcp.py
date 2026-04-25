import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import socket
from contextlib import suppress
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def close_process(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
    for stream_name in ("stdin", "stdout", "stderr"):
        stream = getattr(process, stream_name, None)
        if stream:
            with suppress(Exception):
                stream.close()


def encode_message(payload: dict) -> bytes:
    body = json.dumps(payload).encode("utf-8")
    return f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body


def read_message(stream) -> dict:
    headers = {}
    while True:
        line = stream.readline()
        if not line:
            raise EOFError("Servidor MCP cerró la conexión")
        decoded = line.decode("utf-8").strip()
        if not decoded:
            break
        key, _, value = decoded.partition(":")
        headers[key.lower()] = value.strip()
    length = int(headers["content-length"])
    body = stream.read(length)
    return json.loads(body.decode("utf-8"))


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")


def minimal_repo(repo: Path) -> None:
    write_json(
        repo / "00_sistema_tesis" / "config" / "agent_identity.json",
        {
            "agent_identity": {
                "agent_role": "Codex (Assistant)",
                "provider": "OpenAI",
                "model_version": "GPT-5 Codex",
                "runtime_label": "OpenAI Codex GPT-5",
            }
        },
    )
    write_json(
        repo / "00_sistema_tesis" / "config" / "ia_gobernanza.yaml",
        {
            "evidencia_fuente_conversacion": {
                "obligatoria_para_val_step_nuevo": True,
                "activacion": {"desde_step_id": "VAL-STEP-501"},
            }
        },
    )
    write_json(
        repo / "00_sistema_tesis" / "config" / "serena_mcp.json",
        {
            "server": {"name": "serena-local", "version": "1.0.0"},
            "trace": {"path": "00_sistema_tesis/bitacora/audit_history/serena_mcp_operations.jsonl"},
            "paths": {
                "read_roots": ["docs"],
                "derived_write_roots": ["06_dashboard/generado/", "00_sistema_tesis/bitacora/audit_history/"],
                "controlled_write_roots": [".vscode/", "00_sistema_tesis/", "07_scripts/", "docs/"],
            },
            "tools": {
                "context.fetch_compact": {
                    "enabled": True,
                    "description": "fetch",
                    "risk_level": "MEDIO",
                    "write_scope": "read_only",
                    "requires_step_id": False,
                },
                "context.repo_map": {
                    "enabled": True,
                    "description": "map",
                    "risk_level": "MEDIO",
                    "write_scope": "read_only",
                    "requires_step_id": False,
                },
                "context.fetch_changes": {
                    "enabled": True,
                    "description": "changes",
                    "risk_level": "MEDIO",
                    "write_scope": "read_only",
                    "requires_step_id": False,
                },
                "context.trace_lookup": {
                    "enabled": True,
                    "description": "trace-lookup",
                    "risk_level": "MEDIO",
                    "write_scope": "read_only",
                    "requires_step_id": False,
                },
                "context.session_brief": {
                    "enabled": True,
                    "description": "brief",
                    "risk_level": "MEDIO",
                    "write_scope": "read_only",
                    "requires_step_id": False,
                },
                "governance.preflight": {
                    "enabled": True,
                    "description": "preflight",
                    "risk_level": "ALTO",
                    "write_scope": "read_only",
                    "requires_step_id": False,
                },
                "artifacts.write_derived": {
                    "enabled": True,
                    "description": "write",
                    "risk_level": "MEDIO",
                    "write_scope": "derived",
                    "requires_step_id": False,
                },
                "canon.apply_controlled_change": {
                    "enabled": True,
                    "description": "apply",
                    "risk_level": "ALTO",
                    "write_scope": "controlled",
                    "requires_step_id": True,
                },
                "canon.prepare_change": {
                    "enabled": True,
                    "description": "prepare",
                    "risk_level": "ALTO",
                    "write_scope": "controlled",
                    "requires_step_id": False,
                },
                "artifacts.evaluate_serena": {
                    "enabled": True,
                    "description": "eval",
                    "risk_level": "MEDIO",
                    "write_scope": "derived",
                    "requires_step_id": False,
                },
                "trace.append_operation": {
                    "enabled": True,
                    "description": "trace",
                    "risk_level": "MEDIO",
                    "write_scope": "derived",
                    "requires_step_id": False,
                },
            },
        },
    )
    write_jsonl(
        repo / "00_sistema_tesis" / "canon" / "events.jsonl",
        [
            {
                "event_id": "EVT-0001",
                "event_type": "conversation_source_registered",
                "occurred_at": "2026-04-07 00:00:00",
                "actor": {"type": "system", "id": "tesis-cli", "display_name": "tesis-cli"},
                "session_id": "session-1",
                "risk_level": "ALTO",
                "links": {},
                "payload": {"quoted_text": "PLEASE IMPLEMENT THIS PLAN:"},
                "affected_files": [],
                "human_validation": {"required": False},
                "prev_event_hash": "INICIO",
                "content_hash": "hash-1",
            },
            {
                "event_id": "VAL-STEP-660",
                "event_type": "human_validation",
                "occurred_at": "2026-04-07 00:00:01",
                "actor": {"type": "ai", "id": "OpenAI", "display_name": "OpenAI"},
                "session_id": "session-1",
                "risk_level": "ALTO",
                "links": {},
                "payload": {},
                "affected_files": [],
                "human_validation": {
                    "required": True,
                    "step_id": "VAL-STEP-660",
                    "source_event_id": "EVT-0001",
                },
                "prev_event_hash": "hash-1",
                "content_hash": "hash-2",
            },
        ],
    )
    write_json(repo / "00_sistema_tesis" / "config" / "integrity_manifest.json", {})
    doc = repo / "docs" / "nota.md"
    doc.parent.mkdir(parents=True, exist_ok=True)
    doc.write_text("Linea uno\nSerena MCP permite contexto compacto.\n", encoding="utf-8")
    protected = repo / "docs" / "protegido.md"
    protected.write_text("<!-- SISTEMA_TESIS:PROTEGIDO -->\nOriginal\n", encoding="utf-8")


class TestSerenaMCP(unittest.TestCase):
    def test_stdio_server_lists_and_calls_tools(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            minimal_repo(repo)
            env = dict(os.environ, SISTEMA_TESIS_ROOT=str(repo))
            process = subprocess.Popen(
                [sys.executable, str(ROOT / "07_scripts" / "serena_mcp.py")],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            try:
                process.stdin.write(
                    encode_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {"protocolVersion": "2025-03-26"},
                        }
                    )
                )
                process.stdin.flush()
                init_response = read_message(process.stdout)
                self.assertEqual(init_response["result"]["serverInfo"]["name"], "serena-local")

                process.stdin.write(
                    encode_message({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
                )
                process.stdin.flush()

                process.stdin.write(
                    encode_message({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
                )
                process.stdin.flush()
                tool_response = read_message(process.stdout)
                names = {tool["name"] for tool in tool_response["result"]["tools"]}
                self.assertEqual(len(names), 11)
                self.assertIn("context_fetch_compact", names)
                self.assertIn("context_repo_map", names)
                self.assertIn("context_fetch_changes", names)
                self.assertIn("context_trace_lookup", names)
                self.assertIn("context_session_brief", names)
                self.assertIn("governance_preflight", names)

                process.stdin.write(
                    encode_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 3,
                            "method": "tools/call",
                            "params": {
                                "name": "context_fetch_compact",
                                "arguments": {"query": "Serena", "paths": ["docs/nota.md"]},
                            },
                        }
                    )
                )
                process.stdin.flush()
                fetch_response = read_message(process.stdout)
                fetch_payload = fetch_response["result"]["structuredContent"]
                self.assertEqual(fetch_payload["status"], "ok")
                self.assertTrue(fetch_payload["matches"])

                process.stdin.write(
                    encode_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 30,
                            "method": "tools/call",
                            "params": {
                                "name": "context.fetch_compact",
                                "arguments": {"query": "Serena", "paths": ["docs/nota.md"]},
                            },
                        }
                    )
                )
                process.stdin.flush()
                canonical_fetch_response = read_message(process.stdout)
                self.assertEqual(canonical_fetch_response["result"]["structuredContent"]["status"], "ok")

                process.stdin.write(
                    encode_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 32,
                            "method": "tools/call",
                            "params": {
                                "name": "context_repo_map",
                                "arguments": {"limit": 3},
                            },
                        }
                    )
                )
                process.stdin.flush()
                map_response = read_message(process.stdout)
                self.assertEqual(map_response["result"]["structuredContent"]["status"], "ok")

                process.stdin.write(
                    encode_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 31,
                            "method": "tools/call",
                            "params": {
                                "name": "governance_preflight",
                                "arguments": {
                                    "tool_name": "canon.apply_controlled_change",
                                    "target_paths": ["docs/protegido.md"],
                                    "intent": "verificar enforcement MCP",
                                },
                            },
                        }
                    )
                )
                process.stdin.flush()
                preflight_response = read_message(process.stdout)
                preflight_payload = preflight_response["result"]["structuredContent"]
                self.assertEqual(preflight_payload["status"], "blocked")
                self.assertEqual(preflight_payload["write_scope"], "protected")
                self.assertTrue(preflight_payload["errors"])

                process.stdin.write(
                    encode_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 4,
                            "method": "tools/call",
                            "params": {
                                "name": "artifacts_write_derived",
                                "arguments": {
                                    "path": "06_dashboard/generado/demo.md",
                                    "content": "# Demo\n",
                                },
                            },
                        }
                    )
                )
                process.stdin.flush()
                write_response = read_message(process.stdout)
                self.assertEqual(write_response["result"]["structuredContent"]["status"], "ok")
                self.assertTrue((repo / "06_dashboard" / "generado" / "demo.md").exists())

                process.stdin.write(
                    encode_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 5,
                            "method": "tools/call",
                            "params": {
                                "name": "canon_apply_controlled_change",
                                "arguments": {
                                    "path": "docs/protegido.md",
                                    "new_content": "<!-- SISTEMA_TESIS:PROTEGIDO -->\nCambio\n",
                                },
                            },
                        }
                    )
                )
                process.stdin.flush()
                blocked_response = read_message(process.stdout)
                self.assertIn("error", blocked_response)

                process.stdin.write(
                    encode_message(
                        {
                            "jsonrpc": "2.0",
                            "id": 6,
                            "method": "tools/call",
                            "params": {
                                "name": "canon_apply_controlled_change",
                                "arguments": {
                                    "path": "docs/protegido.md",
                                    "new_content": "<!-- SISTEMA_TESIS:PROTEGIDO -->\nCambio\n",
                                    "step_id": "VAL-STEP-660",
                                    "source_event_id": "EVT-0001",
                                },
                            },
                        }
                    )
                )
                process.stdin.flush()
                apply_response = read_message(process.stdout)
                self.assertEqual(apply_response["result"]["structuredContent"]["status"], "ok")
                self.assertIn("Cambio", (repo / "docs" / "protegido.md").read_text(encoding="utf-8"))
                self.assertTrue((repo / "00_sistema_tesis" / "bitacora" / "audit_history" / "serena_mcp_operations.jsonl").exists())
            finally:
                close_process(process)

    def test_http_server_handles_initialize_and_tools(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            minimal_repo(repo)
            debug_log = repo / "00_sistema_tesis" / "bitacora" / "audit_history" / "serena_mcp_debug.log"
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            env = dict(os.environ, SISTEMA_TESIS_ROOT=str(repo), SERENA_MCP_DEBUG_LOG=str(debug_log))
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(ROOT / "07_scripts" / "serena_mcp.py"),
                    "--transport",
                    "http",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            try:
                time.sleep(1.0)
                init_request = Request(
                    f"http://127.0.0.1:{port}/mcp",
                    data=json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 1,
                            "method": "initialize",
                            "params": {"protocolVersion": "2025-11-25"},
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                    method="POST",
                )
                with urlopen(init_request, timeout=5) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(payload["result"]["serverInfo"]["name"], "serena-local")

                tools_request = Request(
                    f"http://127.0.0.1:{port}/mcp",
                    data=json.dumps({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
                    method="POST",
                )
                with urlopen(tools_request, timeout=5) as response:
                    tools_payload = json.loads(response.read().decode("utf-8"))
                names = {tool["name"] for tool in tools_payload["result"]["tools"]}
                self.assertIn("context_fetch_compact", names)
                self.assertIn("context_repo_map", names)
                self.assertIn("governance_preflight", names)
                debug_lines = debug_log.read_text(encoding="utf-8").splitlines()
                http_out_lines = [line for line in debug_lines if line.startswith("HTTP OUT ")]
                self.assertTrue(http_out_lines)
                self.assertTrue(any('"tool_count": 11' in line for line in http_out_lines))
                self.assertTrue(all('"inputSchema"' not in line for line in http_out_lines))
            finally:
                close_process(process)

    def test_bridge_requires_auth_and_preserves_identity(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            minimal_repo(repo)
            config_path = repo / "00_sistema_tesis" / "config" / "serena_mcp.json"
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            payload["runtime_env"] = {"host_kind": "SISTEMA_TESIS_MCP_HOST_KIND"}
            payload["bridge"] = {
                "bind_host": "127.0.0.1",
                "port": 8766,
                "endpoint": "/mcp/serena",
                "public_bind_allowed": False,
                "auth": {"enabled": True, "env_var": "SERENA_BRIDGE_BEARER_TOKEN", "scheme": "Bearer"},
                "identity_headers": {
                    "agent_role": "X-Sistema-Tesis-Agent-Role",
                    "provider": "X-Sistema-Tesis-Agent-Provider",
                    "model_version": "X-Sistema-Tesis-Agent-Model-Version",
                    "runtime_label": "X-Sistema-Tesis-Agent-Runtime",
                    "host_kind": "X-Sistema-Tesis-Host-Kind",
                },
            }
            write_json(config_path, payload)
            env = dict(os.environ, SISTEMA_TESIS_ROOT=str(repo), SERENA_BRIDGE_BEARER_TOKEN="bridge-secret")
            process = subprocess.Popen(
                [sys.executable, str(ROOT / "runtime" / "serena_bridge" / "bin" / "serena_bridge.py")],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
            )
            try:
                time.sleep(1.0)
                unauthorized_request = Request(
                    "http://127.0.0.1:8766/mcp/serena",
                    data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as unauthorized_error:
                    urlopen(unauthorized_request, timeout=5)
                self.assertEqual(unauthorized_error.exception.code, 401)

                fetch_request = Request(
                    "http://127.0.0.1:8766/mcp/serena",
                    data=json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": 2,
                            "method": "tools/call",
                            "params": {
                                "name": "context.fetch_compact",
                                "arguments": {"query": "Serena", "paths": ["docs/nota.md"]},
                            },
                        }
                    ).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": "Bearer bridge-secret",
                        "X-Sistema-Tesis-Agent-Role": "Compatible Host (Assistant)",
                        "X-Sistema-Tesis-Agent-Provider": "External Host",
                        "X-Sistema-Tesis-Agent-Model-Version": "Test Model",
                        "X-Sistema-Tesis-Agent-Runtime": "External MCP Runtime",
                        "X-Sistema-Tesis-Host-Kind": "external_runtime",
                    },
                    method="POST",
                )
                with urlopen(fetch_request, timeout=5) as response:
                    fetch_payload = json.loads(response.read().decode("utf-8"))
                self.assertEqual(fetch_payload["result"]["structuredContent"]["status"], "ok")

                trace_path = repo / "00_sistema_tesis" / "bitacora" / "audit_history" / "serena_mcp_operations.jsonl"
                rows = [json.loads(line) for line in trace_path.read_text(encoding="utf-8").splitlines() if line.strip()]
                self.assertEqual(rows[-1]["identity"]["host_kind"], "external_runtime")
                self.assertEqual(rows[-1]["identity"]["provider"], "External Host")
            finally:
                close_process(process)


if __name__ == "__main__":
    unittest.main()
