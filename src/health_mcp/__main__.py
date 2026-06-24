"""Command-line entry point for the health MCP server.

Examples
--------
Run for Claude Desktop (stdio, the default)::

    python -m health_mcp

Run an HTTP server for ChatGPT connectors / remote clients::

    python -m health_mcp --transport http --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    # Load the project's .env regardless of the current working directory
    # (e.g. when launched by Claude Desktop), falling back to the default search.
    _project_env = Path(__file__).resolve().parents[2] / ".env"
    if _project_env.exists():
        load_dotenv(_project_env)
    else:
        load_dotenv()
except ModuleNotFoundError:  # python-dotenv is optional
    pass

from .server import mcp


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="health-mcp",
        description="Health & medication information MCP server (openFDA + RxNorm).",
    )
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "sse"],
        default=os.getenv("MCP_TRANSPORT", "stdio"),
        help="Transport to use (default: stdio, for Claude Desktop).",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("MCP_HOST", "127.0.0.1"),
        help="Host to bind for http/sse transports.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", "8000")),
        help="Port to bind for http/sse transports.",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        mcp.run()
    else:
        mcp.run(transport=args.transport, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
