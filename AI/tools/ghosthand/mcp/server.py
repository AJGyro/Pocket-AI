"""
GhostHand MCP Server.

Provides a Model Context Protocol (MCP) interface over stdio for OpenCode.
Exposes coordinate-free, UIA3-based Windows automation tools with compact JSON
responses optimized for small context windows.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure sys.stdout and sys.stderr are utf-8 encoded on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# Configure logging strictly to stderr to prevent corrupting stdio JSON-RPC
logging.basicConfig(
    level=logging.INFO,
    format="[GhostHand MCP %(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("ghosthand.mcp")

# Ensure repository root is on sys.path
AI_DIR = Path(__file__).resolve().parents[3]
if str(AI_DIR) not in sys.path:
    sys.path.insert(0, str(AI_DIR))

from mcp.server.mcpserver import MCPServer
from tools.ghosthand.mcp.tools import (
    tool_window_launch,
    tool_window_list,
    tool_window_focus,
    tool_window_close,
    tool_element_find,
    tool_element_click,
    tool_element_type,
    tool_element_set_value,
    tool_element_get_properties,
    tool_keyboard_press,
    tool_keyboard_hotkey,
    tool_session_attach,
    tool_session_status,
    tool_session_end,
    tool_element_tree,
    tool_screenshot,
)

SERVER_NAME = "ghosthand"
SERVER_VERSION = "1.0.0"


def create_server() -> MCPServer:
    """Create and configure the GhostHand MCPServer instance."""
    server = MCPServer(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        instructions=(
            "GhostHand Windows UI Automation MCP Server. "
            "Enables fast, coordinate-free, semantic control of Windows desktop applications. "
            "Always prefer finding elements by automation_id or name before clicking or typing."
        ),
    )

    # 1. Window Management Tools
    @server.tool(
        name="ghosthand_window_launch",
        description="Launch a Windows application (e.g. notepad.exe, calc.exe) and establish an active automation session.",
    )
    def window_launch(
        app_path: str,
        args: Optional[str] = None,
        timeout_ms: int = 15000,
    ) -> Dict[str, Any]:
        logger.info(f"Launching application: {app_path}")
        return tool_window_launch(app_path=app_path, args=args, timeout_ms=timeout_ms)

    @server.tool(
        name="ghosthand_window_list",
        description="List all top-level windows for the active application session.",
    )
    def window_list() -> Dict[str, Any]:
        logger.info("Listing top-level windows")
        return tool_window_list()

    @server.tool(
        name="ghosthand_window_focus",
        description="Bring a window to the foreground by its hex handle.",
    )
    def window_focus(window_handle: str) -> Dict[str, Any]:
        logger.info(f"Focusing window handle: {window_handle}")
        return tool_window_focus(window_handle=window_handle)

    @server.tool(
        name="ghosthand_window_close",
        description="Close a window by its hex handle.",
    )
    def window_close(window_handle: str) -> Dict[str, Any]:
        logger.info(f"Closing window handle: {window_handle}")
        return tool_window_close(window_handle=window_handle)

    # 2. UI Element Inspection & Interaction Tools
    @server.tool(
        name="ghosthand_element_find",
        description="Find a specific UI element using semantic properties (automation_id, name, control_type). Returns element ID.",
    )
    def element_find(
        automation_id: Optional[str] = None,
        name: Optional[str] = None,
        control_type: Optional[str] = None,
        class_name: Optional[str] = None,
        timeout_ms: int = 10000,
    ) -> Dict[str, Any]:
        logger.info(f"Finding element: aid={automation_id}, name={name}, type={control_type}")
        return tool_element_find(
            automation_id=automation_id,
            name=name,
            control_type=control_type,
            class_name=class_name,
            timeout_ms=timeout_ms,
        )

    @server.tool(
        name="ghosthand_element_click",
        description="Click a UI element by ID using its UIA Invoke or Toggle pattern.",
    )
    def element_click(element_id: str) -> Dict[str, Any]:
        logger.info(f"Clicking element: {element_id}")
        return tool_element_click(element_id=element_id)

    @server.tool(
        name="ghosthand_element_type",
        description="Type text into an editable element using keyboard simulation.",
    )
    def element_type(element_id: str, text: str) -> Dict[str, Any]:
        logger.info(f"Typing into element {element_id}: length {len(text)}")
        return tool_element_type(element_id=element_id, text=text)

    @server.tool(
        name="ghosthand_element_set_value",
        description="Set an element text value directly via UIA ValuePattern (faster & more reliable than typing for text boxes).",
    )
    def element_set_value(element_id: str, value: str) -> Dict[str, Any]:
        logger.info(f"Setting value on element {element_id}: length {len(value)}")
        return tool_element_set_value(element_id=element_id, value=value)

    @server.tool(
        name="ghosthand_element_get_properties",
        description="Get element properties and supported UIA patterns by ID.",
    )
    def element_get_properties(element_id: str) -> Dict[str, Any]:
        logger.info(f"Getting properties for element: {element_id}")
        return tool_element_get_properties(element_id=element_id)

    # 3. Keyboard Shortcut & Key Tools
    @server.tool(
        name="ghosthand_keyboard_press",
        description="Send a special key press to an element (e.g. 'enter', 'tab', 'esc', 'backspace').",
    )
    def keyboard_press(element_id: str, key: str) -> Dict[str, Any]:
        logger.info(f"Pressing key '{key}' on element: {element_id}")
        return tool_keyboard_press(element_id=element_id, key=key)

    @server.tool(
        name="ghosthand_keyboard_hotkey",
        description="Send a keyboard shortcut/hotkey combination (e.g. 'ctrl+s', 'alt+f4', 'ctrl+a').",
    )
    def keyboard_hotkey(element_id: str, hotkey: str) -> Dict[str, Any]:
        logger.info(f"Sending hotkey '{hotkey}' to element: {element_id}")
        return tool_keyboard_hotkey(element_id=element_id, hotkey=hotkey)

    # 4. Session Management Tools
    @server.tool(
        name="ghosthand_session_attach",
        description="Attach GhostHand to an already running application window by process name, PID, or window title.",
    )
    def session_attach(
        process_name: Optional[str] = None,
        pid: Optional[int] = None,
        window_title: Optional[str] = None,
        timeout_ms: int = 10000,
    ) -> Dict[str, Any]:
        logger.info(f"Attaching session: proc={process_name}, pid={pid}, title={window_title}")
        return tool_session_attach(
            process_name=process_name,
            pid=pid,
            window_title=window_title,
            timeout_ms=timeout_ms,
        )

    @server.tool(
        name="ghosthand_session_status",
        description="Check the status and process health of the active GhostHand automation session.",
    )
    def session_status() -> Dict[str, Any]:
        logger.info("Checking session status")
        return tool_session_status()

    @server.tool(
        name="ghosthand_session_end",
        description="End the active GhostHand automation session and clean up session state.",
    )
    def session_end() -> Dict[str, Any]:
        logger.info("Ending session")
        return tool_session_end()

    # 5. Tree Observation Tool (Opt-in only, compact list capped at 50)
    @server.tool(
        name="ghosthand_element_tree",
        description="Inspect the UI element tree. Opt-in only; returns a compact list of discovered elements to conserve context.",
    )
    def element_tree(
        depth: int = 2,
        level: str = "minimal",
        root_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(f"Inspecting element tree: depth={depth}, level={level}")
        return tool_element_tree(depth=depth, level=level, root_id=root_id)

    # 6. Screenshot Tool (Context-Optimized: saves to disk and returns path)
    @server.tool(
        name="ghosthand_screenshot",
        description="Capture a screenshot of a window or element and save it to a file. Returns the file path reference.",
    )
    def screenshot(
        output_path: str = "screenshot.png",
        element_id: Optional[str] = None,
        window_handle: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(f"Capturing screenshot to: {output_path}")
        return tool_screenshot(
            output_path=output_path,
            element_id=element_id,
            window_handle=window_handle,
        )

    return server


def main() -> None:
    """Run the GhostHand MCP Server over stdio transport."""
    server = create_server()
    logger.info(f"Starting {SERVER_NAME} MCP Server v{SERVER_VERSION} on stdio...")
    try:
        server.run(transport="stdio")
    except (KeyboardInterrupt, SystemExit):
        logger.info("Server terminated gracefully.")
    except Exception as ex:
        logger.error(f"Server encountered error: {ex}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
