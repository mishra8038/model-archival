# FastMCP starter example

Minimal MCP server using [FastMCP](https://github.com/PrefectHQ/fastmcp): two tools (`add`, `run_my_script`) that a Cursor/Claude or self-hosted LLM can call.

## Setup

```bash
cd code-archival/examples/fastmcp-starter
uv init  # if not already
uv add fastmcp
```

## Run

- **Stdio** (for Cursor / Claude Desktop):

  ```bash
  uv run server.py
  ```

  In Cursor: add to `.cursor/mcp.json` (or MCP settings):

  ```json
  {
    "mcpServers": {
      "fastmcp-starter": {
        "command": "uv",
        "args": ["run", "server.py"],
        "cwd": "/absolute/path/to/code-archival/examples/fastmcp-starter"
      }
    }
  }
  ```

- **HTTP**: run with transport/port (see FastMCP docs for your version; e.g. `--transport http --port 8000` if supported) and point your client at `http://localhost:8000`.

## Tools

| Tool | Description |
|------|-------------|
| `add` | Add two integers (for quick connectivity tests). |
| `run_my_script` | Example that runs a trivial Python one-liner; replace with your real script path and args. |

Replace the body of `run_my_script` with your own script (e.g. `scripts/my_script.py`) and arguments as needed.
