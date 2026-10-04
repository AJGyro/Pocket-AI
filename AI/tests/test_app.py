import json
import os
import sys
import threading
import time
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app import QwenClient, create_server
from tools import ToolRegistry

class TestPocketAIAppServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mock_registry = ToolRegistry()
        mock_tool = MagicMock()
        mock_tool.name = "ui_click"
        mock_tool.description = "Click an element"
        mock_tool.parameters = {"type": "object", "properties": {}}
        mock_tool.to_schema.return_value = {
            "type": "function",
            "function": {
                "name": "ui_click",
                "description": "Click an element",
                "parameters": {},
            },
        }
        mock_tool.execute.return_value = {"success": True, "name": "Calculator"}
        cls.mock_registry.register(mock_tool)

        cls.mock_qwen = MagicMock(spec=QwenClient)
        cls.mock_qwen.model = "qwen2.5-coder-7b"
        cls.mock_qwen.check_health.return_value = True

        cls.dist_dir = ROOT_DIR / "web" / "dist"

        # Start server on ephemeral port (0)
        cls.server = create_server("127.0.0.1", 0, cls.dist_dir, cls.mock_registry, cls.mock_qwen)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_health_endpoint(self):
        url = f"{self.base_url}/health"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["app"], "Pocket AI")
            self.assertEqual(data["engine"], "GhostHand (FlaUI + UIA3)")
            self.assertEqual(data["tools_count"], 1)

    def test_models_endpoint(self):
        url = f"{self.base_url}/v1/models"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            model_ids = [m["id"] for m in data.get("data", [])]
            self.assertIn("pocket-ai-ghosthand", model_ids)

    def test_tools_endpoint(self):
        url = f"{self.base_url}/api/tools"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertTrue(len(data.get("tools", [])) >= 1)

    def test_static_index_serving(self):
        url = f"{self.base_url}/"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            content = resp.read().decode("utf-8")
            self.assertIn("Pocket AI", content)

    def test_chat_completions_streaming(self):
        # Configure mock Qwen to return a response without tool call
        self.mock_qwen.chat_completion.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Notepad is opened and ready!",
                    }
                }
            ]
        }

        url = f"{self.base_url}/v1/chat/completions"
        payload = {
            "model": "pocket-ai-ghosthand",
            "messages": [{"role": "user", "content": "open notepad"}],
            "stream": True,
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            body = resp.read().decode("utf-8")
            self.assertIn("data: ", body)
            self.assertIn("[DONE]", body)
            self.assertIn("Notepad is opened", body)

if __name__ == "__main__":
    unittest.main()
