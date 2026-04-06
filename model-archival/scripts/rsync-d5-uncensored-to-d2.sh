#!/usr/bin/env bash
#
# Incremental rsync: d5/uncensored → d2/uncensored (archival VM).
#
# Transfers only what needs updating: by default rsync skips files when size and
# modification time match the destination (no full re-read). Re-runs are cheap.
#
# Policy:
#   - Additive / archive-safe: no --delete* on the destination; extra trees on d2 stay.
#   - Resumable: --partial + --partial-dir=.rsync-partial under d2/uncensored.
#   - Optional second phase: UNCSYNC_REMOVE_SOURCE=1 uses --remove-source-files so each
#     file is deleted from d5 only after it is present on d2 (cross-filesystem "move").
#
# Run on the archival VM (paths under /mnt/models), or from another host:
#   ssh x@192.168.8.65 'bash -s' < model-archival/scripts/rsync-d5-uncensored-to-d2.sh
#
# Env:
#   MODELS_MOUNT     default /mnt/models
#   UNCENSORED_SRC   default $MODELS_MOUNT/d5/uncensored
#   UNCENSORED_DST   default $MODELS_MOUNT/d2/uncensored
#   RSYNC_EXTRA      extra rsync args (--dry-run, --itemize-changes, …); --delete* stripped
#   UNCSYNC_CHECKSUM if 1, add --checksum (compare whole file; slow, use if mtimes untrusted)
#   UNCSYNC_REMOVE_SOURCE if 1, add --remove-source-files (deletes successfully copied files from d5)
#
set -euo pipefail

MODELS_MOUNT="${MODELS_MOUNT:-/mnt/models}"
SRC="${UNCENSORED_SRC:-$MODELS_MOUNT/d5/uncensored}"
DST="${UNCENSORED_DST:-$MODELS_MOUNT/d2/uncensored}"

declare -a RSYNC_EXTRA_SAFE=()
if [[ -n "${RSYNC_EXTRA:-}" ]]; then
  # shellcheck disable=SC2206
  read -r -a _rsync_extra_words <<< "$RSYNC_EXTRA"
  for a in "${_rsync_extra_words[@]}"; do
    case "$a" in
      --delete|--delete-before|--delete-during|--delete-after|--delete-excluded|--remove-all-files)
        echo "rsync-d5-uncensored-to-d2: refusing destructive flag: $a" >&2
        exit 2
        ;;
      *) RSYNC_EXTRA_SAFE+=("$a") ;;
    esac
  done
fi

RSYNC=(rsync -aHh --partial --partial-dir=.rsync-partial --info=progress2)
if [[ "${UNCSYNC_CHECKSUM:-0}" == "1" ]]; then
  RSYNC+=(--checksum)
fi
if [[ "${UNCSYNC_REMOVE_SOURCE:-0}" == "1" ]]; then
  RSYNC+=(--remove-source-files)
fi

if [[ ! -d "$SRC" ]]; then
  echo "error: source missing or not a directory: $SRC" >&2
  exit 1
fi
mkdir -p "$DST"

echo "rsync-d5-uncensored-to-d2: $SRC/ → $DST/" >&2
if [[ "${UNCSYNC_CHECKSUM:-0}" == "1" ]]; then
  echo "  (using --checksum: full-file comparison)" >&2
else
  echo "  (default quick check: size + mtime; set UNCSYNC_CHECKSUM=1 to force content compare)" >&2
fi
if [[ "${UNCSYNC_REMOVE_SOURCE:-0}" == "1" ]]; then
  echo "  (--remove-source-files: clearing successfully copied files from source)" >&2
fi

exec "${RSYNC[@]}" "${RSYNC_EXTRA_SAFE[@]}" "$SRC/" "$DST/"
