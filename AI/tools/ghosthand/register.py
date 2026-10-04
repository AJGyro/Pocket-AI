from typing import List, Optional
from .client import GhostHandClient
from ..base import BaseTool
from .tools.session import SessionAttachTool, SessionStatusTool, SessionEndTool
from .tools.window import WindowListTool, WindowFocusTool, WindowCloseTool
from .tools.observe import UiObserveTool, UiFindTool, UiGetPropertiesTool
from .tools.action import AppLaunchTool, UiClickTool, UiTypeTool, UiSetValueTool, UiKeysTool

def get_ghosthand_tools(client: Optional[GhostHandClient] = None) -> List[BaseTool]:
    c = client or GhostHandClient()
    return [
        AppLaunchTool(c),
        SessionAttachTool(c),
        SessionStatusTool(c),
        SessionEndTool(c),
        WindowListTool(c),
        WindowFocusTool(c),
        WindowCloseTool(c),
        UiObserveTool(c),
        UiFindTool(c),
        UiGetPropertiesTool(c),
        UiClickTool(c),
        UiTypeTool(c),
        UiSetValueTool(c),
        UiKeysTool(c),
    ]
