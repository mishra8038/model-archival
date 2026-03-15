# Model Archival — Documentation

This folder describes the **model-archival** repository: its mission, the sub-projects in each directory, the configuration we have decided upon, the artifacts we archive, and how they are distributed across the physical disks.

---

## Mission and objectives

**Mission:** Insurance-first archival of open-source AI artifacts so that models and tooling survive deletion, restriction, or regulatory takedown. We preserve weights, checksums, and source code on local storage with cryptographic verification and resumable, unattended operation.

**Objectives:**

- **Weights:** Download full open-source LLM/LRM weights from Hugging Face (raw BF16/FP16 and selected GGUF) to a fleet of local HDDs, with SHA-256 verification and structured manifests.
- **Checksums:** Record SHA-256 LFS fingerprints for every major model release without downloading weights, providing a lightweight audit trail and integrity reference.
- **Source code:** Snapshot critical open-source AI projects (inference engines, training tools, agents, UIs) from GitHub so they survive potential takedowns.
- **Tooling:** Mirror IDE assistants, agent frameworks, and serving backends listed in the registry as bare git repos on the metadata drive.
- **Safety:** Never write model data to the root SSD; use atomic writes for state and reports; always stop gracefully before reboot to avoid filesystem corruption.

---

## Documentation index

| Document | Contents |
|----------|----------|
| [PROJECTS.md](PROJECTS.md) | Summary of each project in its directory (local, fingerprints, code-archival, gdrive-archival). |
| [CONFIGURATION.md](CONFIGURATION.md) | Decided configuration: registry layout, drives, tiers, priorities, tooling list. |
| [ARTIFACTS.md](ARTIFACTS.md) | What we archive: model weights (tiers A–G), checksums, code snapshots, tooling mirrors. |
| [DISKS-AND-DISTRIBUTION.md](DISKS-AND-DISTRIBUTION.md) | Physical disk layout, roles, and distribution of artifacts per drive. |
| [CHAT-ARCHIVE.md](CHAT-ARCHIVE.md) | Index of Cursor agent chat transcripts (date, title, UUID) and how to refresh it. |

---

## Repository layout (high level)

| Directory | Purpose |
|-----------|---------|
| `local/` | **Weight downloader** — Python archiver; pulls full model weights from Hugging Face to local HDDs via aria2c. |
| `fingerprints/` | **Checksum crawler** — records SHA-256 LFS fingerprints and metadata for major model releases without downloading weights. |
| `code-archival/` | **Source archiver** — snapshots open-source AI project releases (inference, training, agents, UIs) from GitHub. |
| `gdrive-archival/` | **Cloud backup** — backs up key configs, metadata, and selected model IDs to Google Drive via rclone. |

For per-project details, entry points, and file locations, see [PROJECTS.md](PROJECTS.md).
