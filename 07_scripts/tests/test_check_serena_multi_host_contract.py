import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])) # 07_scripts root
sys.path.insert(0, str(Path(__file__).resolve().parent))     # subdirectory siblings


import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

import check_serena_multi_host_contract as contract  # noqa: E402
from utils.data_io import dump_structured_path  # noqa: E402

class TestSerenaMultiHostContract(unittest.TestCase):
    def test_current_repo_contract_is_ok(self):
        report = contract.build_report(ROOT)
        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["configured_tool_count"], 29)
        self.assertTrue(report["checks"]["contract_doc_lists_29_tools"])

    def test_missing_tool_degrades_report(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo = Path(tmp_dir)
            (repo / "00_sistema_tesis" / "documentacion_sistema").mkdir(parents=True)
            (repo / "00_sistema_tesis" / "documentacion_sistema" / "contrato_serena_mcp_agentes.md").write_text(
                "\n".join(contract.public_name(tool) for tool in contract.EXPECTED_TOOLS)
                + "\nCodex OpenClaw Copilot Antigravity Cursor JetBrains\n",
                encoding="utf-8",
            )
            dump_structured_path(
                repo / "00_sistema_tesis" / "config" / "serena_mcp.json",
                {
                    "tools": {tool: {} for tool in contract.EXPECTED_TOOLS[:-1]},
                    "bridge": {"enabled": True, "auth": {"enabled": True, "env_var": "SERENA_BRIDGE_BEARER_TOKEN"}, "endpoint": "/mcp/serena"},
                },
            )
            dump_structured_path(
                repo / ".vscode" / "mcp.json",
                {"servers": {"serena-local": {"type": "http", "url": "http://127.0.0.1:8765/mcp"}}},
            )
            dump_structured_path(
                repo / "docs" / "03_operacion" / "serena-mcp-host-template.json",
                {"servers": {"serena-local": {"type": "http"}, "serena-local-py": {"type": "stdio"}}},
            )
            dump_structured_path(
                repo / "docs" / "03_operacion" / "serena-bridge-external-template.json",
                {"servers": {"serena-local-bridge": {"headers": {"Authorization": "Bearer ${SERENA_BRIDGE_BEARER_TOKEN}"}}}},
            )
            report = contract.build_report(repo)
        self.assertEqual(report["status"], "degraded")
        self.assertEqual(report["missing_config_tools"], ["trace.append_operation"])

if __name__ == "__main__":
    unittest.main()
