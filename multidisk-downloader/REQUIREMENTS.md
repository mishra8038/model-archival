# Requirements - multidisk downloader/uploader

## 1) Usage pattern analysis (derived from current repo behavior)

Observed operating pattern in this repository:

- Long-running unattended jobs via shell wrappers and screen sessions.
- Multi-disk local topology with explicit drive roles (large models, quantized models, metadata/control plane).
- Resumable transfer expectation across interruptions/restarts.
- Safety-first operations: upload-only cloud sync, no destructive remote commands.
- Strong integrity controls: manifests, checksums, verification before/after transfer.
- Persistent run state and human-readable status dashboards.
- Token-gated source repositories and license-gated failure handling.
- Throughput-aware scheduling and explicit bandwidth capping.

The requirements below formalize these behaviors for a standalone downloader/uploader software design.

---

## 2) Scope

In scope:

- Requirements for `downloader` and `uploader` transfer engines.
- Contracts between transfer engines and a separate `selector/planner`.
- Operational, safety, and verification requirements.

Out of scope:

- Curation policy for which models are "important".
- Registry authoring workflows and model ranking heuristics.
- End-user UI polish beyond required status/report outputs.

---

## 3) Hard architectural requirement: separation of concerns

R-SEP-1: A dedicated Selector/Planner subsystem must produce transfer plans.

R-SEP-2: Downloader and uploader must only consume transfer plans and execute them.

R-SEP-3: Downloader/uploader must not read model registries directly for decision making.

R-SEP-4: Downloader/uploader must not reprioritize, substitute, or auto-select new models.

R-SEP-5: Transfer plan schema must be versioned and validated before execution.

R-SEP-6: Policy changes (priority, tier, include/exclude) must be handled by selector-only updates, with no transfer engine code changes required.

---

## 4) Downloader functional requirements

R-DL-1: Support resumable downloads for large multi-file repositories.

R-DL-2: Persist per-item state (`pending`, `in_progress`, `complete`, `failed`, `skipped`) in an atomic-write state file.

R-DL-3: Support per-drive concurrency limits and global concurrency limits.

R-DL-4: Support throughput-aware admission control (do not start more items if projected per-item throughput drops below configured floor).

R-DL-5: Support a global bandwidth cap applied at transfer layer.

R-DL-6: Use temporary scratch paths on designated data drives, not on root/system disk.

R-DL-7: Refresh expiring source URLs/tokens before each transfer attempt when required by source backend.

R-DL-8: Distinguish transient errors (retryable) from auth/license errors (fail fast, no retry loop).

R-DL-9: Verify downloaded artifacts against expected hashes/manifests before marking complete.

R-DL-10: On checksum mismatch, mark item failed, delete corrupt target + stale transfer control artifacts, and retry from clean state if retry policy allows.

R-DL-11: Support clean shutdown on SIGTERM/SIGINT, persisting consistent state.

R-DL-12: Support plan override reload points (for selector-provided priority updates) between items, not mid-item.

---

## 5) Uploader functional requirements

R-UP-1: Upload mode must be copy-only (merge/resume semantics), never delete remote data.

R-UP-2: Disallow destructive remote operations (`sync` with deletions, purge, delete flags) in default and normal modes.

R-UP-3: Support idempotent re-runs after interruptions.

R-UP-4: Support upload root mapping from local paths to remote destination prefixes.

R-UP-5: Support pre-upload local integrity checks (manifest/hash verification) and skip invalid model directories.

R-UP-6: Track successful uploads in a durable local tracker to avoid unnecessary re-uploads.

R-UP-7: For tracker-skipped entries, optionally verify remote parity (checksum check) before skipping.

R-UP-8: Produce explicit reports for skipped/failed items and verification failures.

R-UP-9: Ensure uploader subprocesses always use explicit configured remote credentials/config path.

R-UP-10: Support controlled parallelism and bandwidth limit settings for remote upload backend.

---

## 6) Shared transfer-engine requirements

R-SH-1: Atomic file writes for state, status, and report artifacts (`.tmp` then rename).

R-SH-2: Strong observability: machine-readable state + human-readable status markdown.

R-SH-3: Periodic status refresh with overall progress, active items, throughput, and ETA estimate (when confidence is acceptable).

R-SH-4: Append-only event logging with timestamps for start/complete/fail/skip actions.

R-SH-5: Dry-run mode that validates config, plan schema, mount availability, and auth without mutating transfer targets.

R-SH-6: Preflight checks for drive mounts, available free space, binaries/tools, and source/remote auth readiness.

R-SH-7: Per-item provenance metadata output (source repo/path, commit/revision pin, hash info, transfer timestamp).

R-SH-8: Post-transfer archive/index sync hooks configurable per deployment.

---

## 7) Plan interface requirements (selector -> transfer)

R-IF-1: Transfer plan must include immutable item identifier, source reference, destination drive/path, and verification policy.

R-IF-2: Transfer plan must include execution hints only (priority order, max retries, bandwidth class), not selector internals.

R-IF-3: Transfer engines must reject malformed or unknown plan versions.

R-IF-4: Transfer engines must process only items present in plan; no implicit discovery from filesystem or registries.

R-IF-5: Plan updates during a run must be explicit (new plan file version or override file) and auditable.

---

## 8) Non-functional requirements

R-NF-1: Reliability over peak speed; avoid behavior that risks corruption.

R-NF-2: Restart safety across process crashes and host reboot events.

R-NF-3: Deterministic behavior from fixed plan + fixed config.

R-NF-4: Low operational surprise: conservative defaults, explicit opt-in for aggressive modes.

R-NF-5: Security hygiene: least-privilege credentials, no token leakage in logs.

R-NF-6: Portability across Linux hosts with heterogeneous storage layouts.

R-NF-7: Backward compatibility for persisted state schema (with migration path for breaking changes).

---

## 9) Acceptance criteria (minimum)

- AC-1: Given a valid plan, downloader completes or fails each item with persisted terminal status and restart-safe resume.
- AC-2: Mid-run interruption and restart does not re-download already verified artifacts.
- AC-3: Uploader never issues remote delete operations in standard workflows.
- AC-4: Any model selection change can be made in selector output without modifying downloader/uploader code.
- AC-5: Corrupt local artifacts are detected before "complete/uploaded" status is emitted.
- AC-6: Status/report artifacts remain readable and internally consistent under concurrent workers.
