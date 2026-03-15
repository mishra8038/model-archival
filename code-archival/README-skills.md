# Archiving Agent / LLM Skills

This document describes how to archive a snapshot of the Agent Skills ecosystem: the [Agent Skills spec](https://agentskills.io/home), [Anthropic’s official skills](https://github.com/anthropics/skills), the [Awesome LLM Skills](https://github.com/Prat011/awesome-llm-skills) list, and all external GitHub repos it references.

## What gets archived

| Source | Content |
|--------|--------|
| **agentskills/agentskills** | Open spec, validation (skills-ref), reference library |
| **anthropics/skills** | Official document skills (docx, pdf, pptx, xlsx), example skills, templates |
| **Prat011/awesome-llm-skills** | Curated list + in-repo skills (notion-*, webapp-testing, etc.) |
| **20 external repos** | All unique GitHub roots linked from awesome-llm-skills (see `registry-skills.yaml`) |
| **agentskills.io** | Docs site snapshot (optional; see below) |

The list is built from the awesome-llm-skills README: every `https://github.com/owner/repo` (and subpaths) is reduced to unique `owner/repo` roots so each repo is archived once.

## 1. Download GitHub repos (tarballs)

Uses the same pipeline as code-archival: latest release tarball per repo (or HEAD of default branch if no release), plus `metadata.json` and README snapshot. Output goes to the same `code-archives/` tree so you can share D5 with the main code-archival run.

**From the `code-archival/` directory:**

```bash
# Dry-run: list repos that would be archived
bash archive.sh --registry registry-skills.yaml --dry-run

# Archive all skills repos (skip existing unless --update)
bash archive.sh --registry registry-skills.yaml

# Optional: restrict output directory
bash archive.sh --registry registry-skills.yaml --output /mnt/models/d5

# Re-download / refresh all
bash archive.sh --registry registry-skills.yaml --update
```

Output layout (same as main code-archival):

- `$OUTPUT_ROOT/code-archives/<owner>__<repo>/release/<tarball>.tar.gz`
- `$OUTPUT_ROOT/code-archives/<owner>__<repo>/metadata.json`
- `$OUTPUT_ROOT/code-archives/<owner>__<repo>/README.md`
- `manifest.json` and `MANIFEST.md` in `code-archives/` (reflect only repos from the registry you used)

A `GITHUB_TOKEN` in the environment or in `code-archival/.secrets` is recommended to avoid rate limits (60 req/hr unauthenticated).

## 2. Snapshot agentskills.io (optional)

The spec and docs live at [agentskills.io](https://agentskills.io/home); the site points to the [agentskills/agentskills](https://github.com/agentskills/agentskills) repo for the spec and validation. To keep a static copy of the docs:

```bash
# Create a directory for the site snapshot (e.g. on D5)
SKILLS_SITE_ROOT="/mnt/models/d5/skills-archives/agentskills.io"
mkdir -p "$SKILLS_SITE_ROOT"
cd "$SKILLS_SITE_ROOT"

# Mirror the site (respects robots.txt unless -e robots=off)
wget --mirror --convert-links --no-parent --no-host-directories \
  --adjust-extension --span-hosts --trust-server-names \
  --wait=1 --random-wait --limit-rate=500k \
  https://agentskills.io/
```

For a minimal snapshot (docs only), you can restrict to the paths listed in [llms.txt](https://agentskills.io/llms.txt) and fetch those URLs explicitly, or run the mirror once and prune non-doc paths.

After mirroring, open `agentskills.io/index.html` (or the equivalent) locally to browse.

## 3. Registry format and maintenance

- **Registry:** `code-archival/registry-skills.yaml`
- **Schema:** Same as `registry.yaml`: `id`, `github`, `category`, `risk`, `licence`, `notes`. All entries use `category: agent-skills`.
- **Adding repos:** Append a new `- id: ...` block with `github: owner/repo`. Re-run `archive.sh --registry registry-skills.yaml`.
- **Merging into main registry:** You can merge `registry-skills.yaml` into `registry.yaml` and use `--category agent-skills` when you want to run only skills repos.

## 4. Wrapper script

From `code-archival/`:

```bash
bash archive-skills.sh                  # archive all skills repos (same as --registry registry-skills.yaml)
bash archive-skills.sh --dry-run        # list only
bash archive-skills.sh --update         # refresh existing tarballs
bash archive-skills.sh --site           # also mirror agentskills.io (wget)
bash archive-skills.sh --output /path   # override output root (default /mnt/models/d5)
```

Overrides: `OUTPUT_ROOT`, `SKILLS_SITE_ROOT` (for `--site`).

## 5. Cheat sheet

| Goal | Command |
|------|--------|
| List skills repos (no download) | `bash archive-skills.sh --dry-run` |
| Archive all skills repos | `bash archive-skills.sh` |
| Refresh existing | `bash archive-skills.sh --update` |
| Also snapshot agentskills.io | `bash archive-skills.sh --site` |
| Snapshot site only (manual) | `wget --mirror ...` (see §2) |

## 6. Utilizing skills with self-hosted LLMs

Agent Skills are **structured prompts plus optional scripts/assets**: a `SKILL.md` file (YAML frontmatter `name` + `description`, then Markdown instructions) and optionally `scripts/`, `references/`, `assets/`. They are not tied to a specific API; any self-hosted stack that can load context and run tools can use them.

**Ways to use the archived skills with your own models:**

1. **As system/context injection**
   - **Index:** Parse each archived repo (or extracted tarball), find every `SKILL.md`, read frontmatter. Build a small index: `name`, `description`, path to full `SKILL.md`.
   - **Retrieve:** On each user request, match the query to skill descriptions (keyword overlap, embedding similarity, or a small classifier). Pick one or a few skills.
   - **Inject:** Put the chosen skill’s full `SKILL.md` (and any referenced files) into the system prompt or an early user message. Your model then follows the instructions in the skill (e.g. “use this workflow for PDF extraction”, “run this script when X”).
   - Works with **any backend** (vLLM, Ollama, llama.cpp, etc.) as long as you have an app that builds the prompt and calls your inference API.

2. **With an agent framework**
   - Use an open-source **agent runtime** that supports “skills” or “plugins” (e.g. OpenHands, OpenCode, Mux, Goose, Cursor-style agents). Many of these already consume the Agent Skills format (see [agentskills.io](https://agentskills.io) adoption list).
   - Point the framework’s skill directory at your **extracted** archive (e.g. `code-archives/anthropics__skills/` unpacked, or a copy of selected `*/SKILL.md` trees). The framework handles “when to load which skill” and “when to run scripts”.
   - Self-hosted in this case means: your model runs locally (or in your cloud), and the agent runs on your machine; skills are local files from the archive.

3. **Scripts as tools**
   - Many skills ship executable scripts in `scripts/`. Your stack can expose these as **tools**: when the model decides to “use skill X”, your middleware runs the corresponding script (e.g. Python/Bash) and returns stdout to the model. Same pattern as MCP or function-calling: the skill describes when and how to call the script; your orchestrator executes it.

4. **Minimal “skill loader” for a single model**
   - Keep a flat list of `(name, description, path_to_skill_md)`. At startup (or on demand), load all descriptions into a short system prompt: “You have these capabilities: …”. When the user asks for something that fits a skill, append that skill’s full content to the next request. No need for a full agent framework if you only need “inject the right instructions.”

**Summary:** The archive gives you offline, versioned copies of the skill definitions. Utilization = **index by name/description → select by task → inject SKILL.md (+ refs) into context → optionally run scripts as tools**. That works with any self-hosted LLM API plus a thin orchestration layer (custom app or an open-source agent that supports skills).

## References

- [Agent Skills (agentskills.io)](https://agentskills.io/home)
- [agentskills.io docs index (llms.txt)](https://agentskills.io/llms.txt)
- [Anthropic Skills (anthropics/skills)](https://github.com/anthropics/skills)
- [Awesome LLM Skills (Prat011/awesome-llm-skills)](https://github.com/Prat011/awesome-llm-skills)
