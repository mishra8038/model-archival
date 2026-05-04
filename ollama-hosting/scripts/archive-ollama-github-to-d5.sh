#!/usr/bin/env bash
# Archive two Ollama GitHub bundles on the archival VM under **/mnt/models-d5/ollama**:
#
#   **pinned/<tag>/**  — release that matches **SUPER_OLLAMA_REMOTE** `ollama --version` (Supermicro parity).
#   **latest/**        — **GitHub releases/latest** (rolling); overwritten each run when upstream moves.
#
# Each bundle contains **release/** (install.sh + ollama-linux-amd64.tar.zst + sha256sum.txt) and **code/**
# (shallow **ollama/ollama** clone at that tag). If pinned and latest tags are identical, **latest** is a
# relative symlink to **pinned/<tag>** (no duplicated tarball on disk).
#
# Idempotent: release files re-fetched only if sha256 mismatch; **code/** recloned only when **.bundle_tag**
# under that bundle changes.
#
# Env:
#   ARCHIVAL_VM              default ubuntu@192.168.8.32
#   OLLAMA_VM_D5_OLLAMA_ROOT default /mnt/models-d5/ollama
#   SUPER_OLLAMA_REMOTE      default x@192.168.8.106 (for pinned tag probe)
#   OLLAMA_PINNED_VERSION    e.g. 0.20.0 — skip SSH probe if set
#   OLLAMA_LATEST_TAG        e.g. v0.20.2 — skip GitHub /releases/latest if set
#   OLLAMA_GITHUB_TAG        deprecated alias for OLLAMA_LATEST_TAG
#   OLLAMA_BUNDLE_STAGING    default $HOSTING/archives/ollama-d5-bundle/root (was tree/ — ok to delete old tree/)
#   OLLAMA_ARCHIVE_ASSET     default ollama-linux-amd64.tar.zst (not *-rocm*)
#   OLLAMA_RSYNC_EXTRA       extra rsync args; delete flags stripped
#   OLLAMA_SKIP_RSYNC        if 1, only prepare local staging
#   OLLAMA_SKIP_PINNED       if 1, only build **latest/**
#   OLLAMA_SKIP_LATEST       if 1, only build **pinned/**
#   OLLAMA_D5_CLEAN_LEGACY   default 1 — remove pre-layout **release/** + **code/** at VM root after rsync
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOSTING="$(cd "$SCRIPT_DIR/.." && pwd)"
ARCHIVAL_VM="${ARCHIVAL_VM:-ubuntu@192.168.8.32}"
VM_ROOT="${OLLAMA_VM_D5_OLLAMA_ROOT:-/mnt/models-d5/ollama}"
STAGING="${OLLAMA_BUNDLE_STAGING:-$HOSTING/archives/ollama-d5-bundle/root}"
SUPER_REMOTE="${SUPER_OLLAMA_REMOTE:-x@192.168.8.106}"
PRIMARY_ASSET="${OLLAMA_ARCHIVE_ASSET:-ollama-linux-amd64.tar.zst}"
CURL=(curl -fsSL)
GIT_REMOTE="${OLLAMA_GIT_REMOTE:-https://github.com/ollama/ollama.git}"

sanitize_rsync_extra() {
  rsync_extra_array=()
  [[ -z "${OLLAMA_RSYNC_EXTRA:-}" ]] && return 0
  local -a raw
  read -r -a raw <<< "$OLLAMA_RSYNC_EXTRA"
  local tok
  for tok in "${raw[@]}"; do
    case "$tok" in
      --delete | --delete-before | --delete-during | --delete-after | --delete-delay | --delete-excluded | --delete-missing-args | --del | --remove-source-files | --max-delete | --max-delete=*)
        echo "archive-ollama-github-to-d5: ignoring disallowed rsync flag: $tok" >&2
        ;;
      *) rsync_extra_array+=("$tok") ;;
    esac
  done
}

normalize_v_tag() {
  local t="$1"
  t="${t#v}"
  printf 'v%s' "$t"
}

probe_pinned_version() {
  if [[ -n "${OLLAMA_PINNED_VERSION:-}" ]]; then
    TAG_PIN="$(normalize_v_tag "$OLLAMA_PINNED_VERSION")"
    echo "archive-ollama-github-to-d5: pinned tag=$TAG_PIN (OLLAMA_PINNED_VERSION)" >&2
    return 0
  fi
  local line
  line="$(ssh -o BatchMode=yes -o ConnectTimeout=12 "$SUPER_REMOTE" 'ollama --version 2>/dev/null' || true)"
  if [[ "$line" =~ ([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    TAG_PIN="$(normalize_v_tag "${BASH_REMATCH[1]}")"
    echo "archive-ollama-github-to-d5: pinned tag=$TAG_PIN (from $SUPER_REMOTE)" >&2
    return 0
  fi
  echo "error: set OLLAMA_PINNED_VERSION=… or fix ssh $SUPER_REMOTE ollama --version" >&2
  exit 1
}

resolve_latest_tag() {
  if [[ -n "${OLLAMA_LATEST_TAG:-}" ]]; then
    TAG_LAT="$(normalize_v_tag "$OLLAMA_LATEST_TAG")"
    echo "archive-ollama-github-to-d5: latest tag=$TAG_LAT (OLLAMA_LATEST_TAG)" >&2
    return 0
  fi
  if [[ -n "${OLLAMA_GITHUB_TAG:-}" ]]; then
    TAG_LAT="$(normalize_v_tag "$OLLAMA_GITHUB_TAG")"
    echo "archive-ollama-github-to-d5: latest tag=$TAG_LAT (OLLAMA_GITHUB_TAG, deprecated — use OLLAMA_LATEST_TAG)" >&2
    return 0
  fi
  TAG_LAT="$(python3 - <<'PY'
import json
import urllib.request
req = urllib.request.Request(
    "https://api.github.com/repos/ollama/ollama/releases/latest",
    headers={"Accept": "application/vnd.github+json", "User-Agent": "ollama-d5-archive"},
)
with urllib.request.urlopen(req, timeout=60) as r:
    data = json.load(r)
print(data["tag_name"])
PY
)"
  echo "archive-ollama-github-to-d5: latest tag=$TAG_LAT (GitHub releases/latest)" >&2
}

verify_one_hash() {
  local dir="$1" file="$2"
  (cd "$dir" && grep -F "$file" sha256sum.txt | head -1 | sha256sum -c --status -) 2>/dev/null
}

fetch_release_file() {
  local dest="$1" name="$2" base="$3"
  local url="$base/$name"
  if [[ -f "$dest/$name" ]] && verify_one_hash "$dest" "$name"; then
    echo "archive-ollama-github-to-d5: OK (cached) $name ($dest)" >&2
    return 0
  fi
  echo "archive-ollama-github-to-d5: downloading $url" >&2
  "${CURL[@]}" -o "$dest/$name.part" "$url"
  mv -f "$dest/$name.part" "$dest/$name"
  verify_one_hash "$dest" "$name"
  echo "archive-ollama-github-to-d5: verified sha256 $name" >&2
}

sync_source_tree() {
  local tag="$1" code_dir="$2" bundle_root="$3"
  local tag_file="$bundle_root/.bundle_tag"
  if [[ -f "$tag_file" ]] && [[ "$(cat "$tag_file")" == "$tag" ]] && [[ -d "$code_dir/.git" ]]; then
    echo "archive-ollama-github-to-d5: OK (cached) source $tag → $code_dir" >&2
    return 0
  fi
  echo "archive-ollama-github-to-d5: cloning $GIT_REMOTE @ $tag → $code_dir" >&2
  rm -rf "$code_dir"
  git clone --depth 1 --branch "$tag" "$GIT_REMOTE" "$code_dir"
  printf '%s\n' "$tag" >"$tag_file"
}

write_bundle_manifest() {
  local role="$1" rel_dir="$2" tag="$3" code_dir="$4" out="$5"
  local sha_tar sha_inst commit
  sha_tar="$(sha256sum "$rel_dir/$PRIMARY_ASSET" | awk '{print $1}')"
  sha_inst="$(sha256sum "$rel_dir/install.sh" | awk '{print $1}')"
  commit="$(git -C "$code_dir" rev-parse HEAD 2>/dev/null || echo "")"
  ROLE="$role" TAG="$tag" REMOTE="$GIT_REMOTE" VM_DST="${ARCHIVAL_VM}:${VM_ROOT}" \
    SHA_TAR="$sha_tar" SHA_SH="$sha_inst" COMMIT="$commit" PRIMARY="$PRIMARY_ASSET" SUPER_SSH="$SUPER_REMOTE" \
    OUT="$out" python3 <<'PY'
import json, os
m = {
    "role": os.environ["ROLE"],
    "release_tag": os.environ["TAG"],
    "github_release": f"https://github.com/ollama/ollama/releases/tag/{os.environ['TAG']}",
    "primary_asset": os.environ["PRIMARY"],
    f"sha256_{os.environ['PRIMARY']}": os.environ["SHA_TAR"],
    "sha256_install_sh": os.environ["SHA_SH"],
    "source_git_commit": os.environ["COMMIT"],
    "source_remote": os.environ["REMOTE"],
    "bundled_at_utc": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    "vm_destination": os.environ["VM_DST"],
}
if m["role"] == "pinned":
    m["probed_ssh_host"] = os.environ["SUPER_SSH"]
with open(os.environ["OUT"], "w") as f:
    json.dump(m, f, indent=2)
PY
}

build_one_bundle() {
  local role="$1" tag="$2" bundle_root="$3"
  local rel="$bundle_root/release"
  local code="$bundle_root/code"
  local base="https://github.com/ollama/ollama/releases/download/${tag}"
  mkdir -p "$rel"
  echo "archive-ollama-github-to-d5: [$role] fetching sha256sum.txt for $tag" >&2
  "${CURL[@]}" -o "$rel/sha256sum.txt.part" "$base/sha256sum.txt"
  mv -f "$rel/sha256sum.txt.part" "$rel/sha256sum.txt"
  fetch_release_file "$rel" "$PRIMARY_ASSET" "$base"
  fetch_release_file "$rel" "install.sh" "$base"
  sync_source_tree "$tag" "$code" "$bundle_root"
  write_bundle_manifest "$role" "$rel" "$tag" "$code" "$bundle_root/MANIFEST.json"
}

write_readme() {
  cat >"$STAGING/README.txt" <<'EOF'
Ollama upstream archive (GitHub).

  pinned/<tag>/  — matches Supermicro `ollama --version` (see SUPER_OLLAMA_REMOTE / OLLAMA_PINNED_VERSION).
  latest/        — GitHub releases/latest (updated each run), or symlink to pinned/<tag> when tags match.

Each bundle: release/ (install.sh, ollama-linux-amd64.tar.zst, sha256sum.txt) and code/ (shallow ollama/ollama clone).

Populate: ollama-hosting/scripts/archive-ollama-github-to-d5.sh
EOF
}

write_overview() {
  TAG_PIN="${TAG_PIN:-}" TAG_LAT="${TAG_LAT:-}" SUPER_REMOTE="$SUPER_REMOTE" VM_ROOT="$VM_ROOT" \
    OUT="$STAGING/overview.json" python3 <<'PY'
import json, os
from datetime import datetime, timezone
pin, lat = os.environ.get("TAG_PIN", ""), os.environ.get("TAG_LAT", "")
o = {
    "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
    "supermicro_ssh": os.environ["SUPER_REMOTE"],
    "vm_root": os.environ["VM_ROOT"],
}
if pin:
    o["pinned_tag"] = pin
    o["pinned_path"] = f"pinned/{pin}"
if lat:
    o["latest_tag"] = lat
if pin and lat:
    o["latest_same_as_pinned"] = pin == lat
    o["latest_is_symlink_to_pinned"] = pin == lat
    if pin == lat:
        o["latest_path"] = f"pinned/{pin}"
    else:
        o["latest_path"] = "latest"
with open(os.environ["OUT"], "w") as f:
    json.dump(o, f, indent=2)
PY
}

remove_legacy_vm_layout() {
  [[ "${OLLAMA_D5_CLEAN_LEGACY:-1}" == "0" ]] && return 0
  ssh -o BatchMode=yes -o ConnectTimeout=20 "$ARCHIVAL_VM" bash -s <<EOF
set -euo pipefail
ROOT=$(printf '%q' "$VM_ROOT")
if [[ -d "\$ROOT/pinned" ]] || [[ -L "\$ROOT/latest" ]] || [[ -d "\$ROOT/latest" ]]; then
  if [[ -e "\$ROOT/release/ollama-linux-amd64.tar.zst" ]] || [[ -d "\$ROOT/release" ]]; then
    echo "archive-ollama-github-to-d5: removing legacy flat release/ + code/ under \$ROOT" >&2
    rm -rf "\$ROOT/release" "\$ROOT/code"
    rm -f "\$ROOT/MANIFEST.json" "\$ROOT/.bundle_tag"
  fi
fi
EOF
}

# --- main ---
sanitize_rsync_extra
mkdir -p "$STAGING"

unset TAG_PIN TAG_LAT 2>/dev/null || true

SKIP_PIN="${OLLAMA_SKIP_PINNED:-0}"
SKIP_LAT="${OLLAMA_SKIP_LATEST:-0}"

if [[ "$SKIP_PIN" != 1 ]]; then
  probe_pinned_version
fi
if [[ "$SKIP_LAT" != 1 ]]; then
  resolve_latest_tag
fi

if [[ "$SKIP_LAT" == 1 ]]; then
  rm -rf "$STAGING/latest"
fi

PIN_ROOT=""
if [[ -n "$TAG_PIN" ]]; then
  PIN_ROOT="$STAGING/pinned/$TAG_PIN"
  mkdir -p "$PIN_ROOT"
  build_one_bundle "pinned" "$TAG_PIN" "$PIN_ROOT"
fi

if [[ -n "$TAG_LAT" && -n "$TAG_PIN" && "$TAG_LAT" == "$TAG_PIN" ]]; then
  echo "archive-ollama-github-to-d5: latest == pinned ($TAG_LAT) — latest → symlink" >&2
  rm -rf "$STAGING/latest"
  ln -sfn "pinned/$TAG_PIN" "$STAGING/latest"
elif [[ -n "$TAG_LAT" ]]; then
  LAT_ROOT="$STAGING/latest"
  rm -rf "$LAT_ROOT"
  mkdir -p "$LAT_ROOT"
  build_one_bundle "latest" "$TAG_LAT" "$LAT_ROOT"
fi

write_readme
if [[ -n "${TAG_PIN:-}" || -n "${TAG_LAT:-}" ]]; then
  write_overview
fi

ssh -o BatchMode=yes -o ConnectTimeout=20 "$ARCHIVAL_VM" "mkdir -p $(printf '%q' "$VM_ROOT")"

if [[ "${OLLAMA_SKIP_RSYNC:-0}" == "1" ]]; then
  echo "archive-ollama-github-to-d5: OLLAMA_SKIP_RSYNC=1 — staging only at $STAGING" >&2
  exit 0
fi

echo "archive-ollama-github-to-d5: rsync → $ARCHIVAL_VM:$VM_ROOT/" >&2
rsync -avh --info=progress2 "${rsync_extra_array[@]}" \
  -e "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new" \
  "$STAGING/" "${ARCHIVAL_VM}:${VM_ROOT}/"

remove_legacy_vm_layout

echo "archive-ollama-github-to-d5: done" >&2
