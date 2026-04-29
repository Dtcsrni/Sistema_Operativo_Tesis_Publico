import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "07_scripts"))

import agent_task_router  # noqa: E402


class TestAgentTaskRouter(unittest.TestCase):
    def setUp(self):
        self.config = {
            "privacy_classes": ["public", "redacted", "private", "restricted"],
            "risk_levels": ["BAJO", "MEDIO", "ALTO", "CRITICO"],
            "default_route": "wsl_native",
            "cloud_free_routes": ["github_models_free"],
            "external_context_routes": ["context7_docs"],
            "cloud_allowed_privacy_classes": ["public", "redacted"],
            "context7_allowed_privacy_classes": ["public", "redacted"],
            "github_models": {"required_env_vars": ["GITHUB_MODELS_TOKEN"]},
            "sensitive_path_prefixes": ["00_sistema_tesis/evidencia_privada/", "00_sistema_tesis/canon/"],
            "route_preferences": {
                "docs_external": ["context7_docs", "serena", "wsl_native"],
                "academic_heavy": ["pc_native_llamacpp", "ollama_local", "serena", "wsl_native"],
                "public_cloud": ["github_models_free", "context7_docs", "serena", "wsl_native"],
                "repo_governance": ["serena", "wsl_native"],
                "default": ["serena", "ollama_local", "wsl_native"],
            },
            "quality_gate_defaults": {"max_gate_failures": 0},
        }

    def test_private_task_blocks_github_models(self):
        task = {
            "task_id": "T-private",
            "privacy_class": "private",
            "allow_free_cloud": True,
            "allowed_routes": ["github_models_free", "wsl_native"],
        }
        result = agent_task_router.classify_task(task, self.config)
        self.assertEqual(result["recommended_route"], "wsl_native")
        self.assertEqual(result["blocked_routes"]["github_models_free"], "privacy_blocks_free_cloud")

    def test_public_task_allows_github_models_when_token_exists(self):
        task = {
            "task_id": "T-public",
            "privacy_class": "public",
            "allow_free_cloud": True,
        }
        with patch.dict(os.environ, {"GITHUB_MODELS_TOKEN": "token"}, clear=False):
            result = agent_task_router.classify_task(task, self.config)
        self.assertEqual(result["recommended_route"], "github_models_free")

    def test_external_docs_selects_context7(self):
        task = {
            "task_id": "T-docs",
            "privacy_class": "public",
            "requires_external_docs": True,
        }
        result = agent_task_router.classify_task(task, self.config)
        self.assertEqual(result["recommended_route"], "context7_docs")

    def test_heavy_academic_prefers_local_pc_runtime(self):
        task = {
            "task_id": "T-heavy",
            "privacy_class": "private",
            "domain": "academico",
            "complexity": "alta",
        }
        result = agent_task_router.classify_task(task, self.config)
        self.assertEqual(result["recommended_route"], "pc_native_llamacpp")

    def test_sensitive_path_promotes_restricted_privacy(self):
        task = {
            "task_id": "T-canon",
            "privacy_class": "public",
            "target_paths": ["00_sistema_tesis/canon/events.jsonl"],
        }
        result = agent_task_router.classify_task(task, self.config)
        self.assertEqual(result["privacy_class"], "restricted")
        self.assertEqual(result["recommended_route"], "serena")


if __name__ == "__main__":
    unittest.main()
