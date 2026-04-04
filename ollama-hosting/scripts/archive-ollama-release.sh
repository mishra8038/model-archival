#!/usr/bin/env bash
# Download and archive the Ollama GitHub release that matches the Supermicro (or pinned) version.
# Idempotent: skips re-download when on-disk files already match sha256sum.txt.
#
# Env:
#   OLLAMA_VERSION       e.g. 0.20.0 — if unset, probe via ssh SUPER_OLLAMA_REMOTE + ollama --version
#   SUPER_OLLAMA_REMOTE  default x@192.168.8.106
#   OLLAMA_ARCHIVE_ASSET default ollama-linux-amd64.tar.zst (NVIDIA/CUDA Linux x86_64; not *-rocm*)
#   OLLAMA_ARCHIVE_EXTRA optional space-separated extra release filenames (e.g. install.sh)
#   CURL                 default curl -fsSL
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOSTING="$(cd "$SCRIPT_DIR/.." && pwd)"
DEST_ROOT="${OLLAMA_ARCHIVE_ROOT:-$HOSTING/archives/ollama-releases}"
REMOTE="${SUPER_OLLAMA_REMOTE:-x@192.168.8.106}"
PRIMARY_ASSET="${OLLAMA_ARCHIVE_ASSET:-ollama-linux-amd64.tar.zst}"
EXTRA_ASSETS="${OLLAMA_ARCHIVE_EXTRA:-install.sh}"
CURL=(curl -fsSL)

probe_version() {
  local line
  if [[ -n "${OLLAMA_VERSION:-}" ]]; then
    echo "archive-ollama-release: using OLLAMA_VERSION=$OLLAMA_VERSION" >&2
    return 0
  fi
  line="$(ssh -o BatchMode=yes -o ConnectTimeout=12 "$REMOTE" 'ollama --version 2>/dev/null' || true)"
  if [[ "$line" =~ ([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    OLLAMA_VERSION="${BASH_REMATCH[1]}"
    echo "archive-ollama-release: probed OLLAMA_VERSION=$OLLAMA_VERSION from $REMOTE" >&2
    return 0
  fi
  echo "error: set OLLAMA_VERSION=… or ensure ssh $REMOTE 'ollama --version' works" >&2
  exit 1
}

verify_one_hash() {
  local dir="$1" file="$2"
  # sha256sum.txt lines look like: HASH  ./filename
  (cd "$dir" && grep -F "$file" sha256sum.txt | head -1 | sha256sum -c --status -) 2>/dev/null
}

fetch_if_stale() {
  local tag="$1" dest="$2" name="$3" base="$4"
  local url="$base/$name"
  if [[ -f "$dest/$name" ]] && verify_one_hash "$dest" "$name"; then
    echo "archive-ollama-release: OK (cached) $name" >&2
    return 0
  fi
  echo "archive-ollama-release: downloading $url" >&2
  "${CURL[@]}" -o "$dest/$name.part" "$url"
  mv -f "$dest/$name.part" "$dest/$name"
  verify_one_hash "$dest" "$name"
  echo "archive-ollama-release: verified sha256 $name" >&2
}

write_manifest() {
  local dest="$1" tag="$2" ver="$3"
  local sha_tar sha_inst
  sha_tar="$(sha256sum "$dest/$PRIMARY_ASSET" | awk '{print $1}')"
  sha_inst=""
  [[ -f "$dest/install.sh" ]] && sha_inst="$(sha256sum "$dest/install.sh" | awk '{print $1}')"
  printf '%s\n' "{
  \"ollama_version\": \"${ver}\",
  \"release_tag\": \"${tag}\",
  \"release_page\": \"https://github.com/ollama/ollama/releases/tag/${tag}\",
  \"probed_ssh_host\": \"${REMOTE}\",
  \"archived_at_utc\": \"$(date -u -Iseconds)\",
  \"primary_asset\": \"${PRIMARY_ASSET}\",
  \"sha256_${PRIMARY_ASSET}\": \"${sha_tar}\",
  \"sha256_install_sh\": \"${sha_inst}\",
  \"note\": \"Extract ${PRIMARY_ASSET} or use pinned install.sh for the same major/minor/patch as Supermicro.\"
}"
}

probe_version
TAG="v${OLLAMA_VERSION}"
BASE="https://github.com/ollama/ollama/releases/download/${TAG}"
DEST="$DEST_ROOT/$TAG"
mkdir -p "$DEST"

echo "archive-ollama-release: fetching sha256sum.txt for $TAG" >&2
"${CURL[@]}" -o "$DEST/sha256sum.txt.part" "$BASE/sha256sum.txt"
mv -f "$DEST/sha256sum.txt.part" "$DEST/sha256sum.txt"

fetch_if_stale "$TAG" "$DEST" "$PRIMARY_ASSET" "$BASE"
for extra in $EXTRA_ASSETS; do
  [[ "$extra" == "$PRIMARY_ASSET" ]] && continue
  fetch_if_stale "$TAG" "$DEST" "$extra" "$BASE"
done

write_manifest "$DEST" "$TAG" "$OLLAMA_VERSION" >"$DEST/MANIFEST.json.tmp"
mv -f "$DEST/MANIFEST.json.tmp" "$DEST/MANIFEST.json"

echo "archive-ollama-release: done → $DEST" >&2
ls -lh "$DEST/$PRIMARY_ASSET" "$DEST/MANIFEST.json" 2>/dev/null || ls -lh "$DEST"
