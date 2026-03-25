# multidisk-downloader

Requirements and architecture documentation for a split transfer system:

- `selector` (what to move, when, where)
- `downloader` (pull bytes from source to local disks)
- `uploader` (push local artifacts to remote storage)

This folder is documentation-first. It defines contracts and boundaries so model selection logic stays completely separate from transfer execution logic.

## Documents

- `REQUIREMENTS.md`: functional + non-functional requirements for downloader/uploader based on current repository usage patterns.
- `ARCHITECTURE-BOUNDARIES.md`: strict module boundaries and interface contracts that prevent selector logic from leaking into transfer workers.

## Design principle

Selection and transfer are independent subsystems:

- Selection may read registries, policies, priorities, and quotas.
- Downloader/uploader must execute transfer plans only.
- Transfer workers must not make selection decisions or query selection registries directly.
