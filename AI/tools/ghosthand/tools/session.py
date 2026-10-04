from typing import Any, Dict, Optional
from ..client import GhostHandClient
from ...base import BaseTool

class SessionAttachTool(BaseTool):
    name = "session_attach"
    description = "Attach to a running Windows application by process name, PID, or window title to begin an automation session."
    parameters = {
        "type": "object",
        "properties": {
            "process_name": {
                "type": "string",
                "description": "Process name without .exe (e.g. 'notepad'). Attaches to first match.",
            },
            "pid": {
                "type": "integer",
                "description": "Process ID to attach to.",
            },
            "window_title": {
                "type": "string",
                "description": "Window title text to match (e.g. 'Untitled - Notepad').",
            },
            "timeout_ms": {
                "type": "integer",
                "description": "Maximum time in ms to wait for the window (default 10000).",
                "default": 10000,
            },
        },
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(
        self,
        process_name: Optional[str] = None,
        pid: Optional[int] = None,
        window_title: Optional[str] = None,
        timeout_ms: int = 10000,
        **kwargs,
    ) -> Dict[str, Any]:
        return self.client.session_attach(
            pid=pid,
            process_name=process_name,
            window_title=window_title,
            timeout_ms=timeout_ms,
        )

class SessionStatusTool(BaseTool):
    name = "session_status"
    description = "Check status of the active GhostHand session (process alive, window valid, cache size)."
    parameters = {
        "type": "object",
        "properties": {},
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(self, **kwargs) -> Dict[str, Any]:
        return self.client.session_status()

class SessionEndTool(BaseTool):
    name = "session_end"
    description = "End the active GhostHand session and clean up cached handles."
    parameters = {
        "type": "object",
        "properties": {},
    }

    def __init__(self, client: Optional[GhostHandClient] = None):
        self.client = client or GhostHandClient()

    def execute(self, **kwargs) -> Dict[str, Any]:
        return self.client.session_end()
