"""Data models and registry loader."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class ModelEntry:
    id: str
    hf_repo: str
    tier: str                        # A | B | C | D
    drive: str                       # d1 .. d5
    priority: int                    # 1 = token-free, 2 = gated
    licence: str
    requires_auth: bool
    commit_sha: Optional[str] = None
    quant_levels: list[str] = field(default_factory=list)
    parent_model: Optional[str] = None
    method: Optional[str] = None
    notes: Optional[str] = None

    # Derived: set after registry is loaded alongside drive config
    drive_path: Optional[Path] = None

    @property
    def is_gguf(self) -> bool:
        return self.tier == "C" or bool(self.quant_levels)

    @property
    def content_subdir(self) -> str:
        """Top-level content directory name on the assigned drive."""
        if self.tier == "C":
            return "quantized"
        if self.tier == "D":
            return "uncensored"
        return "raw"

    @property
    def model_dir(self) -> Optional[Path]:
        if self.drive_path is None or self.commit_sha is None:
            return None
        org, name = self.hf_repo.split("/", 1)
        return self.drive_path / self.content_subdir / org / name / self.commit_sha

    @property
    def display_name(self) -> str:
        return self.hf_repo.split("/")[-1]


@dataclass
class DriveConfig:
    label: str          # d1 .. d5
    mount_point: Path
    role: str
    tmp_dir: Optional[Path] = None   # override scratch dir (defaults to mount_point/.tmp)


@dataclass
class Registry:
    models: list[ModelEntry]
    drives: dict[str, DriveConfig]

    def get(self, model_id: str) -> Optional[ModelEntry]:
        for m in self.models:
            if m.id == model_id:
                return m
        return None

    def by_priority(self) -> list[ModelEntry]:
        """Return models sorted: priority asc, then size desc (largest first within tier)."""
        return sorted(self.models, key=lambda m: (m.priority, m.id))

    def gated(self) -> list[ModelEntry]:
        return [m for m in self.models if m.requires_auth]

    def token_free(self) -> list[ModelEntry]:
        return [m for m in self.models if not m.requires_auth]


def load_registry(registry_path: Path, drives_path: Optional[Path] = None) -> Registry:
    with registry_path.open() as f:
        data = yaml.safe_load(f)

    drives: dict[str, DriveConfig] = {}
    if drives_path and drives_path.exists():
        with drives_path.open() as f:
            drives_data = yaml.safe_load(f) or {}
        for label, cfg in drives_data.items():
            raw_tmp = cfg.get("tmp_dir")
            drives[label] = DriveConfig(
                label=label,
                mount_point=Path(cfg["mount_point"]),
                role=cfg.get("role", ""),
                tmp_dir=Path(raw_tmp) if raw_tmp else None,
            )

    models = []
    for raw in data.get("models", []):
        entry = ModelEntry(
            id=raw["id"],
            hf_repo=raw["hf_repo"],
            tier=raw["tier"],
            drive=raw["drive"],
            priority=raw.get("priority", 1),
            licence=raw.get("licence", "unknown"),
            requires_auth=raw.get("requires_auth", False),
            commit_sha=raw.get("commit_sha"),
            quant_levels=raw.get("quant_levels", []),
            parent_model=raw.get("parent_model"),
            method=raw.get("method"),
            notes=raw.get("notes"),
        )
        if entry.drive in drives:
            entry.drive_path = drives[entry.drive].mount_point
        models.append(entry)

    return Registry(models=models, drives=drives)


def save_registry(registry: Registry, registry_path: Path) -> None:
    """Write registry back to YAML, preserving all fields."""
    data: dict = {"models": []}
    for m in registry.models:
        entry: dict = {
            "id": m.id,
            "hf_repo": m.hf_repo,
            "tier": m.tier,
            "drive": m.drive,
            "priority": m.priority,
            "licence": m.licence,
            "requires_auth": m.requires_auth,
        }
        if m.commit_sha is not None:
            entry["commit_sha"] = m.commit_sha
        else:
            entry["commit_sha"] = None
        if m.quant_levels:
            entry["quant_levels"] = m.quant_levels
        if m.parent_model:
            entry["parent_model"] = m.parent_model
        if m.method:
            entry["method"] = m.method
        if m.notes:
            entry["notes"] = m.notes
        data["models"].append(entry)

    tmp = registry_path.with_suffix(".yaml.tmp")
    with tmp.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    tmp.replace(registry_path)
