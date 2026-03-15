# Chat archive

Archived index of Cursor agent conversations for the model-archival project. Raw transcripts live under the Cursor project data directory and are referenced here by ID for traceability and future context.

---

## Where transcripts live

- **Location:** `~/.cursor/projects/home-x-dev-model-archival/agent-transcripts/`
- **Format:** One directory per chat, named by UUID, containing `<uuid>.jsonl` (JSONL with `role` / `message` / `content`).
- **This document:** Human-readable index with date, short title, and transcript ID. Update by re-running the script below or by appending new sessions manually.

---

## Index of chats (newest first)

| Date       | Title (first user query) | Transcript ID |
|-----------|---------------------------|----------------|
| 2026-03-14 | Grok Code 1 — should we download? | `b6b6c37c-3338-40cb-b527-c59ba279871b` |
| 2026-03-14 | gdrive-archival: add D2/D3 models &lt; 200 GB to upload list | `04e4513e-bdb2-4da0-87ad-f67b380cf679` |
| 2026-03-14 | report | `6a458484-30ea-4f06-8aec-50b9c1c00c1d` |
| 2026-03-14 | report on current model download status | `d6dee546-69bd-4503-8dbc-bb530b060449` |
| 2026-03-14 | Have we archived the code for Heretic? | `4ac6c9e1-5bbe-44a5-b9a8-a2594609095e` |
| 2026-03-14 | Leaderboards: analyze LLM/LRM leaderboards, fingerprints, archival list | `c4cf7efb-9077-4c69-9906-6a877f44d574` |
| 2026-03-13 | Upload smaller models and GGUF to Google Drive | `b6d047b2-dccf-481b-94ea-764dfc0854c5` |
| 2026-03-13 | Redundancy checks for filesystem / disks | `9829b747-3dca-4911-ac9d-4862a8e88950` |
| 2026-03-13 | Restart archiver after models added by another agent | `5d070824-a96e-41db-9fe8-727ee77e2052` |
| 2026-03-13 | Model selection criteria (Gemini/ChatGPT/Claude list) | `aba7d6be-2c7a-4169-b148-81fd07d28189` |
| 2026-03-13 | Gemini advice on model archival list | `204b4b72-a841-4c1c-bef0-a550920c2e56` |
| 2026-03-13 | Grok open source models, leaderboard | `aff27d3e-1fbd-4836-9572-e5581cc2348c` |
| 2026-03-13 | report | `e50f0c36-4aaf-4227-b23c-427d5452c966` |
| 2026-03-12 | VPN and download check after reconnect | `9d3c2d14-9a70-4b54-a049-a6925306aaa9` |
| 2026-03-12 | Summarize projects, build docs folder | `8c4c2433-2dad-4ce8-8897-cc51156fe47e` |
| 2026-03-12 | report | `cafdd430-5696-4171-a963-f29a27f02d02` |
| 2026-03-12 | Cursor interaction / tone feedback | `ad246b6a-34d4-4c09-b2b1-b5d39674a228` |
| 2026-03-12 | code-archival: verify project list | `a08bec98-e8e0-4ed3-8be8-838fb3f530eb` |
| 2026-03-12 | Research-grade models on leaderboard | `825e55a7-07f2-4331-bd0e-a90cbfb6f2cd` |
| 2026-03-12 | report | `613ccf79-ff8a-4f76-aede-a938a6425790` |
| 2026-03-11 | Surfshark VPN check (throttling) | `4b755707-be85-4455-bbd5-04031dbf67ce` |
| 2026-03-11 | Cursor tone: oversmart, intent, edge cases | `750062f6-e825-4799-8504-36e49deb92a3` |
| 2026-03-10 | Qwen / Alibaba staff leaving — archive Qwen models | `f3119332-d4fd-4a9c-a7f5-4114f66ce696` |
| 2026-03-09 | Inspect project docs, set context | `866e201d-d3e3-4685-be1b-3dda83b1bb75` |

Raw transcripts: `~/.cursor/projects/home-x-dev-model-archival/agent-transcripts/<id>/<id>.jsonl`

---

## This session (chat archive request)

**Request:** Archive all chats in the chat document.

**Done:**

1. **Chat archive doc**
   - Added `docs/CHAT-ARCHIVE.md` (this file).
   - Index of all agent transcripts: date, short title from first user message, transcript ID.
   - Note on where raw transcripts live (`~/.cursor/.../agent-transcripts/`).

2. **Earlier in this conversation**
   - **Leaderboards:** Analyzed major LLM/LRM leaderboards (HF Open LLM Leaderboard v2, LMSYS Chatbot Arena); compared open models and our `local/config/registry.yaml`; confirmed coverage and suggested watching for new family releases.
   - **Fingerprints:** Ensured leaderboard collection and fingerprinting are in place:
     - HF: `fingerprints/scripts/snapshot_leaderboard.py` — snapshots `open-llm-leaderboard/contents` + HF metadata into `fingerprints/leaderboard-snapshots/YYYY-MM-DD/`.
     - LMSYS: `fingerprints/scripts/snapshot_lmsys_arena.py` — snapshots Arena from a JSON URL or file into `fingerprints/leaderboard-snapshots/lmsys/YYYY-MM-DD/`.
     - Registry: `fingerprints/scripts/build_registry.py` — builds `fingerprints/config/registry.yaml` from leaderboard + HF data (2,725+ models + 44 curated).
   - **Collection:** Triggered HF leaderboard snapshot (run from `fingerprints/` with `uv run python scripts/snapshot_leaderboard.py --output-dir .`).
   - **Fingerprinting:** Ran `uv run python scripts/build_registry.py` in `fingerprints/` to refresh the registry with leaderboard and popularity data.

To refresh the index of chats from transcripts (e.g. after new sessions), run from repo root:

```bash
export TRANSCRIPTS_DIR=~/.cursor/projects/home-x-dev-model-archival/agent-transcripts
python3 -c '
import os, json, re
from pathlib import Path
from datetime import datetime
base = Path(os.environ.get("TRANSCRIPTS_DIR", os.path.expanduser("~/.cursor/projects/home-x-dev-model-archival/agent-transcripts"))).expanduser()
for d in sorted(base.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
    if not d.is_dir(): continue
    id = d.name
    f = d / (id + '.jsonl')
    if not f.exists(): continue
    with open(f) as fp:
        for line in fp:
            try:
                o = json.loads(line)
                if o.get('role') == 'user':
                    text = o.get('message', {}).get('content', [{}])[0].get('text', '')
                    m = re.search(r'<user_query>\s*\n?(.*?)(?:\n</user_query>|$)', text, re.DOTALL)
                    title = (m.group(1).strip() if m else text[:80]).replace('\n', ' ').strip()[:70]
                    print(datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d'), id, title, sep='\t')
                    break
            except: pass
'
```

Then merge the output into the table above (or automate that step in a script under `scripts/` if desired).
