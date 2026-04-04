#!/usr/bin/env bash
#
# Ollama sync — copy the Ollama model cache from supermicro onto the archival VM (default D5).
#
# Policy (additive / archive-safe):
#   - New and updated blobs from the source cache are copied to the destination.
#   - **Completed models only:** Ollama in-progress shards (`models/blobs/*partial*`) are excluded
#     from rsync by default (OLLAMA_SYNC_INCLUDE_PARTIALS=1 to override — not recommended).
#   - After each VM sync, optional maintenance on the archival VM removes stray *partial* blobs and
#     `.rsync-partial` dirs on **all** cycle roots, then checks manifest↔blob integrity (OLLAMA_SYNC_VM_MAINTAIN=0 to skip).
#   - Files already at the destination that no longer exist in the source Ollama cache are NEVER
#     removed. Re-runs are safe after you delete models on supermicro.
#   Implemented by rsync without any --delete* options; RSYNC_EXTRA cannot add them.
#
# Default target is a single archive root on the VM (d5). Override with ARCHIVAL_VM_SITE_CYCLE
# or ARCHIVAL_VM_DEST=/path. Fixed ARCHIVAL_VM_DEST does not advance rotation state.
# Same additive policy everywhere; old blobs under prior paths stay until you move or prune them.
# Idempotent: rsync transfers deltas; --partial resumes interrupted runs.
#
# Strategies (vm mode, in order):
#   1) VM pull — rsync on the VM pulls from supermicro (best if VM can SSH to supermicro).
#   2) Bridge — sshfs on this host + rsync to VM (when VM cannot reach supermicro :22).
#
# Local sync (run on the host with disks mounted; default LOCAL_DEST is under D5):
#   OLLAMA_SYNC_DEST=local OLLAMA_D5_DEST=/mnt/models/d2/supermicro ./scripts/ollama-sync.sh
#
# Env:
#   SUPER_OLLAMA_REMOTE   Ollama host (default: x@192.168.8.106)
#   ARCHIVAL_VM           Archival VM (default: x@192.168.8.65)
#   ARCHIVAL_VM_DEST      Path on VM. If **unset or empty**, the next path from the rotation cycle
#                           is chosen (see docs/OLLAMA-CACHE-POLICY.md). If **set**, that path is used
#                           and the rotation counter is not advanced.
#   ARCHIVAL_VM_SITE_CYCLE  Optional comma-separated cycle: LABEL=PATH pairs or bare paths under
#                           /mnt/models/. Default: d5=/mnt/models/d5/supermicro only.
#   OLLAMA_SYNC_DEST      vm | local (default: vm)
#   OLLAMA_D5_DEST        local directory when OLLAMA_SYNC_DEST=local (default under D5; use a d2 path if D5 full)
#   OLLAMA_REMOTE_DIR     path under ~ on supermicro (default: .ollama)
#   OLLAMA_SUPER_PATH     absolute path on supermicro for sshfs (default: probe \$HOME/.ollama)
#   OLLAMA_SKIP_VM_PULL   if 1, skip strategy 1 and use bridge immediately (vm mode only)
#   SSHPASS               password for sshpass → supermicro (bridge + local rsync)
#   VM_SSHPASS            password for sshpass → archival VM (optional)
#   RSYNC_RSH             override ssh for supermicro rsync (local mode / bridge sshfs uses separate ssh)
#   RSYNC_EXTRA           extra rsync args (e.g. --dry-run); delete/remove flags are stripped
#   OLLAMA_SYNC_BWLIMIT_KB  rsync --bwlimit in KiB/s (default 0 = unlimited on LAN). Cap only if needed
#                             (Ollama *downloads* are throttled separately via pull-queue / trickle, not this script).
#   OLLAMA_SYNC_INCLUDE_PARTIALS  if 1, sync Ollama *partial* blob files (default 0 — completed only)
#   OLLAMA_SYNC_VM_MAINTAIN      if not 0, after VM sync run partial cleanup + integrity on all cycle roots (default 1)
#   OLLAMA_SYNC_UPDATE_INVENTORY  if not 0, after a successful sync run inventory refresh from REPO (non-fatal).
#     vm mode: SSH to ARCHIVAL_VM. local mode: scan LOCAL_DEST with disk label OLLAMA_VM_LOCAL_DISK_LABEL (default: local).
#     Set to 0 to skip. Extra args: OLLAMA_VM_INVENTORY_EXTRA (e.g. --infer-supermicro-cleared --supermicro-ssh x@host).
#   After inventory, regenerates docs/OLLAMA-ARCHIVAL-MODEL-MAP.md (model → disk → path).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

REMOTE="${SUPER_OLLAMA_REMOTE:-x@192.168.8.106}"
REMOTE_REL="${OLLAMA_REMOTE_DIR:-.ollama}"
ARCHIVAL_VM="${ARCHIVAL_VM:-x@192.168.8.65}"
# Empty → rotation (see sync_vm). Non-empty → fixed destination for this run.
ARCHIVAL_VM_DEST="${ARCHIVAL_VM_DEST:-}"
SYNC_DEST="${OLLAMA_SYNC_DEST:-vm}"
LOCAL_DEST="${OLLAMA_D5_DEST:-/mnt/models/d5/supermicro}"

# rsync --bwlimit is KiB/s. Default unlimited: Supermicro ↔ archive VM is LAN; do not confuse with Ollama pull caps.
RSYNC_BW_KB="${OLLAMA_SYNC_BWLIMIT_KB:-0}"
# Additive-only: never pass --delete* to rsync (see sanitize_rsync_extra).
# rsync --partial is for resumable *rsync* transfers, not Ollama's *-partial* blob files (excluded below).
RSYNC_BASE=(rsync -avh --partial --partial-dir=.rsync-partial --info=progress2)
if [[ -n "$RSYNC_BW_KB" && "$RSYNC_BW_KB" != "0" ]]; then
  RSYNC_BASE+=(--bwlimit="$RSYNC_BW_KB")
fi
if [[ "${OLLAMA_SYNC_INCLUDE_PARTIALS:-0}" != "1" ]]; then
  RSYNC_BASE+=(--exclude='models/blobs/*partial*' --exclude='.rsync-partial/')
  echo "ollama-sync: excluding incomplete Ollama blobs (models/blobs/*partial*) and .rsync-partial/" >&2
fi

if ! command -v rsync >/dev/null 2>&1 || ! command -v ssh >/dev/null 2>&1; then
  echo "error: need rsync and ssh" >&2
  exit 1
fi

if [[ -n "${SSHPASS:-}" ]] && ! command -v sshpass >/dev/null 2>&1; then
  echo "error: SSHPASS is set but sshpass is not installed" >&2
  exit 1
fi

if [[ -n "${VM_SSHPASS:-}" ]] && ! command -v sshpass >/dev/null 2>&1; then
  echo "error: VM_SSHPASS is set but sshpass is not installed" >&2
  exit 1
fi

# Drop flags that would remove or trim destination files (Ollama sync policy).
sanitize_rsync_extra() {
  rsync_extra_array=()
  [[ -z "${RSYNC_EXTRA:-}" ]] && return 0
  local -a raw
  read -r -a raw <<< "$RSYNC_EXTRA"
  local tok
  for tok in "${raw[@]}"; do
    case "$tok" in
      --delete | --delete-before | --delete-during | --delete-after | --delete-delay | --delete-excluded | --delete-missing-args | --del)
        echo "ollama-sync: ignoring disallowed flag: $tok (destination is additive-only)" >&2
        ;;
      --remove-source-files)
        echo "ollama-sync: ignoring disallowed flag: $tok (destination is additive-only)" >&2
        ;;
      --max-delete | --max-delete=*)
        echo "ollama-sync: ignoring disallowed flag: $tok (destination is additive-only)" >&2
        ;;
      *)
        rsync_extra_array+=("$tok")
        ;;
    esac
  done
}

sanitize_rsync_extra

# --- SSH helpers (supermicro / workstation-side) ---
if [[ -z "${RSYNC_RSH:-}" ]]; then
  if [[ -n "${SSHPASS:-}" ]]; then
    export RSYNC_RSH="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
  else
    export RSYNC_RSH="ssh -o StrictHostKeyChecking=accept-new"
  fi
else
  export RSYNC_RSH
fi

super_ssh=(ssh -o ConnectTimeout=20)
if [[ -n "${SSHPASS:-}" ]]; then
  super_ssh=(sshpass -e ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20)
else
  super_ssh+=( -o BatchMode=yes )
fi

vm_ssh=(ssh -o ConnectTimeout=20)
if [[ -n "${VM_SSHPASS:-}" ]]; then
  vm_ssh=(sshpass -e ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20)
else
  vm_ssh+=( -o BatchMode=yes )
fi

REM_Q="$(printf '%q' "$REMOTE_REL")"
if ! "${super_ssh[@]}" "$REMOTE" "test -d $REM_Q" 2>/dev/null; then
  echo "error: on $REMOTE, expected directory ~/$REMOTE_REL (Ollama data) — not found or SSH failed" >&2
  exit 1
fi

if [[ -n "$RSYNC_BW_KB" && "$RSYNC_BW_KB" != "0" ]]; then
  echo "ollama-sync: rsync --bwlimit=${RSYNC_BW_KB} KiB/s (~$((RSYNC_BW_KB / 1024)) MiB/s)" >&2
else
  echo "ollama-sync: rsync bandwidth unlimited (default for LAN; set OLLAMA_SYNC_BWLIMIT_KB e.g. 4096 to cap)" >&2
fi
echo "ollama-sync: idempotent run — additive only (no --delete* on destination); interrupted transfers resume via rsync --partial" >&2

sync_local() {
  mkdir -p "$LOCAL_DEST" || {
    echo "error: cannot create or write LOCAL_DEST=$LOCAL_DEST" >&2
    exit 1
  }
  "${RSYNC_BASE[@]}" "${rsync_extra_array[@]}" "$REMOTE:~/$REMOTE_REL/" "$LOCAL_DEST/"
  echo "ollama-sync done: $REMOTE:~/$REMOTE_REL/ -> $LOCAL_DEST/"
}

vm_pull() {
  local _bw=""
  if [[ -n "$RSYNC_BW_KB" && "$RSYNC_BW_KB" != "0" ]]; then
    _bw="--bwlimit=$RSYNC_BW_KB"
  fi
  # Quoted tokens expanded here so the archival VM's bash does not glob *partial*.
  local _partial_excludes=""
  if [[ "${OLLAMA_SYNC_INCLUDE_PARTIALS:-0}" != "1" ]]; then
    _partial_excludes="$(printf '%q ' --exclude='models/blobs/*partial*' --exclude='.rsync-partial/')"
  fi
  "${vm_ssh[@]}" "$ARCHIVAL_VM" "bash -s" <<EOF
set -euo pipefail
REMOTE=$(printf '%q' "$REMOTE")
REL=$(printf '%q' "$REMOTE_REL")
DEST=$(printf '%q' "$ARCHIVAL_VM_DEST")
if ! ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=accept-new "\$REMOTE" "test -d \$HOME/\$REL" 2>/dev/null; then
  exit 1
fi
mkdir -p "\$DEST"
# Additive-only: no --delete* (matches ollama-sync policy).
rsync -avh --partial --partial-dir=.rsync-partial --info=progress2 $_bw $_partial_excludes -e "ssh -o StrictHostKeyChecking=accept-new" \\
  "\$REMOTE:~\$REL/" "\$DEST/"
EOF
}

bridge_via_sshfs() {
  if ! command -v sshfs >/dev/null 2>&1; then
    echo "error: sshfs not installed (needed when the VM cannot SSH to supermicro)" >&2
    exit 1
  fi
  local src_path="${OLLAMA_SUPER_PATH:-}"
  if [[ -z "$src_path" ]]; then
    src_path="$("${super_ssh[@]}" "$REMOTE" "printf '%s' \"\$HOME/$REMOTE_REL\"")"
  fi

  OLLAMA_SSHFS_MNT="$(mktemp -d "${TMPDIR:-/tmp}/ollama-sshfs.XXXXXX")"
  cleanup_sshfs() {
    if [[ -n "${OLLAMA_SSHFS_MNT:-}" ]] && [[ -d "${OLLAMA_SSHFS_MNT:-}" ]]; then
      fusermount -u "$OLLAMA_SSHFS_MNT" 2>/dev/null || umount "$OLLAMA_SSHFS_MNT" 2>/dev/null || true
      rmdir "$OLLAMA_SSHFS_MNT" 2>/dev/null || true
    fi
  }
  trap cleanup_sshfs EXIT

  "${vm_ssh[@]}" "$ARCHIVAL_VM" "mkdir -p $(printf '%q' "$ARCHIVAL_VM_DEST")"

  if [[ -n "${SSHPASS:-}" ]]; then
    SSHPASS="$SSHPASS" sshfs -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3 \
      -o StrictHostKeyChecking=accept-new \
      -o ssh_command='sshpass -e ssh -o StrictHostKeyChecking=accept-new' \
      "${REMOTE}:${src_path}" "$OLLAMA_SSHFS_MNT"
  else
    sshfs -o reconnect,ServerAliveInterval=15,ServerAliveCountMax=3 \
      -o StrictHostKeyChecking=accept-new \
      "${REMOTE}:${src_path}" "$OLLAMA_SSHFS_MNT"
  fi

  if [[ -n "${VM_SSHPASS:-}" ]]; then
    RSYNC_RSH_VM="sshpass -e ssh -o StrictHostKeyChecking=accept-new"
    SSHPASS="$VM_SSHPASS" RSYNC_RSH="$RSYNC_RSH_VM" "${RSYNC_BASE[@]}" "${rsync_extra_array[@]}" \
      "$OLLAMA_SSHFS_MNT/" "${ARCHIVAL_VM}:${ARCHIVAL_VM_DEST}/"
  else
    RSYNC_RSH="ssh -o StrictHostKeyChecking=accept-new" "${RSYNC_BASE[@]}" "${rsync_extra_array[@]}" \
      "$OLLAMA_SSHFS_MNT/" "${ARCHIVAL_VM}:${ARCHIVAL_VM_DEST}/"
  fi

  trap - EXIT
  cleanup_sshfs

  echo "ollama-sync done (bridge): $REMOTE:~/$REMOTE_REL/ -> $ARCHIVAL_VM:$ARCHIVAL_VM_DEST/"
}

sync_vm() {
  # Pick rotated destination unless ARCHIVAL_VM_DEST was already set; always emit full scan roots for inventory.
  eval "$(python3 "$REPO/scripts/ollama_archival_rotation.py" prepare --repo "$REPO" \
    ${ARCHIVAL_VM_DEST:+--dest "$ARCHIVAL_VM_DEST"} \
    ${ARCHIVAL_VM_SITE_CYCLE:+--cycle "$ARCHIVAL_VM_SITE_CYCLE"})"
  echo "ollama-sync: this run → disk ${OLLAMA_SYNC_DISK_LABEL:-?}  $ARCHIVAL_VM_DEST" >&2

  "${vm_ssh[@]}" "$ARCHIVAL_VM" "mkdir -p $(printf '%q' "$ARCHIVAL_VM_DEST")"

  if [[ "${OLLAMA_SKIP_VM_PULL:-0}" != 1 ]] && vm_pull; then
    echo "ollama-sync done (vm pull): $REMOTE:~/$REMOTE_REL/ -> $ARCHIVAL_VM:$ARCHIVAL_VM_DEST/"
    return 0
  fi

  echo "note: VM cannot reach supermicro over SSH (or pull failed); using sshfs bridge from this host." >&2
  bridge_via_sshfs
}

case "$SYNC_DEST" in
  local) sync_local ;;
  vm)    sync_vm ;;
  *)
    echo "error: OLLAMA_SYNC_DEST must be vm or local (got $SYNC_DEST)" >&2
    exit 1
    ;;
esac

# Archival VM: drop stray *partial* shards + rsync debris; report manifest↔blob integrity (all cycle roots).
if [[ "${OLLAMA_SYNC_VM_MAINTAIN:-1}" != "0" ]] && [[ "$SYNC_DEST" == "vm" ]] \
  && [[ -f "$REPO/scripts/ollama_archive_vm_maintain.py" ]]; then
  mapfile -t _maint_roots < <(python3 "$REPO/scripts/ollama_archival_rotation.py" print-archive-roots \
    ${ARCHIVAL_VM_SITE_CYCLE:+--cycle "$ARCHIVAL_VM_SITE_CYCLE"})
  if [[ "${#_maint_roots[@]}" -gt 0 ]]; then
    echo "ollama-sync: archival VM maintain (${#_maint_roots[@]} roots): partial cleanup + integrity check" >&2
    if ! cat "$REPO/scripts/ollama_archive_vm_maintain.py" | "${vm_ssh[@]}" "$ARCHIVAL_VM" python3 - "${_maint_roots[@]}"; then
      echo "ollama-sync: warning: archival VM maintain exited non-zero" >&2
    fi
  fi
fi

# Advance rotation only after a successful VM sync that used the rotated picker.
if [[ "$SYNC_DEST" == "vm" ]]; then
  python3 "$REPO/scripts/ollama_archival_rotation.py" advance-after-success --repo "$REPO" \
    --used-dest "$ARCHIVAL_VM_DEST" \
    --used-label "${OLLAMA_SYNC_DISK_LABEL:-}" \
    --advance "${OLLAMA_SYNC_ROTATION_ADVANCE:-0}" \
    ${ARCHIVAL_VM_SITE_CYCLE:+--cycle "$ARCHIVAL_VM_SITE_CYCLE"} || true
fi

# Refresh docs/data/ollama-vm-models-inventory.yaml (all archival roots → model → disk map).
if [[ "${OLLAMA_SYNC_UPDATE_INVENTORY:-1}" != "0" ]] && command -v uv >/dev/null 2>&1 \
  && [[ -f "$REPO/scripts/update_ollama_vm_inventory.py" ]]; then
  _inv_label="${OLLAMA_VM_LOCAL_DISK_LABEL:-local}"
  if [[ "$SYNC_DEST" == "local" ]]; then
    # shellcheck disable=SC2086
    if (cd "$REPO" && uv run python scripts/update_ollama_vm_inventory.py \
      --root "${_inv_label}=${LOCAL_DEST}" ${OLLAMA_VM_INVENTORY_EXTRA:-}); then
      :
    else
      echo "ollama-sync: warning: Ollama VM inventory update failed (see update_ollama_vm_inventory.py)" >&2
    fi
  else
    # shellcheck disable=SC2086
    if (cd "$REPO" && uv run python scripts/update_ollama_vm_inventory.py --ssh "$ARCHIVAL_VM" \
      ${OLLAMA_VM_INVENTORY_ROOT_FLAGS:-} ${OLLAMA_VM_INVENTORY_EXTRA:-}); then
      :
    else
      echo "ollama-sync: warning: Ollama VM inventory update failed (see update_ollama_vm_inventory.py)" >&2
    fi
  fi
fi

if [[ "${OLLAMA_SYNC_UPDATE_INVENTORY:-1}" != "0" ]] && command -v uv >/dev/null 2>&1 \
  && [[ -f "$REPO/scripts/generate_ollama_archival_map.py" ]]; then
  if (cd "$REPO" && uv run python scripts/generate_ollama_archival_map.py); then
    :
  else
    echo "ollama-sync: warning: generate_ollama_archival_map.py failed" >&2
  fi
fi
