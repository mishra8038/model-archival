#!/usr/bin/env bash
# =============================================================================
# archive.sh — Archive latest release of open-source AI projects to disk
#
# Idempotent: safe to run multiple times. Already-archived repos are skipped
# unless --update is passed. Partial downloads are cleaned up on failure.
# metadata.json and index.json are written atomically (tmp → rename).
#
# For each repo in registry.yaml:
#   1. Download latest tagged release tarball from GitHub  → <repo>/release/
#   2. Write metadata.json atomically                      → <repo>/metadata.json
#   3. Snapshot the README                                 → <repo>/README.md
#   4. Rebuild index.json atomically at end of run
#
# If a repo has NO formal release, falls back to a HEAD tarball.
#
# Usage:
#   bash archive.sh                             # archive all (skip existing)
#   bash archive.sh --output /mnt/models/d5     # explicit output dir
#   bash archive.sh --dry-run                   # list what would run, no writes
#   bash archive.sh --update                    # re-download all (refresh)
#   bash archive.sh --repo ggml-org/llama.cpp   # single repo only
#   bash archive.sh --category inference        # one category only
#   bash archive.sh --risk critical             # one risk level only
#
# Output layout:
#   <output>/code-archives/
#     ggml-org__llama.cpp/
#       release/           ← release tarball(s)
#       metadata.json      ← stars, licence, release tag, sha, archive date, risk
#       README.md          ← README snapshot from tarball
#     index.json           ← rebuilt atomically at end of every run
#     archive.log          ← append-only timestamped log
# =============================================================================
set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REGISTRY="$SCRIPT_DIR/registry.yaml"
OUTPUT_ROOT="/mnt/models/d5"

# Auto-load GITHUB_TOKEN from .secrets if not already in environment
if [[ -z "${GITHUB_TOKEN:-}" && -f "$SCRIPT_DIR/.secrets" ]]; then
    GITHUB_TOKEN="$(grep -E '^GITHUB_TOKEN=' "$SCRIPT_DIR/.secrets" \
        | head -1 | cut -d= -f2- | tr -d '[:space:]')"
    export GITHUB_TOKEN
fi
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

DRY_RUN=false
UPDATE=false
SINGLE_REPO=""
FILTER_CATEGORY=""
FILTER_RISK=""

# ── Arg parsing ───────────────────────────────────────────────────────────────
i=1
while [[ $i -le $# ]]; do
    arg="${!i}"
    case "$arg" in
        --dry-run)    DRY_RUN=true ;;
        --update)     UPDATE=true ;;
        --output)     i=$((i+1)); OUTPUT_ROOT="${!i}" ;;
        --output=*)   OUTPUT_ROOT="${arg#--output=}" ;;
        --repo)       i=$((i+1)); SINGLE_REPO="${!i}" ;;
        --repo=*)     SINGLE_REPO="${arg#--repo=}" ;;
        --category)   i=$((i+1)); FILTER_CATEGORY="${!i}" ;;
        --category=*) FILTER_CATEGORY="${arg#--category=}" ;;
        --risk)       i=$((i+1)); FILTER_RISK="${!i}" ;;
        --risk=*)     FILTER_RISK="${arg#--risk=}" ;;
        --help|-h)
            sed -n '/^# Usage:/,/^# ===/{s/^# \{0,1\}//p}' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
    i=$((i+1))
done

ARCHIVE_DIR="$OUTPUT_ROOT/code-archives"
LOG_FILE="$ARCHIVE_DIR/archive.log"
INDEX_FILE="$ARCHIVE_DIR/index.json"

# ── Dependency check ──────────────────────────────────────────────────────────
for cmd in curl python3 tar; do
    command -v "$cmd" &>/dev/null || { echo "ERROR: '$cmd' not found." >&2; exit 1; }
done
python3 -c "import yaml" &>/dev/null \
    || { echo "ERROR: python3 pyyaml missing. Run: pip install pyyaml" >&2; exit 1; }

# ── Setup ─────────────────────────────────────────────────────────────────────
mkdir -p "$ARCHIVE_DIR"
log()  { echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*" | tee -a "$LOG_FILE"; }
ok()   { echo "  ✓ $*"; }
info() { echo "  · $*"; }
warn() { echo "  ⚠ $*"; }
fail() { echo "  ✗ $*"; }

# ── GitHub helpers ────────────────────────────────────────────────────────────
# Warn early if no token — unauthenticated GitHub API allows only 60 req/hr.
# With a token it's 5000/hr. Generate one at https://github.com/settings/tokens
# (no scopes needed for public repos) then:  export GITHUB_TOKEN=ghp_...
if [[ -z "$GITHUB_TOKEN" ]]; then
    warn "GITHUB_TOKEN not set — unauthenticated API (60 req/hr limit)."
    warn "  Set it with: export GITHUB_TOKEN=ghp_YOUR_TOKEN"
    warn "  Or add to ~/.bashrc: export GITHUB_TOKEN=ghp_YOUR_TOKEN"
fi

gh_api() {
    # Retry up to 4 times; on 403/429 (rate limit) sleep and retry
    local url="$1"
    local attempt body http_code
    for attempt in 1 2 3 4; do
        body="$(curl -sS --retry 0 \
            -H "Accept: application/vnd.github+json" \
            -H "X-GitHub-Api-Version: 2022-11-28" \
            ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
            -w "\n__HTTP_CODE__:%{http_code}" \
            "$url" 2>/dev/null || true)"
        http_code="$(echo "$body" | grep -o '__HTTP_CODE__:[0-9]*' | cut -d: -f2 || echo "0")"
        body="$(echo "$body" | grep -v '__HTTP_CODE__')"
        if [[ "$http_code" == "200" ]]; then
            echo "$body"
            return 0
        elif [[ "$http_code" == "403" || "$http_code" == "429" ]]; then
            local wait=$(( 60 * attempt ))
            warn "GitHub rate-limited (HTTP $http_code) — sleeping ${wait}s (attempt $attempt/4) …"
            sleep "$wait"
        elif [[ "$http_code" == "404" ]]; then
            echo "{}"   # repo not found — let caller handle
            return 0
        else
            sleep $(( 5 * attempt ))
        fi
    done
    echo "{}"
    return 1
}

gh_download() {
    # $1=url  $2=dest (writes to a .part file first, then renames on success)
    local url="$1" dest="$2"
    local part="${dest}.part"
    if curl -fsSL --retry 3 --retry-delay 5 \
            ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
            -L -o "$part" "$url" 2>/dev/null; then
        mv "$part" "$dest"
        return 0
    else
        rm -f "$part"
        return 1
    fi
}

# Atomic JSON write: write to .tmp then rename
atomic_json() {
    # $1=dest_path  $2=json_string
    local dest="$1" content="$2"
    local tmp="${dest}.tmp"
    printf '%s' "$content" > "$tmp"
    mv "$tmp" "$dest"
}

# ── Parse registry (deduplicated by github path) ──────────────────────────────
mapfile -t REPOS < <(python3 - <<PYEOF
import yaml, sys
data = yaml.safe_load(open('$REGISTRY'))
seen = set()
for r in data.get('repos', []):
    gh  = r.get('github', '').strip()
    cat = r.get('category', 'unknown')
    rsk = r.get('risk', 'medium')
    lic = r.get('licence', 'unknown')
    if not gh or gh in seen:
        continue
    seen.add(gh)
    # Filter by category / risk if requested
    if '$FILTER_CATEGORY' and cat != '$FILTER_CATEGORY':
        continue
    if '$FILTER_RISK' and rsk != '$FILTER_RISK':
        continue
    print(f"{gh}|{cat}|{rsk}|{lic}")
PYEOF
)

TOTAL=${#REPOS[@]}
N_DONE=0; N_SKIP=0; N_FAIL=0

log "=================================================="
log "code-archival run started"
log "Output    : $ARCHIVE_DIR"
log "Repos     : $TOTAL"
log "Dry-run   : $DRY_RUN"
log "Update    : $UPDATE"
log "Filter cat: ${FILTER_CATEGORY:-(all)}"
log "Filter rsk: ${FILTER_RISK:-(all)}"
log "=================================================="

# ── Per-repo archive function ─────────────────────────────────────────────────
archive_repo() {
    local github_repo="$1" category="$2" risk="$3" licence="$4"
    local safe_name="${github_repo//\//__}"
    local repo_dir="$ARCHIVE_DIR/$safe_name"
    local archived_at; archived_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

    # ── dry-run ───────────────────────────────────────────────────────────────
    if $DRY_RUN; then
        info "DRY-RUN → $repo_dir"
        return 0
    fi

    # ── skip if already done and not updating ─────────────────────────────────
    if [[ -f "$repo_dir/metadata.json" ]] && ! $UPDATE; then
        local existing_tag
        existing_tag="$(python3 -c \
            "import json; print(json.load(open('$repo_dir/metadata.json')).get('release_tag','?'))" \
            2>/dev/null || echo "?")"
        info "Already archived ($existing_tag) — skipping (use --update to refresh)"
        ((N_SKIP++)) || true
        return 0
    fi

    mkdir -p "$repo_dir/release"

    # ── 1. GitHub repo metadata ───────────────────────────────────────────────
    local repo_json; repo_json="$(gh_api "https://api.github.com/repos/$github_repo")"
    local has_id; has_id="$(python3 -c \
        "import json,sys; d=json.loads(sys.stdin.read()); print('yes' if 'id' in d else 'no')" \
        <<< "$repo_json" 2>/dev/null || echo "no")"
    if [[ "$has_id" != "yes" ]]; then
        fail "GitHub API returned no data for $github_repo — skipping"
        ((N_FAIL++)) || true
        return 0
    fi

    local repo_tmp; repo_tmp="$(mktemp /tmp/gh_repo_XXXXXX.json)"
    echo "$repo_json" > "$repo_tmp"

    local description stars default_branch last_push gh_licence
    description="$(python3 -c \
        "import json; d=json.load(open('$repo_tmp')); s=d.get('description') or ''; print(s.replace('\"','').replace(chr(39),'')[:200])" \
        2>/dev/null || echo "")"
    stars="$(python3 -c \
        "import json; d=json.load(open('$repo_tmp')); print(d.get('stargazers_count',0))" \
        2>/dev/null || echo "0")"
    default_branch="$(python3 -c \
        "import json; d=json.load(open('$repo_tmp')); print(d.get('default_branch','main'))" \
        2>/dev/null || echo "main")"
    last_push="$(python3 -c \
        "import json; d=json.load(open('$repo_tmp')); print(d.get('pushed_at',''))" \
        2>/dev/null || echo "")"
    gh_licence="$(python3 -c \
        "import json; d=json.load(open('$repo_tmp')); l=d.get('license'); print(l['spdx_id'] if l else '')" \
        2>/dev/null || echo "")"
    rm -f "$repo_tmp"

    # ── 2. Latest release ─────────────────────────────────────────────────────
    local release_json; release_json="$(gh_api "https://api.github.com/repos/$github_repo/releases/latest")"
    local rel_tmp; rel_tmp="$(mktemp /tmp/gh_rel_XXXXXX.json)"
    echo "$release_json" > "$rel_tmp"

    local release_tag release_name release_date tarball_url fallback=false
    release_tag="$(python3 -c \
        "import json; d=json.load(open('$rel_tmp')); print(d.get('tag_name',''))" \
        2>/dev/null || echo "")"
    release_name="$(python3 -c \
        "import json; d=json.load(open('$rel_tmp')); print((d.get('name') or '').replace('\"','')[:100])" \
        2>/dev/null || echo "")"
    release_date="$(python3 -c \
        "import json; d=json.load(open('$rel_tmp')); print(d.get('published_at',''))" \
        2>/dev/null || echo "")"
    rm -f "$rel_tmp"

    if [[ -n "$release_tag" ]]; then
        tarball_url="https://github.com/$github_repo/archive/refs/tags/${release_tag}.tar.gz"
        info "Latest release: $release_tag ($release_date)"
    else
        fallback=true
        release_tag="HEAD-${default_branch}"
        release_name="No formal release — HEAD of ${default_branch}"
        release_date="$last_push"
        tarball_url="https://github.com/$github_repo/archive/refs/heads/${default_branch}.tar.gz"
        warn "No formal release — falling back to HEAD of ${default_branch}"
    fi

    # ── 3. Download tarball (idempotent: skip if present, .part cleanup on fail)
    local tarball_file="$repo_dir/release/${safe_name}_${release_tag//\//-}.tar.gz"

    if [[ -f "$tarball_file" ]] && ! $UPDATE; then
        local size; size="$(du -sh "$tarball_file" | cut -f1)"
        info "Tarball already present ($size) — skipping download"
    else
        info "Downloading tarball …"
        if gh_download "$tarball_url" "$tarball_file"; then
            local size; size="$(du -sh "$tarball_file" | cut -f1)"
            ok "Downloaded $size → $(basename "$tarball_file")"
        else
            fail "Download failed: $tarball_url"
            # .part file is already cleaned up by gh_download on failure
            ((N_FAIL++)) || true
            return 0
        fi
    fi

    # ── 4. Extract README from tarball ────────────────────────────────────────
    local readme_extracted=false
    for readme_name in README.md README.rst README.txt readme.md Readme.md; do
        local inner_path
        inner_path="$(tar -tzf "$tarball_file" 2>/dev/null \
            | grep -i "/$readme_name$" | head -1 || true)"
        if [[ -n "$inner_path" ]]; then
            tar -xzf "$tarball_file" -O "$inner_path" \
                > "$repo_dir/README.md" 2>/dev/null \
                && readme_extracted=true && break
        fi
    done
    $readme_extracted && ok "README extracted" || info "No README found in tarball"

    # ── 5. metadata.json — written atomically via Python tmp→rename ───────────
    local meta_json
    meta_json="$(python3 - <<PYEOF
import json
meta = {
    "schema_version":  "1.1",
    "github_repo":     "$github_repo",
    "github_url":      "https://github.com/$github_repo",
    "category":        "$category",
    "risk":            "$risk",
    "licence":         "${gh_licence:-$licence}",
    "stars":           int("${stars:-0}") if "${stars:-0}".strip().lstrip('-').isdigit() else 0,
    "description":     "$description",
    "default_branch":  "$default_branch",
    "last_pushed_at":  "$last_push",
    "release_tag":     "$release_tag",
    "release_name":    "$release_name",
    "release_date":    "$release_date",
    "is_head_fallback": $( [[ "$fallback" == "true" ]] && echo "True" || echo "False" ),
    "archived_at":     "$archived_at",
    "tarball_file":    "$(basename "$tarball_file")",
}
print(json.dumps(meta, indent=2))
PYEOF
)"
    atomic_json "$repo_dir/metadata.json" "$meta_json"
    ok "metadata.json written (atomically)"
    ((N_DONE++)) || true
}

# ── Main loop ─────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "  code-archival · %s\n" "$(date -u '+%Y-%m-%d %H:%M UTC')"
printf "  %d repos → %s\n" "$TOTAL" "$ARCHIVE_DIR"
[[ -n "$FILTER_CATEGORY" ]] && printf "  category filter: %s\n" "$FILTER_CATEGORY"
[[ -n "$FILTER_RISK"     ]] && printf "  risk filter:     %s\n" "$FILTER_RISK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

COUNT=0
for repo_line in "${REPOS[@]}"; do
    IFS='|' read -r github_repo category risk licence <<< "$repo_line"
    [[ -n "$SINGLE_REPO" && "$github_repo" != "$SINGLE_REPO" ]] && continue
    ((COUNT++)) || true
    printf "[%d/%d] %s\n" "$COUNT" "$TOTAL" "$github_repo"
    log "[$COUNT/$TOTAL] $github_repo [$category/$risk]"
    archive_repo "$github_repo" "$category" "$risk" "$licence" || true
    echo ""
done

# ── Rebuild index.json atomically ─────────────────────────────────────────────
# Reads all present metadata.json files — safe to run on partial archives.
# Written as tmp→rename so a concurrent read never sees a half-written file.
if ! $DRY_RUN; then
    local_index="$(python3 - <<PYEOF
import json
from pathlib import Path

archive_dir = Path("$ARCHIVE_DIR")
entries = []
for meta_file in sorted(archive_dir.glob("*/metadata.json")):
    try:
        entries.append(json.loads(meta_file.read_text()))
    except Exception:
        pass

entries.sort(key=lambda e: (e.get("category",""), e.get("github_repo","")))

index = {
    "schema_version": "1.1",
    "generated_at":   "$(date -u '+%Y-%m-%dT%H:%M:%SZ')",
    "total_repos":    len(entries),
    "repos":          entries,
}
print(json.dumps(index, indent=2))
PYEOF
)"
    atomic_json "$INDEX_FILE" "$local_index"
    echo "  Rebuilt index.json ($(echo "$local_index" | python3 -c \
        "import json,sys; print(json.load(sys.stdin)['total_repos'])" 2>/dev/null || echo "?") repos)"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "  Done.  Archived: %d  Skipped: %d  Failed: %d\n" "$N_DONE" "$N_SKIP" "$N_FAIL"
echo "  Output: $ARCHIVE_DIR"
du -sh "$ARCHIVE_DIR" 2>/dev/null || true
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Complete. done=$N_DONE skipped=$N_SKIP failed=$N_FAIL"
