"""
GhostHand MCP Tool Implementations.

Maps clean MCP tool calls to the existing GhostHandClient and GhostHand tools.
Preserves session state, returns compact responses, and optimizes context usage.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure AI directory is on sys.path
AI_DIR = Path(__file__).resolve().parents[3]
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from ..client import GhostHandClient
from ..errors import GhostHandException
from ..tools.action import AppLaunchTool, UiClickTool, UiTypeTool, UiSetValueTool, UiKeysTool, APP_PROFILES
from ..tools.observe import UiObserveTool, UiFindTool, UiGetPropertiesTool
from ..tools.session import SessionAttachTool, SessionStatusTool, SessionEndTool
from ..tools.window import WindowListTool, WindowFocusTool, WindowCloseTool
from .serializers import (
    serialize_element,
    serialize_window,
    serialize_error,
    serialize_exception,
    serialize_success,
)

SESSION_STATE_FILE = AI_DIR / ".ghosthand_active_session.json"


class GhostHandManager:
    """Manages the single GhostHandClient instance for the MCP server session."""

    def __init__(self):
        self._client: Optional[GhostHandClient] = None
        self._init_client()

    def _init_client(self) -> None:
        state = self._load_state()
        session_file = state.get("session_file")
        if session_file and not os.path.exists(session_file):
            session_file = None

        self._client = GhostHandClient(session_file=session_file)
        self._client.active_pid = state.get("active_pid")
        self._client.active_process = state.get("active_process")
        self._client.active_window = state.get("active_window")

    @property
    def client(self) -> GhostHandClient:
        if self._client is None:
            self._init_client()
        return self._client

    def _load_state(self) -> Dict[str, Any]:
        if SESSION_STATE_FILE.exists():
            try:
                import json
                with open(SESSION_STATE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def persist_state(self) -> None:
        if self._client:
            state = self._client.get_state()
            try:
                import json
                with open(SESSION_STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
            except Exception:
                pass

    def clear_state(self) -> None:
        try:
            if SESSION_STATE_FILE.exists():
                SESSION_STATE_FILE.unlink()
        except Exception:
            pass


MANAGER = GhostHandManager()


# -------------------------------------------------------------------------
# Window Tools
# -------------------------------------------------------------------------

def tool_window_launch(
    app_path: str,
    args: Optional[str] = None,
    timeout_ms: int = 15000,
) -> Dict[str, Any]:
    """Launch a Windows application and establish an active automation session."""
    client = MANAGER.client
    tool = AppLaunchTool(client)
    try:
        res = tool.execute(app_path=app_path, args=args, timeout_ms=timeout_ms)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code=res.get("error_code", "LAUNCH_FAILED"),
                message=res.get("message", "Application launch failed"),
                retryable=True,
                recovery_hint="Check ghosthand_window_list or retry with ghosthand_session_attach.",
            )

        return serialize_success(
            f"Launched {app_path} successfully",
            session_id=res.get("sessionFile") or client.session_file,
            pid=res.get("pid") or client.active_pid,
            process_name=res.get("processName") or client.active_process,
        )
    except Exception as ex:
        return serialize_exception(ex, "window_launch")


def tool_window_list() -> Dict[str, Any]:
    """List all top-level windows for the active application session."""
    client = MANAGER.client
    try:
        res = client.window_list()
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="WINDOW_LIST_FAILED",
                message=res.get("message", "Could not retrieve window list"),
                retryable=True,
                recovery_hint="Launch an application with ghosthand_window_launch first.",
            )

        raw_windows = res.get("windows") or []
        compact_windows = [serialize_window(w) for w in raw_windows]
        return serialize_success(
            f"Found {len(compact_windows)} window(s)",
            windows=compact_windows,
        )
    except Exception as ex:
        return serialize_exception(ex, "window_list")


def tool_window_focus(window_handle: str) -> Dict[str, Any]:
    """Bring a window to the foreground by its hex handle."""
    client = MANAGER.client
    try:
        res = client.window_focus(window_handle=window_handle)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="FOCUS_FAILED",
                message=res.get("message", f"Could not focus window {window_handle}"),
                retryable=True,
                recovery_hint="Verify window handle using ghosthand_window_list.",
            )

        return serialize_success(f"Brought window {window_handle} to foreground")
    except Exception as ex:
        return serialize_exception(ex, "window_focus")


def tool_window_close(window_handle: str) -> Dict[str, Any]:
    """Close a window by its hex handle."""
    client = MANAGER.client
    try:
        res = client.window_close(window_handle=window_handle)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="CLOSE_FAILED",
                message=res.get("message", f"Could not close window {window_handle}"),
                retryable=True,
            )

        return serialize_success(f"Closed window {window_handle}")
    except Exception as ex:
        return serialize_exception(ex, "window_close")


# -------------------------------------------------------------------------
# Element Inspection & Interaction Tools
# -------------------------------------------------------------------------

def tool_element_find(
    automation_id: Optional[str] = None,
    name: Optional[str] = None,
    control_type: Optional[str] = None,
    class_name: Optional[str] = None,
    timeout_ms: int = 10000,
) -> Dict[str, Any]:
    """Find a specific UI element using semantic properties (automation_id, name, control_type). Returns element ID."""
    client = MANAGER.client
    tool = UiFindTool(client)
    try:
        res = tool.execute(
            automation_id=automation_id,
            name=name,
            control_type=control_type,
            class_name=class_name,
            timeout_ms=timeout_ms,
        )
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="ELEMENT_NOT_FOUND",
                message=res.get("message", f"Element not found with criteria (aid='{automation_id}', name='{name}')"),
                retryable=True,
                recovery_hint="Use ghosthand_element_tree to inspect the active window controls.",
            )

        elem_dict = serialize_element(res)
        return serialize_success("Element found", element=elem_dict)
    except Exception as ex:
        return serialize_exception(ex, "element_find")


def tool_element_click(element_id: str) -> Dict[str, Any]:
    """Click a UI element by ID using its UIA Invoke or Toggle pattern."""
    client = MANAGER.client
    try:
        res = client.elem_click(element_id=element_id)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="CLICK_FAILED",
                message=res.get("message", f"Could not click element '{element_id}'"),
                retryable=True,
                recovery_hint="Verify element ID using ghosthand_element_find.",
            )

        return serialize_success(f"Clicked element '{element_id}'")
    except Exception as ex:
        return serialize_exception(ex, "element_click")


def tool_element_type(element_id: str, text: str) -> Dict[str, Any]:
    """Type text into an editable element using keyboard simulation."""
    client = MANAGER.client
    tool = UiTypeTool(client)
    try:
        res = tool.execute(element_id=element_id, text=text)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="TYPE_FAILED",
                message=res.get("message", f"Could not type into element '{element_id}'"),
                retryable=True,
                recovery_hint="Verify the element is editable, or try ghosthand_element_set_value.",
            )

        return serialize_success(f"Typed text into element '{element_id}'")
    except Exception as ex:
        return serialize_exception(ex, "element_type")


def tool_element_set_value(element_id: str, value: str) -> Dict[str, Any]:
    """Set an element's text value directly via UIA ValuePattern (faster and more reliable than typing for text boxes)."""
    client = MANAGER.client
    try:
        res = client.elem_set_value(element_id=element_id, value=value)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="SET_VALUE_FAILED",
                message=res.get("message", f"Could not set value on element '{element_id}'"),
                retryable=True,
                recovery_hint="If ValuePattern is not supported, use ghosthand_element_type instead.",
            )

        return serialize_success(f"Set value on element '{element_id}'")
    except Exception as ex:
        return serialize_exception(ex, "element_set_value")


def tool_element_get_properties(element_id: str) -> Dict[str, Any]:
    """Get element properties and supported patterns by ID."""
    client = MANAGER.client
    try:
        res = client.elem_props(element_id=element_id)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="GET_PROPERTIES_FAILED",
                message=res.get("message", f"Could not get properties for element '{element_id}'"),
                retryable=True,
            )

        props = res.get("properties") or res
        return serialize_success(
            "Retrieved element properties",
            properties={
                "id": element_id,
                "name": props.get("name") or props.get("Name"),
                "control_type": props.get("controlType") or props.get("control_type"),
                "automation_id": props.get("automationId") or props.get("automation_id"),
                "is_enabled": props.get("isEnabled", True),
                "supported_patterns": props.get("supportedPatterns", []),
            },
        )
    except Exception as ex:
        return serialize_exception(ex, "element_get_properties")


# -------------------------------------------------------------------------
# Keyboard Interaction Tools
# -------------------------------------------------------------------------

def tool_keyboard_press(element_id: str, key: str) -> Dict[str, Any]:
    """Send a key press to a UI element (e.g. 'enter', 'tab', 'esc', 'backspace')."""
    client = MANAGER.client
    try:
        res = client.elem_keys(element_id=element_id, keys=key)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="KEY_PRESS_FAILED",
                message=res.get("message", f"Failed to send key '{key}'"),
                retryable=True,
            )

        return serialize_success(f"Sent key '{key}' to element '{element_id}'")
    except Exception as ex:
        return serialize_exception(ex, "keyboard_press")


def tool_keyboard_hotkey(element_id: str, hotkey: str) -> Dict[str, Any]:
    """Send a keyboard shortcut/hotkey combination (e.g. 'ctrl+s', 'alt+f4', 'ctrl+a')."""
    client = MANAGER.client
    try:
        res = client.elem_keys(element_id=element_id, keys=hotkey)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="HOTKEY_FAILED",
                message=res.get("message", f"Failed to send hotkey '{hotkey}'"),
                retryable=True,
            )

        return serialize_success(f"Sent hotkey '{hotkey}' to element '{element_id}'")
    except Exception as ex:
        return serialize_exception(ex, "keyboard_hotkey")


# -------------------------------------------------------------------------
# Session Management Tools
# -------------------------------------------------------------------------

def tool_session_attach(
    process_name: Optional[str] = None,
    pid: Optional[int] = None,
    window_title: Optional[str] = None,
    timeout_ms: int = 10000,
) -> Dict[str, Any]:
    """Attach GhostHand to an already running application window."""
    client = MANAGER.client
    # Collision prevention: if switching apps, point to the appropriate session file
    if process_name:
        proc_key = process_name.lower().replace(".exe", "")
        profile = APP_PROFILES.get(proc_key)
        target_session = os.path.abspath(profile["default_session_name"]) if profile else os.path.abspath(f"{proc_key}.session.json")
        if client.active_process and client.active_process.lower() != proc_key:
            client.session_file = target_session

    tool = SessionAttachTool(client)
    try:
        res = tool.execute(
            process_name=process_name,
            pid=pid,
            window_title=window_title,
            timeout_ms=timeout_ms,
        )
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="ATTACH_FAILED",
                message=res.get("message", "Session attach failed"),
                retryable=True,
                recovery_hint="Verify the application process is running using tasklist or ghosthand_window_list.",
            )

        return serialize_success(
            "Attached to session",
            session_file=res.get("sessionFile") or client.session_file,
            pid=res.get("pid") or client.active_pid,
            process_name=res.get("processName") or client.active_process,
        )
    except Exception as ex:
        return serialize_exception(ex, "session_attach")


def tool_session_status() -> Dict[str, Any]:
    """Check the status of the active GhostHand session."""
    client = MANAGER.client
    try:
        res = client.session_status()
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="SESSION_STATUS_FAILED",
                message=res.get("message", "Session status check failed"),
                retryable=True,
                recovery_hint="Launch an application with ghosthand_window_launch first.",
            )

        return serialize_success(
            "Session status retrieved",
            alive=res.get("processAlive", False),
            pid=res.get("pid") or client.active_pid,
            session_file=client.session_file,
            main_window=res.get("mainWindowTitle") or client.active_window,
        )
    except Exception as ex:
        return serialize_exception(ex, "session_status")


def tool_session_end() -> Dict[str, Any]:
    """End the active GhostHand automation session."""
    client = MANAGER.client
    try:
        res = client.session_end()
        MANAGER.clear_state()
        return serialize_success("Active session ended successfully")
    except Exception as ex:
        return serialize_exception(ex, "session_end")


# -------------------------------------------------------------------------
# Opt-in Tree Observation Tool (Context-Optimized)
# -------------------------------------------------------------------------

def tool_element_tree(
    depth: int = 2,
    level: str = "minimal",
    root_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Inspect the UI element tree. Opt-in only; returns a compact list of discovered elements to conserve context."""
    client = MANAGER.client
    tool = UiObserveTool(client)
    try:
        res = tool.execute(depth=depth, level=level, root_id=root_id)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="OBSERVE_FAILED",
                message=res.get("message", "UI tree observation failed"),
                retryable=True,
                recovery_hint="Ensure the application window is active and foregrounded.",
            )

        raw_elements = res.get("elements") or []
        compact_elements = [serialize_element(e) for e in raw_elements[:50]]
        return serialize_success(
            f"Observed {len(compact_elements)} elements",
            count=len(compact_elements),
            elements=compact_elements,
        )
    except Exception as ex:
        return serialize_exception(ex, "element_tree")


# -------------------------------------------------------------------------
# Screenshot Tool
# -------------------------------------------------------------------------

def tool_screenshot(
    output_path: str = "screenshot.png",
    element_id: Optional[str] = None,
    window_handle: Optional[str] = None,
) -> Dict[str, Any]:
    """Capture a screenshot of a window or element and save it to a file. Returns the file path reference."""
    client = MANAGER.client
    cmd = ["screenshot", "--output", output_path]
    if element_id:
        cmd.extend(["--id", element_id])
    if window_handle:
        cmd.extend(["--window", window_handle])

    try:
        res = client.run_raw(cmd)
        MANAGER.persist_state()

        if not res.get("success"):
            return serialize_error(
                code="SCREENSHOT_FAILED",
                message=res.get("message", "Failed to capture screenshot"),
                retryable=True,
            )

        return serialize_success(
            f"Screenshot saved to {output_path}",
            output_path=os.path.abspath(output_path),
        )
    except Exception as ex:
        return serialize_exception(ex, "screenshot")
