"""Health & medication information MCP server."""

# Defined before the server import below: server.py and clients.http read it.
__version__ = "0.1.0"

from .server import mcp  # noqa: E402

__all__ = ["mcp", "__version__"]
