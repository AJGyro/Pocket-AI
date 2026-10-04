import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from tools import ToolRegistry, register_all_tools
from tools.ghosthand.client import GhostHandClient
from tools.ghosthand.tools.action import AppLaunchTool
from tools.ghosthand.tools.observe import UiFindTool

class TestGhostHandRegression(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock(spec=GhostHandClient)
        self.mock_client.session_file = None
        self.registry = ToolRegistry()

    # Test 1 & 2: ToolRegistry.execute accepts name="2" without argument collision
    def test_registry_execute_name_collision(self):
        ui_find = UiFindTool(self.mock_client)
        self.registry.register(ui_find)
        self.mock_client.elem_find.return_value = {
            "success": True,
            "id": "btn_2",
            "name": "2",
            "control_type": "Button",
        }

        # Must execute without "got multiple values for argument 'name'"
        res = self.registry.execute("ui_find", control_type="Button", name="2")
        self.assertTrue(res["success"])
        self.assertEqual(res["id"], "btn_2")

    # Test 3: Existing chrome session cannot cause app_launch("notepad.exe") to return Chrome
    @patch("subprocess.Popen")
    @patch("tools.ghosthand.tools.action.get_running_pids")
    def test_existing_chrome_session_cannot_cause_notepad_to_return_chrome(self, mock_pids, mock_popen):
        mock_pids.return_value = {1000}
        mock_proc = MagicMock()
        mock_proc.pid = 9999
        mock_popen.return_value = mock_proc

        # Mock session_attach mistakenly returning Chrome
        self.mock_client.session_attach.return_value = {
            "success": True,
            "sessionFile": r"E:\AI\chrome.session.json",
            "pid": 2136,
            "processName": "chrome",
            "mainWindowTitle": "Pocket AI - Google Chrome",
        }

        tool = AppLaunchTool(self.mock_client)
        res = tool.execute(app_path="notepad.exe", timeout_ms=500)

        # Must fail launch validation, never return Chrome
        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "LAUNCH_VALIDATION_FAILED")
        self.assertIn("chrome", res["message"])

    # Test 4: Existing old session cannot cause unrelated attachment
    @patch("subprocess.Popen")
    @patch("tools.ghosthand.tools.action.get_running_pids")
    def test_unrelated_old_process_attachment_fails_validation(self, mock_pids, mock_popen):
        mock_pids.return_value = set()
        mock_proc = MagicMock()
        mock_proc.pid = 1111
        mock_popen.return_value = mock_proc

        self.mock_client.session_attach.return_value = {
            "success": True,
            "sessionFile": r"E:\AI\explorer.session.json",
            "pid": 555,
            "processName": "explorer",
            "mainWindowTitle": "File Explorer",
        }

        tool = AppLaunchTool(self.mock_client)
        res = tool.execute(app_path="notepad.exe", timeout_ms=500)
        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "LAUNCH_VALIDATION_FAILED")

    # Test 5: app_launch result must match requested application
    @patch("subprocess.Popen")
    @patch("tools.ghosthand.tools.action.get_running_pids")
    def test_app_launch_success_when_matching_notepad(self, mock_pids, mock_popen):
        mock_pids.side_effect = [{100}, {100, 200}]
        mock_proc = MagicMock()
        mock_proc.pid = 200
        mock_popen.return_value = mock_proc

        self.mock_client.session_attach.return_value = {
            "success": True,
            "sessionFile": r"E:\AI\notepad.session.json",
            "pid": 200,
            "processName": "Notepad",
            "mainWindowTitle": "Untitled - Notepad",
        }

        tool = AppLaunchTool(self.mock_client)
        res = tool.execute(app_path="notepad.exe", timeout_ms=1000)
        self.assertTrue(res["success"])
        self.assertEqual(res["processName"], "Notepad")

    # Test 6: Calculator may use ApplicationFrameHost if window is Calculator
    @patch("subprocess.Popen")
    @patch("tools.ghosthand.tools.action.get_running_pids")
    def test_calculator_application_frame_host_validation(self, mock_pids, mock_popen):
        mock_pids.return_value = set()
        mock_proc = MagicMock()
        mock_proc.pid = 300
        mock_popen.return_value = mock_proc

        # Case A: Window is Calculator -> ACCEPT
        self.mock_client.session_attach.return_value = {
            "success": True,
            "sessionFile": r"E:\AI\calculator.session.json",
            "pid": 30580,
            "processName": "ApplicationFrameHost",
            "mainWindowTitle": "Calculator",
        }

        tool = AppLaunchTool(self.mock_client)
        res_ok = tool.execute(app_path="calc.exe", timeout_ms=500)
        self.assertTrue(res_ok["success"])

        # Case B: Window is Photos or Settings -> REJECT
        self.mock_client.session_attach.return_value = {
            "success": True,
            "sessionFile": r"E:\AI\calculator.session.json",
            "pid": 40000,
            "processName": "ApplicationFrameHost",
            "mainWindowTitle": "Settings",
        }
        res_bad = tool.execute(app_path="calc.exe", timeout_ms=500)
        self.assertFalse(res_bad["success"])
        self.assertEqual(res_bad["error_code"], "LAUNCH_VALIDATION_FAILED")

    # Test 7 & 8: Calculator semantic lookup for "2", "+", "7", "4", "="
    def test_calculator_semantic_lookup(self):
        ui_find = UiFindTool(self.mock_client)

        def mock_elem_find(aid=None, name=None, control_type=None, **kwargs):
            # Simulate Windows Calculator UIA: literal name "2" doesn't exist, but num2Button or "Two" exists
            if aid == "num2Button" or name == "Two":
                return {"success": True, "id": "btn_2", "name": "Two", "automationId": "num2Button"}
            if aid == "plusButton" or name == "Plus":
                return {"success": True, "id": "btn_plus", "name": "Plus", "automationId": "plusButton"}
            if aid == "num7Button" or name == "Seven":
                return {"success": True, "id": "btn_7", "name": "Seven", "automationId": "num7Button"}
            if aid == "num4Button" or name == "Four":
                return {"success": True, "id": "btn_4", "name": "Four", "automationId": "num4Button"}
            if aid == "equalButton" or name == "Equals":
                return {"success": True, "id": "btn_eq", "name": "Equals", "automationId": "equalButton"}
            return {"success": False, "message": "Element not found."}

        self.mock_client.elem_find.side_effect = mock_elem_find

        # Lookup "2"
        res2 = ui_find.execute(control_type="Button", name="2")
        self.assertTrue(res2["success"])
        self.assertEqual(res2["id"], "btn_2")

        # Lookup "+"
        res_plus = ui_find.execute(control_type="Button", name="+")
        self.assertTrue(res_plus["success"])
        self.assertEqual(res_plus["id"], "btn_plus")

        # Lookup "7"
        res7 = ui_find.execute(control_type="Button", name="7")
        self.assertTrue(res7["success"])
        self.assertEqual(res7["id"], "btn_7")

        # Lookup "4"
        res4 = ui_find.execute(control_type="Button", name="4")
        self.assertTrue(res4["success"])
        self.assertEqual(res4["id"], "btn_4")

        # Lookup "="
        res_eq = ui_find.execute(control_type="Button", name="=")
        self.assertTrue(res_eq["success"])
        self.assertEqual(res_eq["id"], "btn_eq")

    # Test 9: Multiple existing sessions do not cause ambiguity
    def test_client_explicit_session_passing(self):
        client = GhostHandClient(session_file=r"E:\AI\notepad.session.json")
        with patch("subprocess.run") as mock_run:
            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stdout = '{"success": true}'
            mock_proc.stderr = ""
            mock_run.return_value = mock_proc

            client.elem_find(aid="test")
            called_cmd = mock_run.call_args[0][0]
            # Must explicitly include --session E:\AI\notepad.session.json
            self.assertIn("--session", called_cmd)
            self.assertIn(r"E:\AI\notepad.session.json", called_cmd)

    # Test 10: Invalid launch/session association returns failure
    @patch("subprocess.Popen")
    @patch("tools.ghosthand.tools.action.get_running_pids")
    def test_invalid_launch_returns_failure_not_false_success(self, mock_pids, mock_popen):
        mock_pids.return_value = set()
        mock_proc = MagicMock()
        mock_proc.pid = 999
        mock_popen.return_value = mock_proc

        self.mock_client.session_attach.return_value = {
            "success": True,
            "sessionFile": r"E:\AI\unknown.session.json",
            "pid": 888,
            "processName": "something_else",
            "mainWindowTitle": "Something",
        }

        tool = AppLaunchTool(self.mock_client)
        res = tool.execute(app_path="notepad.exe", timeout_ms=300)
        self.assertFalse(res["success"])
        self.assertEqual(res["error_code"], "LAUNCH_VALIDATION_FAILED")

    # Test 11: Repeated app_launch calls do not oscillate
    @patch("subprocess.Popen")
    @patch("tools.ghosthand.tools.action.get_running_pids")
    def test_repeated_app_launch_does_not_oscillate(self, mock_pids, mock_popen):
        mock_pids.return_value = set()
        mock_proc = MagicMock()
        mock_proc.pid = 1234
        mock_popen.return_value = mock_proc

        self.mock_client.session_attach.return_value = {
            "success": True,
            "sessionFile": r"E:\AI\notepad.session.json",
            "pid": 1234,
            "processName": "Notepad",
            "mainWindowTitle": "Untitled - Notepad",
        }

        tool = AppLaunchTool(self.mock_client)
        res1 = tool.execute(app_path="notepad.exe", timeout_ms=500)
        res2 = tool.execute(app_path="notepad.exe", timeout_ms=500)
        self.assertTrue(res1["success"])
        self.assertTrue(res2["success"])
        self.assertEqual(res1["processName"], "Notepad")
        self.assertEqual(res2["processName"], "Notepad")

    # Test 12: Semantic identification eliminates need to guess element IDs
    def test_semantic_identification_avoids_guessing(self):
        ui_find = UiFindTool(self.mock_client)
        self.mock_client.elem_find.return_value = {
            "success": True,
            "id": "e_calc_result",
            "name": "Display is 0",
            "automationId": "CalculatorResults",
            "controlType": "Text",
        }
        res = ui_find.execute(automation_id="CalculatorResults")
        self.assertTrue(res["success"])
        self.assertEqual(res["id"], "e_calc_result")

if __name__ == "__main__":
    unittest.main()
