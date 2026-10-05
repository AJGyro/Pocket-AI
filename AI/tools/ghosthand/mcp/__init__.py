"""
GhostHand MCP (Model Context Protocol) Package.

Exposes GhostHand Windows automation as a stdio-based MCP server for OpenCode.
"""

__version__ = "1.0.0"
__server_name__ = "ghosthand"

from .server import create_server, main

__all__ = ["__version__", "__server_name__", "create_server", "main"]
