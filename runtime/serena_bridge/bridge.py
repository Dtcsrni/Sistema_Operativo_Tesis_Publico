from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "07_scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from serena_mcp import LOGGER as SERENA_LOGGER  # noqa: E402
from serena_mcp import SerenaMCPServer, _jsonrpc_error  # noqa: E402
from serena_policy import load_serena_config, resolve_root  # noqa: E402


LOGGER = logging.getLogger("serena_bridge")


def load_bridge_config(root: Path | None = None) -> dict[str, Any]:
    resolved_root = resolve_root(root)
    config = load_serena_config(resolved_root)
    bridge = dict(config.get("bridge", {}))
    auth = dict(bridge.get("auth", {}))
    headers = dict(bridge.get("identity_headers", {}))
    return {
        "enabled": bool(bridge.get("enabled", True)),
        "bind_host": str(bridge.get("bind_host", "127.0.0.1")).strip() or "127.0.0.1",
        "port": int(bridge.get("port", 8766)),
        "endpoint": str(bridge.get("endpoint", "/mcp/serena")).strip() or "/mcp/serena",
        "public_bind_allowed": bool(bridge.get("public_bind_allowed", False)),
        "auth": {
            "enabled": bool(auth.get("enabled", True)),
            "env_var": str(auth.get("env_var", "SERENA_BRIDGE_BEARER_TOKEN")).strip() or "SERENA_BRIDGE_BEARER_TOKEN",
            "scheme": str(auth.get("scheme", "Bearer")).strip() or "Bearer",
        },
        "identity_headers": {
            "agent_role": str(headers.get("agent_role", "X-Sistema-Tesis-Agent-Role")).strip(),
            "provider": str(headers.get("provider", "X-Sistema-Tesis-Agent-Provider")).strip(),
            "model_version": str(headers.get("model_version", "X-Sistema-Tesis-Agent-Model-Version")).strip(),
            "runtime_label": str(headers.get("runtime_label", "X-Sistema-Tesis-Agent-Runtime")).strip(),
            "host_kind": str(headers.get("host_kind", "X-Sistema-Tesis-Host-Kind")).strip(),
        },
    }


def _is_local_host(host: str) -> bool:
    return host in {"127.0.0.1", "localhost", "::1"}


def _resolve_token(config: dict[str, Any]) -> str:
    auth = dict(config.get("auth", {}))
    if not auth.get("enabled", True):
        return ""
    env_var = str(auth.get("env_var", "SERENA_BRIDGE_BEARER_TOKEN")).strip()
    token = os.getenv(env_var, "").strip()
    if not token:
        raise ValueError(f"Falta el token del bridge en la variable de entorno `{env_var}`.")
    return token


def _identity_from_headers(headers: Any, config: dict[str, Any]) -> dict[str, str]:
    mapping = dict(config.get("identity_headers", {}))
    defaults = {
        "agent_role": "Compatible Host (Assistant)",
        "provider": "External Host",
        "model_version": "Unknown",
        "runtime_label": "External MCP Runtime",
        "host_kind": "external_runtime",
    }
    identity: dict[str, str] = {}
    for key, default in defaults.items():
        header_name = str(mapping.get(key, "")).strip()
        value = headers.get(header_name, "").strip() if header_name else ""
        identity[key] = value or default
    return identity


class SerenaBridgeHandler(BaseHTTPRequestHandler):
    server_version = "SerenaBridge/1.0"

    @property
    def bridge_config(self) -> dict[str, Any]:
        return self.server.bridge_config  # type: ignore[attr-defined]

    @property
    def repo_root(self) -> Path:
        return self.server.repo_root  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("HTTP %s", format % args)

    def _is_endpoint(self) -> bool:
        return urlparse(self.path).path == str(self.bridge_config.get("endpoint", "/mcp/serena"))

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any] | list[Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_status(self, status: HTTPStatus) -> None:
        self.send_response(status.value)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _check_auth(self) -> tuple[bool, str]:
        auth = dict(self.bridge_config.get("auth", {}))
        if not auth.get("enabled", True):
            return True, ""
        header = self.headers.get("Authorization", "").strip()
        expected = _resolve_token(self.bridge_config)
        scheme = str(auth.get("scheme", "Bearer")).strip()
        expected_header = f"{scheme} {expected}".strip()
        if header != expected_header:
            return False, "Token de autorización inválido o ausente."
        return True, ""

    def _mcp_server(self) -> SerenaMCPServer:
        identity = _identity_from_headers(self.headers, self.bridge_config)
        return SerenaMCPServer(root=self.repo_root, identity_overrides=identity)

    def do_GET(self) -> None:
        if not self._is_endpoint():
            self._send_status(HTTPStatus.NOT_FOUND)
            return
        try:
            server = self._mcp_server()
            token_configured = bool(_resolve_token(self.bridge_config)) if self.bridge_config.get("auth", {}).get("enabled", True) else False
        except Exception as exc:
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"status": "error", "error": str(exc)})
            return
        self._send_json(
            HTTPStatus.OK,
            {
                "server": server.config.get("server", {}),
                "status": "ok",
                "transport": "streamable-http",
                "endpoint": self.bridge_config.get("endpoint", "/mcp/serena"),
                "auth_enabled": bool(self.bridge_config.get("auth", {}).get("enabled", True)),
                "token_configured": token_configured,
            },
        )

    def do_POST(self) -> None:
        if not self._is_endpoint():
            self._send_status(HTTPStatus.NOT_FOUND)
            return
        authorized, error_message = self._check_auth()
        if not authorized:
            response = _jsonrpc_error(None, -32001, error_message, {"type": "AuthenticationError"})
            self._send_json(HTTPStatus.UNAUTHORIZED, response)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._send_status(HTTPStatus.BAD_REQUEST)
            return
        body = self.rfile.read(length)
        if not body:
            self._send_status(HTTPStatus.BAD_REQUEST)
            return
        try:
            message = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_status(HTTPStatus.BAD_REQUEST)
            return
        try:
            server = self._mcp_server()
            response = server.dispatch_message(message)
        except Exception as exc:
            LOGGER.exception("Serena Bridge error")
            response = _jsonrpc_error(message.get("id"), -32000, str(exc), {"type": exc.__class__.__name__})
        if response is None:
            self._send_status(HTTPStatus.ACCEPTED)
            return
        self._send_json(HTTPStatus.OK, response)


def serve_bridge(*, host: str | None = None, port: int | None = None, root: Path | None = None) -> int:
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    SERENA_LOGGER.setLevel(logging.INFO)
    repo_root = resolve_root(root)
    bridge_config = load_bridge_config(repo_root)
    bind_host = host or str(bridge_config.get("bind_host", "127.0.0.1"))
    bind_port = port or int(bridge_config.get("port", 8766))
    if not bridge_config.get("public_bind_allowed", False) and not _is_local_host(bind_host):
        raise ValueError("El bridge solo puede bindear fuera de localhost cuando public_bind_allowed=true.")
    _resolve_token(bridge_config)
    endpoint = str(bridge_config.get("endpoint", "/mcp/serena"))
    httpd = ThreadingHTTPServer((bind_host, bind_port), SerenaBridgeHandler)
    httpd.bridge_config = bridge_config  # type: ignore[attr-defined]
    httpd.repo_root = repo_root  # type: ignore[attr-defined]
    LOGGER.info("BRIDGE_READY http://%s:%s%s", bind_host, bind_port, endpoint)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info("BRIDGE_STOP keyboard-interrupt")
    finally:
        httpd.server_close()
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Expone Serena MCP por HTTP autenticado para runtimes externos.")
    parser.add_argument("--host", default="", help="Host de bind. Default: config bridge.bind_host.")
    parser.add_argument("--port", type=int, default=0, help="Puerto de bind. Default: config bridge.port.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    host = args.host.strip() or None
    port = args.port or None
    return serve_bridge(host=host, port=port)


if __name__ == "__main__":
    raise SystemExit(main())
