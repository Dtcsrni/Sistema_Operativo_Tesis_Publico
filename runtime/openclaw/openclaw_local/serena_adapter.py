from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import request as urllib_request


REQUIRED_TOOLS = {
    "context.fetch_compact",
    "governance.preflight",
    "artifacts.evaluate_serena",
    "artifacts.write_derived",
    "canon.prepare_change",
    "canon.apply_controlled_change",
    "trace.append_operation",
}

LEGACY_TOOL_ALIASES = {
    "context_fetch_compact": "context.fetch_compact",
    "governance_preflight": "governance.preflight",
    "artifacts_evaluate_serena": "artifacts.evaluate_serena",
    "artifacts_write_derived": "artifacts.write_derived",
    "canon_prepare_change": "canon.prepare_change",
    "canon_apply_controlled_change": "canon.apply_controlled_change",
    "trace_append_operation": "trace.append_operation",
}


class SerenaAdapterError(RuntimeError):
    pass


class SerenaTransportError(SerenaAdapterError):
    pass


class SerenaProtocolError(SerenaAdapterError):
    pass


class SerenaToolError(SerenaAdapterError):
    pass


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw not in {"0", "false", "no", "off"}


def _normalize_tool_name(name: str) -> str:
    return LEGACY_TOOL_ALIASES.get(name, name)


def _normalize_tool_names(names: list[str]) -> set[str]:
    return {_normalize_tool_name(name) for name in names}


class SerenaClient:
    def __init__(
        self,
        *,
        repo_root: Path,
        transport: str,
        timeout_ms: int,
        url: str,
        python_bin: str,
        server_script: Path,
    ) -> None:
        self.repo_root = repo_root
        self.transport = transport
        self.timeout_ms = max(timeout_ms, 100)
        self.url = url
        self.python_bin = python_bin
        self.server_script = server_script

    @classmethod
    def from_repo(cls, repo_root: Path) -> "SerenaClient":
        url = os.getenv("OPENCLAW_SERENA_URL", "http://127.0.0.1:8765/mcp").strip()
        transport = os.getenv("OPENCLAW_SERENA_TRANSPORT", "").strip().lower()
        if transport not in {"http", "stdio"}:
            transport = "http" if os.getenv("OPENCLAW_SERENA_URL", "").strip() else "stdio"
        python_bin = os.getenv("OPENCLAW_SERENA_PYTHON", sys.executable).strip() or sys.executable
        script_default = repo_root / "07_scripts" / "serena_mcp.py"
        server_script = Path(os.getenv("OPENCLAW_SERENA_SCRIPT", str(script_default))).resolve()
        timeout_ms = int(os.getenv("OPENCLAW_SERENA_TIMEOUT_MS", "4000"))
        return cls(
            repo_root=repo_root,
            transport=transport,
            timeout_ms=timeout_ms,
            url=url,
            python_bin=python_bin,
            server_script=server_script,
        )

    def config_snapshot(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "transport": self.transport,
            "timeout_ms": self.timeout_ms,
            "url": self.url if self.transport == "http" else "",
            "server_script": str(self.server_script) if self.transport == "stdio" else "",
            "python_bin": self.python_bin if self.transport == "stdio" else "",
            "auto_enabled": _env_bool("OPENCLAW_SERENA_ENABLED", True),
        }
        return payload

    def healthcheck(self) -> dict[str, Any]:
        try:
            sequence = self._run_sequence([])
        except SerenaAdapterError as exc:
            return {
                "status": "unavailable",
                "error": str(exc),
                "transport": self.transport,
                "config": self.config_snapshot(),
            }
        missing = sorted(REQUIRED_TOOLS - _normalize_tool_names(sequence["tool_names"]))
        status = "ok" if not missing else "degraded"
        return {
            "status": status,
            "transport": self.transport,
            "tool_names": sequence["tool_names"],
            "missing_tools": missing,
            "server": sequence["server"],
            "protocol_version": sequence["protocol_version"],
            "config": self.config_snapshot(),
        }

    def fetch_compact(
        self,
        *,
        query: str,
        paths: list[str],
        limit: int = 3,
        context_lines: int = 1,
    ) -> dict[str, Any]:
        payload = self._run_sequence(
            [
                (
                    "context.fetch_compact",
                    {
                        "query": query,
                        "paths": paths,
                        "limit": limit,
                        "context_lines": context_lines,
                    },
                )
            ]
        )
        result = payload["calls"][0]["response"]
        result["tool_name"] = "context.fetch_compact"
        result["transport"] = self.transport
        return result

    def preflight(
        self,
        *,
        tool_name: str,
        target_paths: list[str],
        step_id: str = "",
        source_event_id: str = "",
        intent: str = "",
    ) -> dict[str, Any]:
        payload = self._run_sequence(
            [
                (
                    "governance.preflight",
                    {
                        "tool_name": tool_name,
                        "target_paths": target_paths,
                        "step_id": step_id,
                        "source_event_id": source_event_id,
                        "intent": intent,
                    },
                )
            ]
        )
        result = payload["calls"][0]["response"]
        result["tool_name"] = "governance.preflight"
        result["transport"] = self.transport
        return result

    def _run_sequence(self, calls: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
        if self.transport == "http":
            return self._run_http_sequence(calls)
        if self.transport == "stdio":
            return self._run_stdio_sequence(calls)
        raise SerenaTransportError(f"Transporte Serena no soportado: {self.transport}")

    def _run_http_sequence(self, calls: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
        init = self._post_jsonrpc(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-03-26"},
            }
        )
        self._post_jsonrpc({"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}})
        tools = self._post_jsonrpc({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        responses = []
        for index, (name, arguments) in enumerate(calls, start=10):
            response = self._post_jsonrpc(
                {
                    "jsonrpc": "2.0",
                    "id": index,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                }
            )
            responses.append({"name": name, "arguments": arguments, "response": self._extract_tool_response(response)})
        return {
            "server": dict(init.get("result", {}).get("serverInfo", {})),
            "protocol_version": str(init.get("result", {}).get("protocolVersion", "")),
            "tool_names": [str(item["name"]) for item in tools.get("result", {}).get("tools", [])],
            "calls": responses,
        }

    def _run_stdio_sequence(self, calls: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
        env = dict(os.environ, SISTEMA_TESIS_ROOT=str(self.repo_root))
        process = subprocess.Popen(
            [self.python_bin, str(self.server_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.repo_root,
            env=env,
        )
        try:
            init = self._stdio_send(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {"protocolVersion": "2025-03-26"},
                },
            )
            self._stdio_send(process, {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}, expect_response=False)
            tools = self._stdio_send(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            responses = []
            for index, (name, arguments) in enumerate(calls, start=10):
                response = self._stdio_send(
                    process,
                    {
                        "jsonrpc": "2.0",
                        "id": index,
                        "method": "tools/call",
                        "params": {"name": name, "arguments": arguments},
                    },
                )
                responses.append({"name": name, "arguments": arguments, "response": self._extract_tool_response(response)})
            return {
                "server": dict(init.get("result", {}).get("serverInfo", {})),
                "protocol_version": str(init.get("result", {}).get("protocolVersion", "")),
                "tool_names": [str(item["name"]) for item in tools.get("result", {}).get("tools", [])],
                "calls": responses,
            }
        finally:
            process.kill()
            process.wait(timeout=max(1, self.timeout_ms // 1000))

    def _post_jsonrpc(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib_request.Request(
            self.url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        timeout_seconds = self.timeout_ms / 1000
        try:
            with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
                body = response.read()
        except urllib_error.URLError as exc:
            raise SerenaTransportError(f"Serena HTTP no disponible en {self.url}: {exc.reason}") from exc
        if not body:
            return {}
        parsed = json.loads(body.decode("utf-8"))
        self._raise_jsonrpc_error(parsed)
        return parsed

    def _stdio_send(self, process: subprocess.Popen[bytes], payload: dict[str, Any], *, expect_response: bool = True) -> dict[str, Any]:
        if process.stdin is None or process.stdout is None:
            raise SerenaTransportError("El proceso Serena no expuso stdin/stdout.")
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        message = f"Content-Length: {len(body)}\r\n\r\n".encode("ascii") + body
        process.stdin.write(message)
        process.stdin.flush()
        if not expect_response:
            return {}
        response = self._stdio_read(process.stdout)
        self._raise_jsonrpc_error(response)
        return response

    def _stdio_read(self, stream: Any) -> dict[str, Any]:
        headers: dict[str, str] = {}
        while True:
            line = stream.readline()
            if not line:
                raise SerenaTransportError("El servidor Serena cerró la conexión.")
            if line in (b"\r\n", b"\n"):
                break
            key, value = line.decode("ascii").split(":", 1)
            headers[key.strip().lower()] = value.strip()
        if "content-length" not in headers:
            raise SerenaProtocolError("Serena no devolvió Content-Length.")
        length = int(headers["content-length"])
        body = stream.read(length)
        if not body:
            raise SerenaProtocolError("Serena devolvió un cuerpo vacío.")
        return json.loads(body.decode("utf-8"))

    def _raise_jsonrpc_error(self, payload: dict[str, Any]) -> None:
        if not payload:
            return
        if "error" in payload:
            error_payload = payload["error"]
            message = str(error_payload.get("message", "Error MCP"))
            raise SerenaToolError(message)

    def _extract_tool_response(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = dict(payload.get("result", {}))
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        if isinstance(result.get("content"), list):
            return {"content": result["content"]}
        raise SerenaProtocolError("La respuesta de Serena no contiene structuredContent.")
