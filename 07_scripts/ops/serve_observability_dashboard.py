from __future__ import annotations

import json
import os
import secrets
import sys
from datetime import UTC, datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import ROOT
from utils.data_io import append_jsonl_path, dump_structured_path
from observability_snapshot import build_snapshot


DEFAULT_HOST = os.getenv("SIOT_OBSERVABILITY_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("SIOT_OBSERVABILITY_PORT", "8082"))
CONTROL_QUEUE = ROOT / "runtime" / "observability" / "control_requests.jsonl"
HEARTBEAT_PATH = ROOT / "runtime" / "observability" / "dashboard_heartbeat.json"


def auth_ok(headers: Any) -> bool:
    token = os.getenv("SIOT_OBSERVABILITY_TOKEN", "").strip()
    if not token or token == "change-me-local-only":
        return False
    auth = str(headers.get("Authorization", ""))
    if not auth.startswith("Bearer "):
        return False
    return secrets.compare_digest(auth.removeprefix("Bearer ").strip(), token)


class ObservabilityHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(ROOT / "06_dashboard" / "generado"), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.startswith("/api/observability"):
            if not auth_ok(self.headers):
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(b'{"status":"unauthorized","detail":"missing_or_invalid_bearer_token"}')
                return
            payload = build_snapshot(public=False)
            rendered = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(rendered)
            return
        if self.path.startswith("/api/public-observability"):
            payload = build_snapshot(public=True)
            rendered = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(rendered)
            return
        super().do_GET()

    def do_POST(self) -> None:  # noqa: N802
        if not auth_ok(self.headers):
            self.send_response(401)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(b'{"status":"unauthorized","detail":"missing_or_invalid_bearer_token"}')
            return
        if self.path == "/api/heartbeat":
            payload = {
                "status": "active",
                "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "client": self.client_address[0],
                "telegram_suppression": True,
            }
            dump_structured_path(HEARTBEAT_PATH, payload)
            self._json_response({"status": "ok", "heartbeat": payload})
            return
        if self.path == "/api/control/request":
            content_length = int(self.headers.get("Content-Length", "0") or "0")
            raw_body = self.rfile.read(min(content_length, 16384))
            try:
                body = json.loads(raw_body.decode("utf-8") or "{}")
            except json.JSONDecodeError:
                self._json_response({"status": "bad_request", "detail": "invalid_json"}, status=400)
                return
            request_record = {
                "request_id": f"OBS-REQ-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
                "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "source": "observability_dashboard",
                "client": self.client_address[0],
                "orchestrator": "OpenClaw",
                "status": "pending_human_approval",
                "requires_human_approval": True,
                "direct_execution": False,
                "payload": {
                    "intent": str(body.get("intent", "diagnose_stack"))[:80],
                    "target": str(body.get("target", "stack"))[:120],
                    "reason": str(body.get("reason", ""))[:1000],
                    "prechecks": body.get("prechecks", []),
                },
            }
            append_jsonl_path(CONTROL_QUEUE, request_record)
            self._json_response({"status": "queued", "request": request_record}, status=202)
            return
        self._json_response({"status": "not_found"}, status=404)

    def _json_response(self, payload: dict[str, Any], status: int = 200) -> None:
        rendered = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(rendered)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return


def main() -> int:
    token = os.getenv("SIOT_OBSERVABILITY_TOKEN", "").strip()
    if not token or token == "change-me-local-only":
        print("[ERROR] Falta SIOT_OBSERVABILITY_TOKEN real para exponer la vista privada en LAN.")
        return 2
    server = ThreadingHTTPServer((DEFAULT_HOST, DEFAULT_PORT), ObservabilityHandler)
    print(f"[OK] Observability command center en http://{DEFAULT_HOST}:{DEFAULT_PORT}")
    print("[OK] API privada protegida: /api/observability")
    print("[OK] Control gobernado: /api/control/request y /api/heartbeat")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
