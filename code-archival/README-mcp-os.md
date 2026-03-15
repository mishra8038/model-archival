# OS skills & automation: Linux and Windows MCP servers

This document lists **major collections** for OS-level skills and automation using MCP servers (and related SKILL.md sets). It covers Linux command execution, RHEL diagnostics, Windows system control, remote management, and observability. All archivable GitHub repos are in `registry-mcp.yaml` and are included when you run `archive-mcp.sh`.

---

## 1. Linux command execution servers

These give an LLM direct “hands” on the Linux terminal over MCP.

| Server | Repo | Notes |
|--------|------|--------|
| **Linux Command MCP** (xkiranj) | [xkiranj/linux-command-mcp](https://github.com/xkiranj/linux-command-mcp) | Remote command execution over MCP. Node.js client/server; `exec`, directory listing, system info, PM2. No sudo/password; diagnostic focus. *Archived.* |
| **Linux MCP Server** (LobeHub / RHEL Lightspeed) | [rhel-lightspeed/linux-mcp-server](https://github.com/rhel-lightspeed/linux-mcp-server) | RHEL-oriented; read-only diagnostics, multi-host SSH, services/processes/network/storage. Python, Apache-2.0. *Archived.* |
| **RHEL MCP Server** (Red Hat) | [RedHatInsights/insights-mcp](https://github.com/RedHatInsights/insights-mcp) | Official developer preview. Read-only: journalctl, systemctl, CPU/memory/processes; SSH keys; multi-host. RHEL 10+, also Linux/macOS/Windows 11. *Archived.* |

---

## 2. Claude Code Linux skills (SKILL.md)

These use the **SKILL.md** format for Claude Code (and can often be reused by other agents). They are archived via **registry-skills.yaml** (run `archive-skills.sh`), not `registry-mcp.yaml`.

| Collection | Repo | Notes |
|------------|------|--------|
| **Claude Skills Hub** (alirezarezvani) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | 180+ skills; Engineering/DevOps includes Linux security, server management, automated deployments. *In registry-skills.yaml.* |
| **Awesome Claude Skills** (travisvn) | [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills) | Curated list; “Superpowers” for TDD, Unix debugging, Linux-heavy workflows. *In registry-skills.yaml.* |
| **Official Anthropic Skills** | [anthropics/skills](https://github.com/anthropics/skills) | Reference repo for document processing and modular skills in Claude’s Linux dev environment. *In registry-skills.yaml.* |

---

## 3. Remote management & monitoring

| Resource | Type | Notes |
|----------|------|--------|
| **Devolutions RDM MCP Server** | MCP (experimental) | Integrates with Remote Desktop Manager for administrative actions on Linux/Windows. Works with Devolutions Agent (RDP channels). No standalone public GitHub MCP repo; see [Devolutions RDM MCP docs](https://docs.devolutions.net/rdm/commands/tools/more-tools/mcp-server/). |
| **CardinalHQ Chip MCP** | MCP + backend | Linux observability: logs, metrics, traces exposed to AI; links to commits/deployments; IDE reproduction, Grafana. Chip runs on **Lakerunner**; the open-source backend is [cardinalhq/lakerunner](https://github.com/cardinalhq/lakerunner). *Lakerunner archived.* |

---

## 4. Windows MCP servers & skills

### Core Windows OS & system administration

| Server / skill | Repo | Notes |
|----------------|------|--------|
| **Windows-MCP** (CursorTouch) | [CursorTouch/Windows-MCP](https://github.com/CursorTouch/Windows-MCP) | File navigation, app control, UI interaction, PowerShell, clipboard, keyboard. Accessibility tree (no screenshots). Windows 7–11. `uvx windows-mcp`. *Archived.* |
| **Windows System Administration** (evolv3ai) | LobeHub skills | Claude Code skills: PowerShell 7.x, registry env vars, Scoop/Winget/Chocolatey, WSL coordination. Install via LobeHub marketplace (e.g. `evolv3ai-claude-skills-archive-admin-wsl`, `windows-wsl-coordination`). |
| **Microsoft MCP Server for Enterprise** | Hosted (preview) | Entra ID + Microsoft Graph via natural language. User reporting, directory troubleshooting. [Learn: Get started](https://learn.microsoft.com/en-us/graph/mcp-server/get-started). Provision with Entra Beta PowerShell; endpoint: `https://mcp.svc.cloud.microsoft/enterprise`. |
| **Entra ID MCP** (community) | [hieuttmmo/entraid-mcp-server](https://github.com/hieuttmmo/entraid-mcp-server) | Self-hosted Entra/Graph MCP alternative. *Archived.* |
| **RDM MCP Server** (Devolutions) | See §3 | Same as above; supports Windows (and Linux) fleets. |

### Windows productivity & dev tools

| Server | Repo | Notes |
|--------|------|--------|
| **Microsoft MCP catalog** | [microsoft/mcp](https://github.com/microsoft/mcp) | Azure MCP Server (40+ services), Fabric MCP, libs, tests. C#. *Archived.* |
| **Microsoft Clarity MCP** | [microsoft/clarity-mcp-server](https://github.com/microsoft/clarity-mcp-server) | Natural language access to Clarity analytics (traffic, sessions, filters). *Archived.* |
| **YouTube Automation MCP** (Yutu) | [eat-pray-ai/yutu](https://github.com/eat-pray-ai/yutu) | Cross-platform (Windows/Mac/Linux). YouTube Data/Analytics/Reporting APIs; videos, playlists, channels, comments. Go; GCP OAuth. *Archived.* |

Office Document Skills (e.g. tfriedel) for Word/Excel/PowerPoint in terminal are often listed in awesome lists; check [Awesome MCP Servers (punkpeye)](https://github.com/punkpeye/awesome-mcp-servers) 📂 Developer Tools for current links.

### Native Windows integration

- **Windows On-Device Registry (ODR)**: discovery and secure access to MCP servers locally; standardized inventory and audit. Configure via Windows / VS Code MCP management.
- **VS Code**: manage MCP servers in Extensions view (`@mcp`), auto-start in workspace.

---

## 5. How to use these skills and servers

- **Clone (skills)**  
  `git clone <repo-url> ~/.claude/skills/skill-name` (or your agent’s skill path).

- **Configure MCP**  
  Add the server to your client config (e.g. `claude_desktop_config.json` in `~/.config/Claude/` or Cursor MCP settings) with the **absolute path** to the server entry point (e.g. `uv run server.py`, `npx -y @package/mcp-server`).

- **Self-hosted conversion**  
  Use **FastMCP** (or OpenAPI→MCP) to wrap your own Linux/Windows scripts into MCP tools consumable by any tool-calling LLM. See `code-archival/examples/fastmcp-starter/` and `README-mcp.md` §7.

---

## 6. Archiving

All MCP repos below are in **registry-mcp.yaml**. One run archives both general MCP and OS/Windows entries:

```bash
cd code-archival
bash archive-mcp.sh --dry-run   # list (includes OS/Windows)
bash archive-mcp.sh             # download
```

Skills (SKILL.md) are archived separately:

```bash
bash archive-skills.sh          # uses registry-skills.yaml
```

---

## 7. Additional recommendations

- **Awesome MCP Servers (punkpeye)**  
  Indexes 300+ servers; use the 📂 Developer Tools (and system/shell-related) sections for more OS/automation servers. Already in `registry-mcp.yaml`.

- **Claude Skill Registry (majiayu000)**  
  [majiayu000/claude-skill-registry](https://github.com/majiayu000/claude-skill-registry) — 162k+ SKILL.md files indexed; useful for discovering and archiving OS/admin skills. Consider adding to `registry-skills.yaml` if you want it in the skills archive.

- **Skill Evolution (hao-cyber)**  
  [hao-cyber/skill-evolution](https://github.com/hao-cyber/skill-evolution) — self-evolving skills that learn from execution; offline-capable, Claude Code oriented.

- **Official MCP servers (modelcontextprotocol/servers)**  
  Includes **Filesystem** and **Git**; useful for OS-adjacent workflows. Already in `registry-mcp.yaml`.

- **Docker MCP Gateway**  
  Run MCP servers in containers for isolation; one gateway for Claude/Cursor/VS Code. Already in `registry-mcp.yaml`.

---

## References

- [Red Hat: MCP server for RHEL (developer preview)](https://www.redhat.com/en/blog/smarter-troubleshooting-new-mcp-server-red-hat-enterprise-linux-now-developer-preview)
- [Microsoft MCP Server for Enterprise](https://learn.microsoft.com/en-us/graph/mcp-server/overview)
- [Windows-MCP (CursorTouch)](https://github.com/CursorTouch/Windows-MCP)
- [Cardinal Chip MCP setup](https://cardinalhq.io/blog/mcp-server-setup-guide)
- [Awesome MCP Servers](https://github.com/punkpeye/awesome-mcp-servers)
