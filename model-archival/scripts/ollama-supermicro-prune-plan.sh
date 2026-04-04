#!/usr/bin/env bash
#
# Plan Ollama removals on supermicro AFTER blobs are synced to the archival VM.
#
# Policy (operator-approved): KEEP only
#   - **Gemma 4** (all quants: MoE, dense, E2B/E4B edge — manifest path `gemma4/*`)
#   - **Qwen Coder** line only (`qwen2.5-coder/*`, `qwen3*coder*/*` — not base Qwen chat / R1)
#
# Everything else is PRUNE (suggested `ollama rm`) once the same tag exists on the VM cache.
#
# Usage:
#   # On supermicro — list local manifests:
#   find ~/.ollama/models/manifests/registry.ollama.ai/library -type f | sed 's|.*/library/||' | sort > /tmp/super.txt
#   # On VM — list synced cache:
#   find /mnt/models/d5/supermicro/models/manifests/registry.ollama.ai/library -type f | sed 's|.*/library/||' | sort > /tmp/vm.txt
#   # On workstation — copy both files here, then:
#   SUPER=/tmp/super.txt VM=/tmp/vm.txt DRY_RUN=1 bash scripts/ollama-supermicro-prune-plan.sh
#
#   DRY_RUN=0 prints ollama rm commands (run on supermicro only after verifying VM byte-complete).
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO"

SUPER="${SUPER:-}"
VM="${VM:-}"
DRY_RUN="${DRY_RUN:-1}"

keep_tag() {
  local rel="$1"
  [[ "$rel" == gemma4/* ]] && return 0
  [[ "$rel" == qwen2.5-coder/* ]] && return 0
  [[ "$rel" == qwen3*coder*/* ]] && return 0
  return 1
}

if [[ -z "$SUPER" || -z "$VM" ]]; then
  echo "Set SUPER and VM to manifest list files (relative paths under registry.ollama.ai/library)." >&2
  echo "Example: SUPER=/tmp/super.txt VM=/tmp/vm.txt DRY_RUN=1 $0" >&2
  exit 1
fi

if [[ ! -f "$SUPER" || ! -f "$VM" ]]; then
  echo "error: missing file SUPER=$SUPER VM=$VM" >&2
  exit 1
fi

mapfile -t vm_tags < <(sort -u "$VM")
declare -A on_vm=()
for t in "${vm_tags[@]}"; do
  on_vm["$t"]=1
done

echo "# ollama-supermicro-prune-plan ($(date -u +%Y-%m-%dT%H:%MZ))"
echo "## KEEP on supermicro (Gemma 4 full line + Qwen Coder line only)"
echo
while IFS= read -r rel || [[ -n "${rel:-}" ]]; do
  [[ -z "$rel" ]] && continue
  if keep_tag "$rel"; then
    echo "KEEP $rel"
  fi
done < <(sort -u "$SUPER")
echo
echo "## PRUNE candidates (on super, also present on VM, not in KEEP policy)"
echo
while IFS= read -r rel || [[ -n "${rel:-}" ]]; do
  [[ -z "$rel" ]] && continue
  if keep_tag "$rel"; then
    continue
  fi
  if [[ -n "${on_vm[$rel]:-}" ]]; then
    m="${rel%%/*}"
    t="${rel#*/}"
    echo "PRUNE $rel  ->  ollama rm ${m}:${t}"
  fi
done < <(sort -u "$SUPER")

echo
echo "## PRUNE blocked (on super but NOT yet on VM — do not delete)"
while IFS= read -r rel || [[ -n "${rel:-}" ]]; do
  [[ -z "$rel" ]] && continue
  if keep_tag "$rel"; then
    continue
  fi
  if [[ -z "${on_vm[$rel]:-}" ]]; then
    echo "WAIT $rel"
  fi
done < <(sort -u "$SUPER")

if [[ "$DRY_RUN" == "0" ]]; then
  echo
  echo "## Executing ollama rm on this host (DRY_RUN=0)"
  while IFS= read -r rel || [[ -n "${rel:-}" ]]; do
    [[ -z "$rel" ]] && continue
    keep_tag "$rel" && continue
    [[ -z "${on_vm[$rel]:-}" ]] && continue
    m="${rel%%/*}"
    t="${rel#*/}"
    ollama rm "${m}:${t}" || echo "warn: ollama rm failed: ${m}:${t}" >&2
  done < <(sort -u "$SUPER")
fi
