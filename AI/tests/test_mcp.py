import asyncio
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from ghosthand.mcp.server import create_server, SERVER_NAME, SERVER_VERSION
from ghosthand.mcp.serializers import (
    serialize_element,
    serialize_window,
    serialize_error,
    serialize_exception,
    serialize_success,
)
from tools.ghosthand.errors import ErrorCode, GhostHandException


class TestGhostHandMCP(unittest.TestCase):
    """Unit and integration tests for the GhostHand MCP Server."""

    def setUp(self):
        self.server = create_server()

    def test_mcp_server_initialization(self):
        """Test that MCPServer initializes with correct identity."""
        self.assertEqual(self.server.name, SERVER_NAME)
        self.assertEqual(self.server.version, SERVER_VERSION)
        self.assertIn("GhostHand", self.server.instructions)

    def test_tool_listing(self):
        """Verify all 16 core tools are registered and available."""
        async def run():
            tools = await self.server.list_tools()
            tool_names = {t.name for t in tools}
            expected_tools = {
                "ghosthand_window_launch",
                "ghosthand_window_list",
                "ghosthand_window_focus",
                "ghosthand_window_close",
                "ghosthand_element_find",
                "ghosthand_element_click",
                "ghosthand_element_type",
                "ghosthand_element_set_value",
                "ghosthand_element_get_properties",
                "ghosthand_keyboard_press",
                "ghosthand_keyboard_hotkey",
                "ghosthand_session_attach",
                "ghosthand_session_status",
                "ghosthand_session_end",
                "ghosthand_element_tree",
                "ghosthand_screenshot",
            }
            for expected in expected_tools:
                self.assertIn(expected, tool_names, f"Missing tool: {expected}")
            self.assertEqual(len(tool_names), 16)

        asyncio.run(run())

    def test_tool_descriptions_concise(self):
        """Verify tool descriptions are concise and model-friendly to conserve context."""
        async def run():
            tools = await self.server.list_tools()
            for t in tools:
                self.assertTrue(len(t.description) > 10, f"{t.name} description too short")
                self.assertTrue(len(t.description) < 200, f"{t.name} description too long ({len(t.description)} chars)")

        asyncio.run(run())

    def test_serializers_compact_element(self):
        """Verify serialize_element returns only essential keys without bloated internal state."""
        raw_elem = {
            "id": "e_btn1",
            "name": "Save",
            "control_type": "Button",
            "automation_id": "btnSave",
            "internal_flaUI_object": "SHOULD_BE_STRIPPED",
            "runtime_id": [42, 1024],
            "bounding_rectangle": {"top": 100, "left": 200, "width": 80, "height": 30},
        }
        compact = serialize_element(raw_elem)
        self.assertEqual(compact["id"], "e_btn1")
        self.assertEqual(compact["name"], "Save")
        self.assertEqual(compact["control_type"], "Button")
        self.assertEqual(compact["automation_id"], "btnSave")
        self.assertNotIn("internal_flaUI_object", compact)
        self.assertNotIn("runtime_id", compact)

    def test_serializers_compact_window(self):
        """Verify serialize_window produces compact representation."""
        raw_win = {
            "handle": "0x123456",
            "title": "Untitled - Notepad",
            "process_name": "notepad",
            "pid": 5678,
            "raw_win32_extra": "drop_me",
        }
        compact = serialize_window(raw_win)
        self.assertEqual(compact["handle"], "0x123456")
        self.assertEqual(compact["title"], "Untitled - Notepad")
        self.assertEqual(compact["process_name"], "notepad")
        self.assertNotIn("raw_win32_extra", compact)

    def test_serializers_error_format(self):
        """Verify error serialization structure."""
        err = serialize_error(
            code="ELEMENT_NOT_FOUND",
            message="Button not found",
            retryable=True,
            recovery_hint="Check window focus",
        )
        self.assertFalse(err["success"])
        self.assertEqual(err["error"]["code"], "ELEMENT_NOT_FOUND")
        self.assertTrue(err["error"]["retryable"])
        self.assertEqual(err["error"]["recovery_hint"], "Check window focus")

        exc = GhostHandException(ErrorCode.TIMEOUT, "Operation timed out", recoverable=True)
        exc_dict = serialize_exception(exc, "test_action")
        self.assertFalse(exc_dict["success"])
        self.assertEqual(exc_dict["error"]["code"], "TIMEOUT")
        self.assertTrue(exc_dict["error"]["retryable"])

    def test_safe_window_list_execution(self):
        """Verify calling ghosthand_window_list returns a valid JSON response."""
        async def run():
            res = await self.server.call_tool("ghosthand_window_list", {})
            self.assertFalse(res.is_error)
            self.assertTrue(len(res.content) > 0)
            data = json.loads(res.content[0].text)
            self.assertIn("success", data)
            if not data["success"]:
                self.assertIn("error", data)
                self.assertIn("code", data["error"])

        asyncio.run(run())

    @patch("tools.ghosthand.mcp.tools.MANAGER._client")
    def test_mocked_element_click_flow(self, mock_client):
        """Verify element click flow through MCP tool."""
        mock_client.elem_click.return_value = {"success": True}

        async def run():
            res = await self.server.call_tool("ghosthand_element_click", {"element_id": "test_id"})
            self.assertFalse(res.is_error)
            data = json.loads(res.content[0].text)
            self.assertTrue(data["success"])
            self.assertIn("Clicked element 'test_id'", data["message"])

        asyncio.run(run())

    @patch("tools.ghosthand.mcp.tools.MANAGER._client")
    def test_mocked_element_find_flow(self, mock_client):
        """Verify element find returns compact element."""
        mock_client.elem_find.return_value = {
            "success": True,
            "elementId": "elem_42",
            "name": "Text Editor",
            "controlType": "Document",
            "automationId": "15",
        }

        async def run():
            res = await self.server.call_tool(
                "ghosthand_element_find",
                {"name": "Text Editor", "control_type": "Document"},
            )
            self.assertFalse(res.is_error)
            data = json.loads(res.content[0].text)
            self.assertTrue(data["success"])
            self.assertEqual(data["element"]["id"], "elem_42")
            self.assertEqual(data["element"]["name"], "Text Editor")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
