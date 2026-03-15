#!/usr/bin/env bash
# =============================================================================
# archive.sh — Archive latest release of open-source AI projects to disk
#
# Idempotent: safe to run multiple times. Already-archived repos are skipped
# unless --update is passed. Partial downloads are cleaned up on failure.
# Continues past any individual repo failure — all failures are recorded with
# reasons in manifest.json and MANIFEST.md.
#
# Handles GitHub 301 redirects automatically (renamed/transferred repos).
#
# For each repo in registry.yaml:
#   1. Follow any 301 redirect to canonical path
#   2. Download latest tagged release tarball from GitHub  → <repo>/release/
#   3. Write metadata.json atomically                      → <repo>/metadata.json
#   4. Snapshot the README                                 → <repo>/README.md
#   5. Rebuild index.json and MANIFEST.md atomically at end of run
#
# Usage:
#   bash archive.sh                             # archive all (skip existing)
#   bash archive.sh --output /mnt/models/d5     # explicit output dir
#   bash archive.sh --dry-run                   # list what would run, no writes
#   bash archive.sh --update                    # re-download all (refresh)
#   bash archive.sh --repo ggml-org/llama.cpp   # single repo only
#   bash archive.sh --category inference        # one category only
#   bash archive.sh --risk critical             # one risk level only
#   bash archive.sh --registry registry-skills.yaml  # use alternate registry (e.g. skills)
#
# Output layout:
#   <output>/code-archives/
#     ggml-org__llama.cpp/
#       release/           ← release tarball(s)
#       metadata.json      ← stars, licence, release tag, sha, archive date, risk
#       README.md          ← README snapshot from tarball
#     index.json           ← rebuilt atomically at end of every run
#     manifest.json        ← per-repo status: targeted/downloaded/failed + reason
#     MANIFEST.md          ← human-readable table of all repos + status
#     archive.log          ← append-only timestamped log
# =============================================================================

# NOTE: We do NOT use set -e here. The script must survive individual repo
# failures and always complete the full loop + manifest write.
set -uo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_ROOT="/mnt/models/d5"

# Auto-load GITHUB_TOKEN from .secrets if not already in environment
if [[ -z "${GITHUB_TOKEN:-}" && -f "$SCRIPT_DIR/.secrets" ]]; then
    GITHUB_TOKEN="$(grep -E '^GITHUB_TOKEN=' "$SCRIPT_DIR/.secrets" \
        | head -1 | cut -d= -f2- | tr -d '[:space:]')"
    export GITHUB_TOKEN
fi
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

REGISTRY="$SCRIPT_DIR/registry.yaml"
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
        --registry)   i=$((i+1)); REGISTRY="${!i}" ;;
        --registry=*) REGISTRY="${arg#--registry=}" ;;
        --help|-h)
            sed -n '/^# Usage:/,/^# ===/{s/^# \{0,1\}//p}' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
    i=$((i+1))
done

# Resolve relative registry path to script dir
case "$REGISTRY" in
    /*) ;;
    *) REGISTRY="$SCRIPT_DIR/$REGISTRY" ;;
esac

ARCHIVE_DIR="$OUTPUT_ROOT/code-archives"
LOG_FILE="$ARCHIVE_DIR/archive.log"
INDEX_FILE="$ARCHIVE_DIR/index.json"
MANIFEST_JSON="$ARCHIVE_DIR/manifest.json"
MANIFEST_MD="$ARCHIVE_DIR/MANIFEST.md"
RUN_LOG="$ARCHIVE_DIR/archive-run-$(date -u '+%Y%m%d-%H%M%S').log"

# ── Dependency check ──────────────────────────────────────────────────────────
for cmd in curl python3 tar; do
    command -v "$cmd" &>/dev/null || { echo "ERROR: '$cmd' not found." >&2; exit 1; }
done
python3 -c "import yaml" &>/dev/null \
    || { echo "ERROR: python3 pyyaml missing. Run: pip install pyyaml" >&2; exit 1; }

# ── Setup ─────────────────────────────────────────────────────────────────────
mkdir -p "$ARCHIVE_DIR"

log() {
    local msg="[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] $*"
    echo "$msg" | tee -a "$LOG_FILE" | tee -a "$RUN_LOG" >/dev/null
    echo "$msg"
}
ok()   { echo "  ✓ $*"; }
info() { echo "  · $*"; }
warn() { echo "  ⚠ $*"; }
fail() { echo "  ✗ $*"; }

# ── Per-repo manifest state ───────────────────────────────────────────────────
# Associative arrays keyed by github_repo
declare -A MANIFEST_STATUS   # downloaded | skipped | failed
declare -A MANIFEST_REASON   # human-readable reason for skipped/failed
declare -A MANIFEST_TAG      # release tag archived
declare -A MANIFEST_SIZE     # tarball size (human)
declare -A MANIFEST_DATE     # archived_at timestamp
declare -A MANIFEST_STARS    # star count
declare -A MANIFEST_CATEGORY
declare -A MANIFEST_RISK

# ── GitHub token warning ──────────────────────────────────────────────────────
if [[ -z "$GITHUB_TOKEN" ]]; then
    warn "GITHUB_TOKEN not set — unauthenticated API (60 req/hr limit)."
    warn "  Set: export GITHUB_TOKEN=ghp_... or add GITHUB_TOKEN= to .secrets"
fi

# ── GitHub helpers ────────────────────────────────────────────────────────────

# gh_api: fetch a GitHub API URL, following 301 redirects, retrying on 429/403.
# Echos the JSON body on success. On 404 echoes "{}". On persistent error echoes "{}".
gh_api() {
    local url="$1"
    local attempt body http_code location
    for attempt in 1 2 3 4; do
        body="$(curl -sS --retry 0 \
            -H "Accept: application/vnd.github+json" \
            -H "X-GitHub-Api-Version: 2022-11-28" \
            ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
            -w "\n__HTTP_CODE__:%{http_code}\n__LOCATION__:%{redirect_url}" \
            "$url" 2>/dev/null || true)"
        http_code="$(echo "$body" | grep -o '__HTTP_CODE__:[0-9]*' | cut -d: -f2 || echo "0")"
        location="$(echo "$body"  | grep -o '__LOCATION__:.*'      | cut -d: -f2- || echo "")"
        body="$(echo "$body" | grep -Ev '__HTTP_CODE__|__LOCATION__')"
        case "$http_code" in
            200)
                echo "$body"; return 0 ;;
            301|302)
                # Follow redirect: extract new owner/repo from Location header
                local new_path
                new_path="$(echo "$location" | grep -oP 'api\.github\.com/repos/\K[^?]+' || true)"
                if [[ -n "$new_path" ]]; then
                    url="https://api.github.com/repos/$new_path"
                    warn "Redirect → $new_path"
                else
                    # Fall back to curl -L for opaque redirects
                    body="$(curl -sSkL --retry 0 \
                        -H "Accept: application/vnd.github+json" \
                        -H "X-GitHub-Api-Version: 2022-11-28" \
                        ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
                        "$url" 2>/dev/null || true)"
                    echo "$body"; return 0
                fi
                ;;
            403|429)
                local wait=$(( 60 * attempt ))
                warn "GitHub rate-limited (HTTP $http_code) — sleeping ${wait}s (attempt $attempt/4) …"
                sleep "$wait" ;;
            404)
                echo "{}"; return 0 ;;  # repo not found — caller handles
            *)
                sleep $(( 5 * attempt )) ;;
        esac
    done
    echo "{}"; return 0
}

# gh_api_follow: like gh_api but always uses curl -L (simpler, for tarball URLs)
gh_download() {
    local url="$1" dest="$2"
    local part="${dest}.part"
    if curl -fsSL --retry 3 --retry-delay 5 \
            ${GITHUB_TOKEN:+-H "Authorization: Bearer $GITHUB_TOKEN"} \
            -o "$part" "$url" 2>/dev/null; then
        mv "$part" "$dest"
        return 0
    else
        rm -f "$part"
        return 1
    fi
}

# Atomic JSON write: write to .tmp then rename
atomic_json() {
    local dest="$1" content="$2"
    local tmp="${dest}.tmp"
    printf '%s' "$content" > "$tmp"
    mv "$tmp" "$dest"
}

# ── Parse registry ────────────────────────────────────────────────────────────
mapfile -t REPOS < <(python3 - <<PYEOF
import yaml, sys
data = yaml.safe_load(open('$REGISTRY'))
seen = set()
for r in data.get('repos', []):
    gh  = r.get('github', '').strip()
    cat = r.get('category', 'unknown')
    rsk = r.get('risk', 'medium')
    lic = r.get('licence', 'unknown')
    nts = (r.get('notes') or '').replace('\n', ' ').replace('|', '/').strip()[:120]
    if not gh or gh in seen:
        continue
    seen.add(gh)
    if '$FILTER_CATEGORY' and cat != '$FILTER_CATEGORY':
        continue
    if '$FILTER_RISK' and rsk != '$FILTER_RISK':
        continue
    print(f"{gh}|{cat}|{rsk}|{lic}|{nts}")
PYEOF
)

TOTAL=${#REPOS[@]}
N_DONE=0; N_SKIP=0; N_FAIL=0

log "=================================================="
log "code-archival run started"
log "Output    : $ARCHIVE_DIR"
log "Repos     : $TOTAL"
log "Registry  : $REGISTRY"
log "Dry-run   : $DRY_RUN"
log "Update    : $UPDATE"
log "Filter cat: ${FILTER_CATEGORY:-(all)}"
log "Filter rsk: ${FILTER_RISK:-(all)}"
log "=================================================="

# ── Per-repo archive function ─────────────────────────────────────────────────
# Returns 0 always. Sets MANIFEST_* arrays for the repo.
archive_repo() {
    local github_repo="$1" category="$2" risk="$3" licence="$4"
    local safe_name="${github_repo//\//__}"
    local repo_dir="$ARCHIVE_DIR/$safe_name"
    local archived_at; archived_at="$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

    MANIFEST_CATEGORY["$github_repo"]="$category"
    MANIFEST_RISK["$github_repo"]="$risk"

    # ── dry-run ───────────────────────────────────────────────────────────────
    if $DRY_RUN; then
        info "DRY-RUN → $repo_dir"
        MANIFEST_STATUS["$github_repo"]="dry-run"
        MANIFEST_REASON["$github_repo"]="dry-run"
        return 0
    fi

    # ── skip if already done ──────────────────────────────────────────────────
    if [[ -f "$repo_dir/metadata.json" ]] && ! $UPDATE; then
        local existing_tag
        existing_tag="$(python3 -c \
            "import json; print(json.load(open('$repo_dir/metadata.json')).get('release_tag','?'))" \
            2>/dev/null || echo "?")"
        info "Already archived ($existing_tag) — skipping"
        N_SKIP=$(( N_SKIP + 1 ))
        MANIFEST_STATUS["$github_repo"]="skipped"
        MANIFEST_REASON["$github_repo"]="already archived ($existing_tag)"
        MANIFEST_TAG["$github_repo"]="$existing_tag"
        local sz; sz="$(du -sh "$repo_dir/release" 2>/dev/null | cut -f1 || echo "?")"
        MANIFEST_SIZE["$github_repo"]="$sz"
        return 0
    fi

    mkdir -p "$repo_dir/release"

    # ── 1. GitHub repo metadata (follows 301 redirects) ──────────────────────
    local repo_json; repo_json="$(gh_api "https://api.github.com/repos/$github_repo")"
    local has_id; has_id="$(python3 -c \
        "import json,sys; d=json.loads(sys.stdin.read()); print('yes' if 'id' in d else 'no')" \
        <<< "$repo_json" 2>/dev/null || echo "no")"

    if [[ "$has_id" != "yes" ]]; then
        local msg="GitHub API returned no data (repo may be renamed, private, or deleted)"
        fail "$msg for $github_repo"
        N_FAIL=$(( N_FAIL + 1 ))
        MANIFEST_STATUS["$github_repo"]="failed"
        MANIFEST_REASON["$github_repo"]="$msg"
        return 0
    fi

    # Check if the API redirected us to a different canonical name
    local canonical_repo; canonical_repo="$(python3 -c \
        "import json,sys; d=json.loads(sys.stdin.read()); print(d.get('full_name',''))" \
        <<< "$repo_json" 2>/dev/null || echo "")"
    if [[ -n "$canonical_repo" && "$canonical_repo" != "$github_repo" ]]; then
        warn "Repo moved: $github_repo → $canonical_repo (update registry for future runs)"
        github_repo="$canonical_repo"
        safe_name="${github_repo//\//__}"
        repo_dir="$ARCHIVE_DIR/$safe_name"
        mkdir -p "$repo_dir/release"
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

    MANIFEST_STARS["$github_repo"]="$stars"

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

    # ── 3. Download tarball ───────────────────────────────────────────────────
    local tarball_file="$repo_dir/release/${safe_name}_${release_tag//\//-}.tar.gz"

    if [[ -f "$tarball_file" ]] && ! $UPDATE; then
        local size; size="$(du -sh "$tarball_file" | cut -f1)"
        info "Tarball already present ($size) — skipping download"
        MANIFEST_SIZE["$github_repo"]="$size"
    else
        info "Downloading tarball …"
        if gh_download "$tarball_url" "$tarball_file"; then
            local size; size="$(du -sh "$tarball_file" | cut -f1)"
            ok "Downloaded $size → $(basename "$tarball_file")"
            MANIFEST_SIZE["$github_repo"]="$size"
        else
            local msg="Download failed (curl error): $tarball_url"
            fail "$msg"
            N_FAIL=$(( N_FAIL + 1 ))
            MANIFEST_STATUS["$github_repo"]="failed"
            MANIFEST_REASON["$github_repo"]="$msg"
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
            if tar -xzf "$tarball_file" -O "$inner_path" \
                > "$repo_dir/README.md" 2>/dev/null; then
                readme_extracted=true
                break
            fi
        fi
    done
    $readme_extracted && ok "README extracted" || info "No README found in tarball"

    # ── 5. metadata.json ──────────────────────────────────────────────────────
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
)" || true

    if [[ -n "$meta_json" ]]; then
        atomic_json "$repo_dir/metadata.json" "$meta_json"
        ok "metadata.json written (atomically)"
    fi

    N_DONE=$(( N_DONE + 1 ))
    MANIFEST_STATUS["$github_repo"]="downloaded"
    MANIFEST_REASON["$github_repo"]=""
    MANIFEST_TAG["$github_repo"]="$release_tag"
    MANIFEST_DATE["$github_repo"]="$archived_at"
    return 0
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
    IFS='|' read -r github_repo category risk licence _notes <<< "$repo_line"
    [[ -n "$SINGLE_REPO" && "$github_repo" != "$SINGLE_REPO" ]] && continue
    COUNT=$(( COUNT + 1 ))
    printf "[%d/%d] %s\n" "$COUNT" "$TOTAL" "$github_repo"
    log "[$COUNT/$TOTAL] $github_repo [$category/$risk]"
    # Wrap in error handler so any unexpected failure is caught and logged,
    # but the loop always continues to the next repo.
    if ! archive_repo "$github_repo" "$category" "$risk" "$licence" 2>&1; then
        warn "Unexpected error in archive_repo for $github_repo — continuing"
        N_FAIL=$(( N_FAIL + 1 ))
        MANIFEST_STATUS["$github_repo"]="${MANIFEST_STATUS[$github_repo]:-failed}"
        MANIFEST_REASON["$github_repo"]="${MANIFEST_REASON[$github_repo]:-unexpected shell error}"
    fi
    echo ""
done

# ── Rebuild index.json atomically ─────────────────────────────────────────────
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
)" || true
    if [[ -n "$local_index" ]]; then
        atomic_json "$INDEX_FILE" "$local_index"
        n_idx="$(echo "$local_index" | python3 -c \
            "import json,sys; print(json.load(sys.stdin)['total_repos'])" 2>/dev/null || echo "?")"
        echo "  Rebuilt index.json ($n_idx repos)"
    fi
fi

# ── Write manifest.json + MANIFEST.md ────────────────────────────────────────
if ! $DRY_RUN; then
    # Build manifest.json — one entry per targeted repo
    python3 - <<PYEOF
import json, yaml
from pathlib import Path

registry_path = Path("$REGISTRY")
archive_dir   = Path("$ARCHIVE_DIR")
generated_at  = "$(date -u '+%Y-%m-%dT%H:%M:%SZ')"

data = yaml.safe_load(registry_path.read_text())
repos = data.get('repos', [])

# Deduplicate
seen = set()
unique_repos = []
for r in repos:
    gh = r.get('github','').strip()
    if gh and gh not in seen:
        seen.add(gh)
        unique_repos.append(r)

manifest_entries = []
for r in unique_repos:
    gh       = r.get('github','').strip()
    cat      = r.get('category','unknown')
    risk     = r.get('risk','medium')
    lic      = r.get('licence','unknown')

    # Apply category/risk filters if set
    if '$FILTER_CATEGORY' and cat != '$FILTER_CATEGORY':
        continue
    if '$FILTER_RISK' and risk != '$FILTER_RISK':
        continue

    safe_name = gh.replace('/','__')
    meta_file = archive_dir / safe_name / "metadata.json"

    # Also check for redirected canonical name (metadata has actual github_repo)
    canonical = gh
    status = "failed"
    reason = "not attempted or unknown error"
    tag    = ""
    size   = ""
    stars  = 0
    archived_at = ""

    # Search for a matching metadata by scanning dirs
    for mf in sorted(archive_dir.glob("*/metadata.json")):
        try:
            m = json.loads(mf.read_text())
            if m.get("github_repo","") == gh or mf.parent.name == safe_name:
                canonical   = m.get("github_repo", gh)
                status      = "downloaded"
                reason      = ""
                tag         = m.get("release_tag","")
                stars       = m.get("stars",0)
                archived_at = m.get("archived_at","")
                td = mf.parent / "release"
                if td.exists():
                    tarballs = list(td.glob("*.tar.gz"))
                    if tarballs:
                        sz = tarballs[0].stat().st_size
                        size = f"{sz/1024/1024:.1f} MB" if sz < 1024**3 else f"{sz/1024**3:.2f} GB"
                break
        except Exception:
            pass

    manifest_entries.append({
        "github_repo":   gh,
        "canonical_repo": canonical,
        "category":      cat,
        "risk":          risk,
        "licence":       lic,
        "status":        status,
        "reason":        reason,
        "release_tag":   tag,
        "stars":         stars,
        "size":          size,
        "archived_at":   archived_at,
    })

manifest = {
    "schema_version": "1.0",
    "generated_at":   generated_at,
    "summary": {
        "total":      len(manifest_entries),
        "downloaded": sum(1 for e in manifest_entries if e["status"] == "downloaded"),
        "skipped":    sum(1 for e in manifest_entries if e["status"] == "skipped"),
        "failed":     sum(1 for e in manifest_entries if e["status"] == "failed"),
    },
    "repos": manifest_entries,
}

# Write manifest.json atomically
tmp = Path("$MANIFEST_JSON.tmp")
tmp.write_text(json.dumps(manifest, indent=2))
tmp.replace(Path("$MANIFEST_JSON"))

# Write MANIFEST.md atomically
now = generated_at
s = manifest["summary"]
lines = [
    "# Code-Archival Manifest",
    "",
    f"> Generated: {now}",
    "",
    "## Summary",
    "",
    "| Status | Count |",
    "|--------|-------|",
    f"| ✅ downloaded | {s['downloaded']} |",
    f"| ⏭️  skipped   | {s['skipped']} |",
    f"| ❌ failed     | {s['failed']} |",
    f"| **Total**     | **{s['total']}** |",
    "",
    "## All Repos",
    "",
    "| # | Repo | Category | Risk | Status | Tag | Size | Stars | Reason / Notes |",
    "|---|------|----------|------|--------|-----|------|-------|----------------|",
]
icons = {"downloaded": "✅", "skipped": "⏭️", "failed": "❌"}
for i, e in enumerate(manifest_entries, 1):
    icon   = icons.get(e["status"], "❓")
    repo   = e["github_repo"]
    canon  = e["canonical_repo"]
    url    = f"https://github.com/{canon}"
    label  = f"[{repo}]({url})" if canon == repo else f"[{repo}]({url}) → {canon}"
    reason = e["reason"] or ""
    lines.append(
        f"| {i} | {label} | {e['category']} | {e['risk']} "
        f"| {icon} {e['status']} | {e['release_tag'] or '—'} "
        f"| {e['size'] or '—'} | {e['stars']:,} | {reason} |"
    )

content = "\n".join(lines) + "\n"
tmp_md = Path("$MANIFEST_MD.tmp")
tmp_md.write_text(content)
tmp_md.replace(Path("$MANIFEST_MD"))

print(f"  manifest.json written ({len(manifest_entries)} repos)")
print(f"  MANIFEST.md written")
PYEOF
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
printf "  Done.  Archived: %d  Skipped: %d  Failed: %d\n" "$N_DONE" "$N_SKIP" "$N_FAIL"
echo "  Output: $ARCHIVE_DIR"
du -sh "$ARCHIVE_DIR" 2>/dev/null || true
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
log "Complete. done=$N_DONE skipped=$N_SKIP failed=$N_FAIL"
