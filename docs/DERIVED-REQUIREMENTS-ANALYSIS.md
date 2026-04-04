# Derived Requirements Analysis

**Date:** 2026-04-02  
**Scope:** Derive the real requirements of this repository from:

- the current monorepo structure,
- the project docs and architecture,
- the curated transcript summary in `docs/AGENT_TRANSCRIPT_SUMMARY.md`,
- the chat index in `docs/CHAT-ARCHIVE.md`,
- sampled raw Cursor transcript first prompts from `~/.cursor/projects/home-x-z-dev-model-archival-model-archival/agent-transcripts/`.

---

## 1. Executive summary

The project started as a **Hugging Face model downloader**, but actual usage shows it became a broader **AI artifact preservation and archive operations system**.

The most important recurring human-in-the-loop activities were not “download bytes” tasks. They were:

1. **Choosing what to archive next**
2. **Starting, stopping, resuming, and reconfiguring long-running jobs**
3. **Synthesizing status from many moving parts**
4. **Managing storage pressure and drive placement**
5. **Selecting and executing Google Drive uploads**
6. **Extending scope to adjacent preservation tasks** such as code archival, GitHub snapshots, fingerprints, and metadata capture
7. **Keeping documentation, inventories, and project structure coherent**

This strongly suggests the core product is not a downloader. It is an **unattended archival control plane** with multiple transfer backends and multiple artifact types.

---

## 2. What the transcripts say the project really is

Across the sampled Cursor chats, the recurring requests were:

- “connect to VM and start the model archival”
- “show me our gdrive upload plan”
- “are there any download / uploads running on the vm?”
- “update progress”
- “update status”
- “stop writing to d5 going forward”
- “start download ... use the speciality registry”
- “complete map of models on each drive”
- “verify archived repositories”
- “download Ollama model list and fingerprints”
- “download a snapshot of my personal github projects and upload them to gdrive”
- “hunt for empty space on disk drives”
- “create a collection of the smallest models on the leaderboards ... compare with what we have”

These prompts indicate the user needed chat mainly for:

- operational orchestration,
- policy decisions,
- status consolidation,
- archive curation,
- recovery and adaptation,
- scope expansion into new archival domains.

The transcripts do **not** suggest the main bottleneck is raw transfer implementation. The bottleneck is the lack of a fully autonomous planner/operator/reconciler around the transfer engines.

---

## 3. Derived product definition

The real product can be stated as:

> A policy-driven, unattended archival system that selects, downloads, verifies, inventories, mirrors, and backs up important AI-related artifacts across multiple local disks and remote storage targets, while preserving provenance and minimizing babysitting.

That product contains at least six distinct concerns:

1. **Selection / curation**
2. **Transfer execution**
3. **Verification / integrity**
4. **Inventory / reporting**
5. **Backup / replication**
6. **Operations / orchestration**

---

## 4. Most important activities you used chat for

### A. Operations copilot

This was the largest pattern.

Examples:

- start or restart archival runs
- check whether jobs are running
- change bandwidth caps
- change target registry
- stop using a specific drive
- inspect progress and summarize current status

**Derived requirement:** the system must expose a first-class autonomous operations layer, not just CLIs.

### B. Selection and prioritization

Examples:

- which models to archive
- should a new family be added
- compare leaderboards against what is already archived
- create specialized or smallest-self-hostable subsets
- separate main, legacy, specialist, uncensored, quantized priorities

**Derived requirement:** model selection is a planner problem and must remain separate from transfer execution.

### C. Inventory and reporting

Examples:

- complete map of models on each drive
- archived projects lists
- metadata and checksums rollups
- progress reports
- upload plans

**Derived requirement:** status must be derivable automatically from the filesystem + state + registries, without chat-based manual synthesis.

### D. Storage and recovery management

Examples:

- hunt for free space
- identify `.tmp` reclaim candidates
- move infra away from D5
- reconcile partial/incomplete work

**Derived requirement:** storage pressure management must become an automated policy-and-reconciliation subsystem.

### E. Backup curation and remote replication

Examples:

- upload chosen trees to Google Drive
- choose smaller models for the cloud budget
- upload arbitrary folders
- snapshot GitHub repos and push them to Drive

**Derived requirement:** backup is its own project domain, with explicit budget/policy logic and reusable remote sinks.

### F. Archive surface expansion

Examples:

- code archival
- GitHub-owned repo archival
- Ollama metadata/fingerprints
- Graphcore tarballs and docker checksums
- full software stack archival

**Derived requirement:** the architecture must support multiple artifact classes, not only Hugging Face model weights.

---

## 5. Core derived requirements

### 5.1 Functional requirements

1. The system must support **artifact-type-specific selectors** that emit versioned execution plans.
2. The system must support **unattended execution** for long-running jobs across reboots, SSH drops, and transient failures.
3. The system must support **resumable, idempotent transfer** for both local archival and remote backup.
4. The system must support **policy-based drive placement**, including “avoid drive X”, scratch policy, and control-plane/data-plane separation.
5. The system must maintain **authoritative run state**, **append-only event logs**, and **derived human-readable dashboards**.
6. The system must support **automated inventory generation** for models, code archives, checksums, fingerprints, and upload coverage.
7. The system must support **integrity verification** before completion and before remote upload.
8. The system must support **budget-aware backup planning** for constrained remotes such as Google Drive.
9. The system must support **failure classification** and distinct handling for auth, missing upstream, corruption, disk pressure, and transient network failures.
10. The system must support **incremental archive expansion** to new artifact classes without rewriting the control plane.

### 5.2 Operational requirements

1. No babysitting should be required for normal runs.
2. Human intervention should be needed only for:
   - new policy decisions,
   - credential acquisition,
   - hardware changes,
   - genuinely ambiguous failures.
3. The system must auto-generate operator digests:
   - what is running,
   - what completed,
   - what failed and why,
   - what needs attention next.
4. The system must be able to **self-reconcile** after restart:
   - re-read state,
   - rediscover partials,
   - refresh plans,
   - continue safely.

### 5.3 Architectural requirements

1. Selection must remain separate from transfer workers.
2. Transfer workers must be generic across artifact types where possible.
3. Inventory/reporting must be derived, not hand-maintained.
4. Remote backup must be treated as a separate stage from local archival.
5. Shared concerns such as state, integrity, events, retries, and storage policy should live in common libraries.

---

## 6. What should be automated next

### Highest-value automation targets

#### 1. Autonomous status synthesis

Today chat is repeatedly used for “update progress” and “update status”.

Automate with:

- one canonical `ops status` command,
- machine-readable health JSON,
- markdown summary,
- “attention needed” list,
- per-drive and per-pipeline views.

This alone eliminates a large fraction of chat usage.

#### 2. Autonomous planning and dispatch

Today chat is used to decide:

- which registry to run,
- which drive slice to target,
- which models to upload,
- what to deprioritize or defer.

Automate with:

- a planner that emits executable plans,
- policy files for caps, inclusion rules, and budget,
- override files for emergency changes.

#### 3. Autonomous restart and reconciliation

Today chat is used for:

- restart after interruptions,
- inspecting whether work is still running,
- cleaning up weird partial states.

Automate with:

- a supervisor,
- startup reconciliation,
- heartbeat-based liveness checks,
- stalled-job detection,
- automatic safe restart when possible.

#### 4. Autonomous storage pressure management

Today chat is used to hunt disk space and decide when to avoid a drive.

Automate with:

- free-space thresholds,
- reclaimable `.tmp` audits,
- “quarantine this drive” toggles,
- planner-level placement changes,
- pre-run “can this plan fit?” admission control.

#### 5. Autonomous backup candidate selection

Today chat is used to ask “what should go to GDrive?”

Automate with:

- a backup planner using:
  - size budget,
  - urgency/risk,
  - completeness,
  - uniqueness,
  - replacement cost,
  - existing remote coverage.

#### 6. Autonomous curation refresh

Today chat is used to compare leaderboards and curated model lists to current holdings.

Automate with:

- a periodic selector refresh,
- change reports for newly important models,
- “candidate additions” queues,
- approval gates only for policy-sensitive additions.

---

## 7. Best underlying logic for unattended operation

The right strategy is not “more shell scripts”. It is a **closed-loop archive controller**.

### Recommended control loop

1. **Observe**
   - ingest registry, inventory, run state, remote state, disk state, fingerprints, and upstream metadata
2. **Plan**
   - emit a versioned action plan with download, verify, replicate, upload, or defer actions
3. **Execute**
   - workers consume the plan only
4. **Verify**
   - integrity checks and parity checks
5. **Reconcile**
   - compare desired state vs actual state
6. **Adapt**
   - replan on disk pressure, new upstream availability, failures, or completed work
7. **Report**
   - produce operator digest and machine-readable health outputs

### Decision strategy

Use a policy engine with weighted scoring, not ad hoc prompts.

For every candidate artifact, compute a score from:

- preservation risk
- importance / capability
- uniqueness
- size
- local storage fit
- remote backup suitability
- auth availability
- estimated download cost
- replacement difficulty
- current completion state

This score should drive:

- local archival order,
- backup order,
- defer decisions,
- drive placement suggestions.

### Important design principle

The system should be **approval-light but policy-heavy**:

- humans define policy,
- planners make routine decisions,
- workers execute safely,
- reports surface exceptions.

That is how you get “unattended, no babysitting”.

---

## 8. Suggested project decomposition

The current repo already points toward a healthier split.

### Recommended top-level projects

#### 1. `archive-control-plane`

Purpose:

- policy engine
- selectors/planners
- run orchestration
- state reconciliation
- operator reports

This becomes the brain.

#### 2. `artifact-transfer-engine`

Purpose:

- generic transfer workers
- resumable download/upload execution
- retry logic
- verification hooks
- event/state primitives

This becomes the muscle.

#### 3. `model-archive`

Purpose:

- Hugging Face model-specific selection logic
- registry authoring
- artifact-specific verification/provenance
- gated/auth-aware handling

This becomes one plugin or domain package.

#### 4. `remote-backup`

Purpose:

- Google Drive and future remotes
- backup budgeting
- remote parity tracking
- remote inventory cache

This should be independent from model-specific logic.

#### 5. `code-archive`

Purpose:

- GitHub repos
- release tarballs
- code mirrors
- owned repo snapshots

This is already becoming its own cohesive project.

#### 6. `artifact-fingerprints`

Purpose:

- lightweight metadata/fingerprint harvesting
- leaderboard snapshots
- Ollama metadata
- source-of-truth verification references

This should remain separate from byte-heavy archival.

#### 7. `software-stack-archive`

Purpose:

- full-stack environment archival
- OS/CUDA/toolchain/wheelhouse artifacts

This is not the same product as model archival and should stay separate.

### Cross-cutting shared libraries

These should be reused across projects:

- state I/O
- event logging
- manifests and checksums
- inventory schemas
- plan schema
- retry/error taxonomy
- disk policy helpers
- report rendering

---

## 9. Proposed target architecture

### Control-plane components

- `selector-models`
- `selector-backups`
- `selector-code`
- `planner`
- `reconciler`
- `policy-engine`
- `ops-supervisor`
- `reporter`

### Execution-plane components

- `download-worker-hf`
- `upload-worker-rclone`
- `snapshot-worker-git`
- `fingerprint-worker`
- `verify-worker`

### Data contracts

All selectors should emit a shared `plan.json` shape with:

- `plan_version`
- `artifact_type`
- `item_id`
- `action`
- `source`
- `destination`
- `verification_policy`
- `priority_score`
- `budget_class`
- `retry_policy`
- `policy_context`

---

## 10. Additional requirements worth adding now

1. **Supervisor mode**
   - background daemon or service that restarts failed tasks and regenerates status.
2. **Attention queue**
   - explicit queue of items requiring humans: auth needed, disk unavailable, ambiguous mismatch, upstream removed.
3. **Planner explainability**
   - every plan item should say why it was selected or deferred.
4. **Remote inventory parity**
   - maintain a local cached model of what is already on Drive or other remotes.
5. **Storage forecast**
   - estimate time-to-full and space-to-complete before runs start.
6. **Stall detection**
   - detect zero-progress jobs and classify likely causes.
7. **Policy snapshots**
   - store the exact policy/config used for each run.
8. **Automatic daily digest**
   - one summary file with completions, failures, uploads, remaining high-priority items, and storage risk.
9. **Artifact lineage**
   - connect local archive, checksum/fingerprint record, and remote backup status for each item.
10. **Credential readiness checks**
   - proactively report missing or expired HF, GitHub, or rclone credentials before a run.
11. **Drive quarantine mode**
   - mark a drive read-only or no-new-writes at policy level without code edits.
12. **Compaction / cleanup rules**
   - automated safe cleanup for reclaimable scratch and obsolete transient artifacts.
13. **Budgeted remote tiers**
   - e.g. “must-backup”, “nice-to-backup”, “local-only”.
14. **Artifact class plugins**
   - models, code repos, GitHub-owned repos, Ollama metadata, software stack archives should plug into the same control plane.
15. **Approval gates for major scope changes**
   - frontier model addition, giant artifact admission, or new remote budget consumption should require explicit approval.

---

## 11. What should remain manual

Not everything should be automated.

Keep these human-controlled:

- preservation policy changes
- legal/licensing judgment
- deciding what counts as “important”
- adding new artifact classes
- one-time infrastructure surgery
- destructive cleanup outside predefined safe rules

Everything else should trend toward autonomous execution.

---

## 12. Recommended next step

The best next move is:

1. treat `multidisk-downloader/` as the seed of the **generic transfer-engine spec**,
2. define a separate **control-plane spec** for planning/reconciliation/reporting,
3. make `model-archival/`, `gdrive-archival/`, `code-archival/`, `gh-archival/`, `fingerprints/`, and `full-stack/` into domain packages that plug into that control plane.

This preserves what already works while making the unattended future achievable.

---

## 13. Bottom line

This repository is evolving toward a **general-purpose archival operations platform for AI artifacts**.

The most important lesson from the transcripts is:

> the hard part is not downloading; the hard part is deciding, coordinating, recovering, verifying, and reporting without constant operator attention.

That should become the design center of the next version.
