#!/usr/bin/env python3
# =============================================================================
# FastMCP starter: expose a Python function as an MCP tool
#
# Run:  uv run server.py   (or: python server.py)
# Stdio (default): use in Cursor/Claude by adding to MCP config, e.g.:
#   "command": "uv", "args": ["run", "server.py"], "cwd": "/path/to/fastmcp-starter"
# HTTP: pass --transport http --port 8000 to run on localhost:8000
# =============================================================================
from __future__ import annotations

from fastmcp import FastMCP

mcp = FastMCP("Demo")


@mcp.tool()
def run_my_script(input_path: str, option: str = "default") -> str:
    """Run the legacy script and return stdout.

    input_path: path to input file
    option: mode — "default" or "verbose"
    """
    import subprocess

    result = subprocess.run(
        ["python", "-c", f"print('input_path={input_path!r}, option={option!r}')"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    return result.stdout or result.stderr or "(no output)"


@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers. Example tool for testing."""
    return a + b


if __name__ == "__main__":
    mcp.run()
