import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from main import parse_fallback_tool_calls, AgentRunner, QwenClient
from tools import ToolRegistry

class TestMainAgent(unittest.TestCase):
    def test_fallback_tag_parsing(self):
        text = 'Thinking... <tool_call>{"name": "app_launch", "arguments": {"app_path": "notepad.exe"}}</tool_call>'
        calls = parse_fallback_tool_calls(text)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["function"]["name"], "app_launch")
        args = json.loads(calls[0]["function"]["arguments"])
        self.assertEqual(args["app_path"], "notepad.exe")

    def test_agent_runner_flow(self):
        mock_client = MagicMock(spec=QwenClient)
        mock_registry = MagicMock(spec=ToolRegistry)
        mock_registry.get_schemas.return_value = []
        mock_registry.execute.return_value = {"success": True}

        mock_client.chat_completion.side_effect = [
            {
                "choices": [{
                    "message": {
                        "content": None,
                        "tool_calls": [{
                            "id": "c1",
                            "function": {
                                "name": "app_launch",
                                "arguments": '{"app_path": "notepad.exe"}'
                            }
                        }]
                    }
                }]
            },
            {
                "choices": [{
                    "message": {
                        "content": "Notepad is opened!",
                        "tool_calls": []
                    }
                }]
            }
        ]

        runner = AgentRunner(mock_client, mock_registry)
        runner.run_turn("open notepad")

        mock_registry.execute.assert_called_once_with("app_launch", app_path="notepad.exe")
        self.assertEqual(len(runner.messages), 5)

if __name__ == "__main__":
    unittest.main()
