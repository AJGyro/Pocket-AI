from typing import Any, Dict, Optional
from ..client import GhostHandClient
from ...base import BaseTool

class WindowListTool(BaseTool):
    name = "window_list"
    description = "List all top-level windows for the application in the active session."
    parameters = {
        "type": "object",
        "properties": {},
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(self, **kwargs) -> Dict[str, Any]:
        return self.client.window_list()

class WindowFocusTool(BaseTool):
    name = "window_focus"
    description = "Bring a window to the foreground by its hex handle."
    parameters = {
        "type": "object",
        "properties": {
            "window_handle": {
                "type": "string",
                "description": "Hex window handle (e.g. '0x1A2B') from window_list.",
            },
        },
        "required": ["window_handle"],
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(self, window_handle: str, **kwargs) -> Dict[str, Any]:
        return self.client.window_focus(window_handle=window_handle)

class WindowCloseTool(BaseTool):
    name = "window_close"
    description = "Close a window by its hex handle."
    parameters = {
        "type": "object",
        "properties": {
            "window_handle": {
                "type": "string",
                "description": "Hex window handle (e.g. '0x1A2B') to close.",
            },
        },
        "required": ["window_handle"],
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(self, window_handle: str, **kwargs) -> Dict[str, Any]:
        return self.client.window_close(window_handle=window_handle)
