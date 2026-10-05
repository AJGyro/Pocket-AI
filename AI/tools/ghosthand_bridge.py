"""
GhostHand OpenCode Bridge.

Translates OpenCode tool requests to the existing GhostHand Python layer
using GhostHandClient as the single execution layer.
Preserves session state across tool calls without bypassing GhostHandClient.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure E:\AI is on sys.path
AI_DIR = Path(__file__).resolve().parent.parent
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from tools.ghosthand.client import GhostHandClient
from tools.ghosthand.errors import ErrorCode, GhostHandException
from tools.ghosthand.tools.session import SessionAttachTool, SessionStatusTool, SessionEndTool
from tools.ghosthand.tools.window import WindowListTool, WindowFocusTool, WindowCloseTool
from tools.ghosthand.tools.observe import UiObserveTool, UiFindTool, UiGetPropertiesTool
from tools.ghosthand.tools.action import (
    AppLaunchTool,
    UiClickTool,
    UiTypeTool,
    UiSetValueTool,
    UiKeysTool,
    APP_PROFILES,
)

SESSION_STATE_FILE = AI_DIR / ".ghosthand_active_session.json"


def load_session_state() -> Dict[str, Any]:
    if SESSION_STATE_FILE.exists():
        try:
            with open(SESSION_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_session_state(state: Dict[str, Any]) -> None:
    try:
        with open(SESSION_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass


def clear_session_state() -> None:
    try:
        if SESSION_STATE_FILE.exists():
            SESSION_STATE_FILE.unlink()
    except Exception:
        pass


def create_client() -> GhostHandClient:
    state = load_session_state()
    session_file = state.get("session_file")
    
    # Verify session file actually exists on disk before reusing it
    if session_file and not os.path.exists(session_file):
        session_file = None
        
    client = GhostHandClient(session_file=session_file)
    client.active_pid = state.get("active_pid")
    client.active_process = state.get("active_process")
    client.active_window = state.get("active_window")
    return client


def persist_client_state(client: GhostHandClient) -> None:
    state = client.get_state()
    save_session_state(state)


def get_recovery_hint(error_code: str, action: str, error_msg: str) -> str:
    code = (error_code or "").upper()
    msg_lower = (error_msg or "").lower()

    if "not found" in msg_lower or code in ("ELEMENT_NOT_FOUND", "ELEMENTNOTFOUND"):
        return "Call ghosthand_ui_observe before retrying to refresh the UI tree and find the valid element ID."
    if "session" in msg_lower or code in ("SESSION_NOT_FOUND", "SESSION_EXPIRED", "NO_ACTIVE_SESSION"):
        return "No active session. Call ghosthand_app_launch to start the application, or ghosthand_session_attach if it is already open."
    if "window" in msg_lower or code in ("WINDOW_NOT_FOUND", "WINDOWNOTFOUND"):
        return "Target window was not found. Call ghosthand_window_list to see available windows or ghosthand_app_launch to launch the application."
    if "disabled" in msg_lower or code in ("ELEMENT_DISABLED", "ELEMENTDISABLED"):
        return "The element is currently disabled. Check the application state or prerequisites before interacting."
    if "offscreen" in msg_lower or code in ("ELEMENT_OFFSCREEN", "ELEMENTOFFSCREEN"):
        return "The element is offscreen. Use ghosthand_window_focus or scroll it into view before clicking."
    if "timeout" in msg_lower or code == "TIMEOUT":
        return "The operation timed out. Verify that the application is running and responsive, then try again."
    if code == "LAUNCH_VALIDATION_FAILED":
        return "Launch validation failed. Call ghosthand_window_list to inspect running windows, or call ghosthand_session_attach with window_title."
    return f"Verify the inputs for {action} and call ghosthand_ui_observe to verify the current UI state."


def execute_action(action: str, params: Dict[str, Any]) -> Dict[str, Any]:
    # Strip ghosthand_ prefix if present
    canonical_action = action
    if canonical_action.startswith("ghosthand_"):
        canonical_action = canonical_action[len("ghosthand_"):]

    client = create_client()

    tools_map = {
        "app_launch": AppLaunchTool(client),
        "session_attach": SessionAttachTool(client),
        "session_status": SessionStatusTool(client),
        "session_end": SessionEndTool(client),
        "window_list": WindowListTool(client),
        "window_focus": WindowFocusTool(client),
        "window_close": WindowCloseTool(client),
        "ui_observe": UiObserveTool(client),
        "ui_find": UiFindTool(client),
        "ui_get_properties": UiGetPropertiesTool(client),
        "ui_click": UiClickTool(client),
        "ui_type": UiTypeTool(client),
        "ui_set_value": UiSetValueTool(client),
        "ui_keys": UiKeysTool(client),
    }

    tool = tools_map.get(canonical_action)
    if not tool:
        return {
            "success": False,
            "error_code": "UNKNOWN_TOOL",
            "message": f"Unknown GhostHand tool: {action}",
            "recoverable": False,
            "recovery_hint": f"Choose one of the supported tools: {list(tools_map.keys())}",
        }

    # Handle collision prevention for session_attach when switching apps
    if canonical_action == "session_attach":
        proc_name = params.get("process_name")
        if proc_name:
            proc_key = proc_name.lower().replace(".exe", "")
            profile = APP_PROFILES.get(proc_key)
            if profile:
                target_session = os.path.abspath(profile["default_session_name"])
            else:
                target_session = os.path.abspath(f"{proc_key}.session.json")
            # If switching process, do not inherit old session file from previous process
            if client.active_process and client.active_process.lower() != proc_key:
                client.session_file = target_session

    try:
        raw_result = tool.execute(**params)

        # Update and persist session state after execution
        if canonical_action == "session_end":
            clear_session_state()
        else:
            persist_client_state(client)

        # Check if the result dictionary indicates failure
        if isinstance(raw_result, dict):
            if raw_result.get("success") is False:
                err_code = raw_result.get("error_code") or raw_result.get("code") or "ACTION_FAILED"
                msg = raw_result.get("message") or raw_result.get("error") or "Operation failed"
                return {
                    "success": False,
                    "error_code": err_code,
                    "message": msg,
                    "recoverable": raw_result.get("recoverable", True),
                    "recovery_hint": get_recovery_hint(err_code, canonical_action, msg),
                    "raw": raw_result,
                }
            return raw_result
        return {"success": True, "result": raw_result}

    except GhostHandException as ghe:
        persist_client_state(client)
        err_code = ghe.code.value if hasattr(ghe.code, "value") else str(ghe.code)
        return {
            "success": False,
            "error_code": err_code,
            "message": ghe.message,
            "recoverable": ghe.recoverable,
            "recovery_hint": get_recovery_hint(err_code, canonical_action, ghe.message),
            "detail": ghe.detail,
        }
    except Exception as ex:
        persist_client_state(client)
        msg = str(ex)
        return {
            "success": False,
            "error_code": "EXCEPTION",
            "message": msg,
            "recoverable": True,
            "recovery_hint": get_recovery_hint("EXCEPTION", canonical_action, msg),
        }


def main():
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error_code": "INVALID_ARGUMENT",
            "message": "Usage: ghosthand_bridge.py <action> [params_json]",
            "recoverable": False,
            "recovery_hint": "Specify an action name and optional JSON parameters.",
        }))
        sys.exit(1)

    action = sys.argv[1]
    params: Dict[str, Any] = {}

    if len(sys.argv) >= 3 and sys.argv[2] != "-":
        try:
            params = json.loads(sys.argv[2])
        except Exception as ex:
            print(json.dumps({
                "success": False,
                "error_code": "JSON_PARSE_ERROR",
                "message": f"Failed to parse parameters JSON: {str(ex)}",
                "recoverable": False,
                "recovery_hint": "Ensure arguments are passed as valid JSON.",
            }))
            sys.exit(1)
    elif len(sys.argv) >= 3 and sys.argv[2] == "-":
        stdin_content = sys.stdin.read().strip()
        if stdin_content:
            try:
                params = json.loads(stdin_content)
            except Exception as ex:
                print(json.dumps({
                    "success": False,
                    "error_code": "JSON_PARSE_ERROR",
                    "message": f"Failed to parse stdin parameters JSON: {str(ex)}",
                    "recoverable": False,
                    "recovery_hint": "Ensure arguments on stdin are valid JSON.",
                }))
                sys.exit(1)

    res = execute_action(action, params)
    print(json.dumps(res, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
