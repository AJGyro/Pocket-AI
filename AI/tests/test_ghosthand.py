import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools import ToolRegistry, register_all_tools
from tools.ghosthand.errors import ErrorCode, GhostHandException
from tools.ghosthand.models import ElementInfo, WindowInfo, ObservationResult
from tools.ghosthand.client import GhostHandClient
from tools.ghosthand.tools.observe import _flatten_and_filter_tree

class TestGhostHandCore(unittest.TestCase):
    def test_error_code_and_exception(self):
        exc = GhostHandException(ErrorCode.ELEMENT_NOT_FOUND, "Not found", recoverable=True, detail="id=submit")
        self.assertEqual(exc.code, ErrorCode.ELEMENT_NOT_FOUND)
        self.assertTrue(exc.recoverable)
        self.assertEqual(exc.to_dict()["code"], "ELEMENT_NOT_FOUND")

    def test_models_to_dict(self):
        el = ElementInfo(id="e1", name="Submit", control_type="Button", automation_id="btnSubmit")
        d = el.to_dict()
        self.assertEqual(d["id"], "e1")
        self.assertEqual(d["name"], "Submit")
        self.assertEqual(d["control_type"], "Button")

    def test_tree_flatten_and_cap(self):
        tree = {
            "elementId": "root_1",
            "controlType": "Window",
            "name": "Main Window",
            "children": [
                {"elementId": f"btn_{i}", "controlType": "Button", "name": f"Btn {i}", "children": []}
                for i in range(100)
            ],
        }
        res_min = _flatten_and_filter_tree(tree, level="minimal", max_count=10)
        self.assertEqual(len(res_min), 10)
        self.assertEqual(res_min[0]["id"], "root_1")
        self.assertEqual(res_min[0]["control_type"], "Window")
        self.assertEqual(res_min[1]["id"], "btn_0")
        self.assertEqual(res_min[1]["control_type"], "Button")

        res_norm = _flatten_and_filter_tree(tree, level="normal", max_count=50)
        self.assertEqual(len(res_norm), 50)

    def test_tool_registry_registration(self):
        reg = register_all_tools()
        tools = reg.list_tools()
        self.assertGreaterEqual(len(tools), 9)

        names = {t.name for t in tools}
        expected = {
            "session_attach", "session_status", "session_end",
            "window_list", "window_focus", "window_close",
            "ui_observe", "ui_find", "ui_get_properties"
        }
        self.assertTrue(expected.issubset(names))

        schemas = reg.get_schemas()
        self.assertEqual(len(schemas), len(tools))
        for schema in schemas:
            self.assertEqual(schema["type"], "function")
            self.assertIn("name", schema["function"])
            self.assertIn("parameters", schema["function"])

    def test_mocked_client_execution(self):
        mock_client = MagicMock(spec=GhostHandClient)
        mock_client.session_status.return_value = {"success": True, "active": True}
        mock_client.window_list.return_value = {"success": True, "windows": []}
        mock_client.elem_find.return_value = {"success": True, "id": "btn_1"}

        reg = register_all_tools(ghosthand_client=mock_client)
        status_res = reg.execute("session_status")
        self.assertTrue(status_res["success"])
        mock_client.session_status.assert_called_once()

        find_res = reg.execute("ui_find", automation_id="btnSubmit")
        self.assertTrue(find_res["success"])
        mock_client.elem_find.assert_called_once_with(
            aid="btnSubmit",
            name=None,
            control_type=None,
            class_name=None,
            timeout_ms=10000,
            window_handle=None,
        )

if __name__ == "__main__":
    unittest.main()
