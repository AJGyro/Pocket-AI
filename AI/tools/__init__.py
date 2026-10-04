from typing import Optional
from .base import BaseTool, ToolRegistry
from .ghosthand.register import get_ghosthand_tools
from .ghosthand.client import GhostHandClient

def register_all_tools(
    registry: Optional[ToolRegistry] = None,
    ghosthand_client: Optional[GhostHandClient] = None,
) -> ToolRegistry:
    reg = registry or ToolRegistry()
    for tool in get_ghosthand_tools(client=ghosthand_client):
        reg.register(tool)
    return reg

__all__ = ["BaseTool", "ToolRegistry", "register_all_tools", "get_ghosthand_tools"]
