# MCP servers code archive

This document describes the **code archive** for MCP servers: master collections, LLM development servers, self-hosted integration, build/convert tools, and the distinction between **Skills** (Claude/.md) and **MCP servers** (universal processes).

---

## 1. Master collections ("big lists")

Start here to browse thousands of community-contributed servers.

| Source | What it is | URL / repo |
|--------|------------|------------|
| **Awesome MCP Servers** (punkpeye) | Largest community list; 📂 Developer Tools section for coding servers | [punkpeye/awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) — *archived in this registry* |
| **MCP Servers Directory** (official) | Reference implementations from Anthropic/partners: Git, PostgreSQL, FileSystem, etc. | [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) — *archived*; [registry.modelcontextprotocol.io](https://modelcontextprotocol.io/registry/about) for published metadata |
| **Glama MCP Market** | Searchable registry by category (e.g. DevTools, Observability) | [glama.ai/mcp/servers](https://glama.ai/mcp/servers) — *web only* |
| **Smithery** | Registry that automates MCP installation for Claude Desktop; useful for quick testing before self-hosting | [smithery.ai](https://smithery.ai) — *web only* |

---

## 2. LLM development & engineering skills

Specialized servers for building, testing, and monitoring LLMs.

### Evaluation & testing

| Server | Purpose | Repo / package |
|--------|---------|-----------------|
| **Promptfoo MCP** | Run evaluations, red-teaming, regression tests from your agent | [promptfoo/promptfoo](https://github.com/promptfoo/promptfoo) — `npx promptfoo mcp` |
| **LangWatch MCP** | Query traces, debug past execution steps | [langwatch/langwatch](https://github.com/langwatch/langwatch) — `@langwatch/mcp-server` |
| **MCP-Bench** | Benchmark how well agents use tools (packaged as a server) | *Community tool; no single canonical repo in this archive* |
| **Arize Phoenix MCP** | Trace data, prompt versioning, dataset management from Phoenix | [Arize-ai/phoenix](https://github.com/Arize-ai/phoenix) — `@arizeai/phoenix-mcp` |

### Vector databases & RAG

| Server | Purpose | Repo |
|--------|---------|------|
| **Qdrant MCP** | Manage collections, query vector embeddings | [qdrant/mcp-server-qdrant](https://github.com/qdrant/mcp-server-qdrant) |
| **Pinecone MCP** | Pinecone index management and retrieval | *Check Awesome MCP / Glama for community servers* |
| **Weaviate MCP** | Semantic search and cluster operations | [weaviate/mcp-server-weaviate](https://github.com/weaviate/mcp-server-weaviate) |
| **LlamaCloud MCP** | Query LlamaIndex managed indexes and extract agents | [run-llama/mcp-server-llamacloud](https://github.com/run-llama/mcp-server-llamacloud), [run-llama/llamacloud-mcp](https://github.com/run-llama/llamacloud-mcp) |

### Orchestration & frameworks

| Resource | Purpose |
|----------|---------|
| **LangChain MCP Adapters** | Any LangChain/LangGraph agent can consume MCP tools | [langchain-ai/langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) |
| **Hugging Face MCP** | Search models, datasets, Spaces; run Gradio tools from Hub | [huggingface/hf-mcp-server](https://github.com/huggingface/hf-mcp-server) |

---

## 3. Self-hosted & local LLM integration

When running Ollama or LocalAI, you need bridges to use MCP tooling.

| Approach | Notes |
|----------|--------|
| **Ollama MCP bridge** | Use Stdio transport to pipe MCP tools into Ollama's tool-calling JSON mode. Community patterns; no single canonical repo in this registry. |
| **LocalAI function calling** | OpenAI-compatible function calling. Use **OpenAPI-to-MCP** to turn existing OpenAPI schemas into MCP servers. |
| **Docker MCP Toolkit** | Containers that run MCP servers in isolation; gateway for safe self-hosted agents | [docker/mcp-gateway](https://github.com/docker/mcp-gateway) — *archived* |

---

## 4. Tools to build & convert skills

| Tool | Language | Purpose |
|------|----------|---------|
| **OpenAPI → MCP** | Go | Convert Swagger/OpenAPI specs into a running MCP server | [jedisct1/openapi-mcp](https://github.com/jedisct1/openapi-mcp), [higress-group/openapi-to-mcpserver](https://github.com/higress-group/openapi-to-mcpserver) |
| **FastMCP** | Python | Decorator-based (FastAPI-style); expose Python functions as MCP tools | [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp) |
| **EasyMCP** | TypeScript | Equivalent for Node/Bun; declarative tool/resource API | [zcaceres/easy-mcp](https://github.com/zcaceres/easy-mcp) |

---

## 5. Skills vs. servers (important distinction)

| | **Skills** (Claude Code / .md) | **MCP Servers** |
|--|--------------------------------|------------------|
| **What** | Text files with instructions and optional bash/scripts (e.g. `SKILL.md` in anthropics/skills) | Actual processes (Python/Node/Go) running locally or remotely |
| **Scope** | Claude-specific (or agent-specific if the runtime reads them) | **Universal**: work with Claude, Cursor, and self-hosted agents (LangChain, LlamaIndex, etc.) |
| **Recommendation | Lightweight for one-off workflows | **Prioritize building MCP servers** for long-term, cross-platform utility. |

This archive focuses on **MCP servers and SDKs**; the separate `registry-skills.yaml` and `README-skills.md` cover Agent Skills (.md) and awesome lists for those.

---

## 6. Archiving MCP repos (this project)

Same pipeline as code-archival: latest release tarball (or default-branch HEAD), `metadata.json`, README snapshot. Output under `code-archives/` with manifest.

**From `code-archival/`:**

```bash
# Dry-run: list MCP repos that would be archived
bash archive-mcp.sh --dry-run

# Archive all MCP repos (skip existing unless --update)
bash archive-mcp.sh

# Refresh existing
bash archive-mcp.sh --update
```

- **Registry:** `code-archival/registry-mcp.yaml`
- **Wrapper:** `code-archival/archive-mcp.sh` (same options as `archive-skills.sh`: `--output`, `--dry-run`, `--update`)

---

## 7. FastMCP starter: wrap a script as an MCP tool

Minimal example: a Python function exposed as an MCP tool so a self-hosted LLM (or Cursor/Claude) can call it.

```python
# server.py — run with: uv run python server.py  (or: fastmcp run server.py)
from fastmcp import FastMCP

mcp = FastMCP("Demo", host="localhost", port=8000)  # or omit for stdio

@mcp.tool()
def run_my_script(input_path: str, option: str = "default") -> str:
    """Run the legacy script and return stdout. input_path: path to file; option: default|verbose."""
    import subprocess
    result = subprocess.run(
        ["python", "scripts/my_script.py", input_path, "--mode", option],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stdout or result.stderr or "(no output)"

if __name__ == "__main__":
    mcp.run()
```

- Install: `uv add fastmcp` (or `pip install fastmcp`).
- **Stdio** (for Cursor/Claude Desktop): use `mcp = FastMCP("Demo")` and in client config point `command` to `uv` / `python` and `args` to `server.py`.
- **HTTP**: use `host`/`port` and connect your agent to `http://localhost:8000` (Streamable HTTP or SSE if supported).

A fuller example lives in `code-archival/examples/fastmcp-starter/`.

---

## See also

- **OS skills & Windows/Linux MCP servers:** [README-mcp-os.md](README-mcp-os.md) — Linux command servers, RHEL, Windows-MCP, Clarity, Yutu, remote management, and how to use them.

---

## References

- [Model Context Protocol (modelcontextprotocol.io)](https://modelcontextprotocol.io)
- [MCP Registry (official)](https://modelcontextprotocol.io/registry/about)
- [Awesome MCP Servers (punkpeye)](https://github.com/punkpeye/awesome-mcp-servers)
- [FastMCP docs](https://fastmcp.wiki/en/getting-started/quickstart) / [PrefectHQ/fastmcp](https://github.com/PrefectHQ/fastmcp)
