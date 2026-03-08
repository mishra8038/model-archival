"""Data models loaded from config/registry.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class ModelEntry:
    hf_repo: str
    family: str
    tier: str                       # A / B / C / D
    importance: str                 # critical / high / medium
    licence: str
    requires_auth: bool
    notes: str = ""
    parent_model: Optional[str] = None
    method: Optional[str] = None    # for derivatives: abliteration / LoRA / etc.
    # Rich metadata from leaderboard + HF API
    params_b: float = 0.0           # parameter count in billions
    arch: str = ""                  # e.g. LlamaForCausalLM
    merged: bool = False            # weight-merged model
    hf_downloads: int = 0
    hf_likes: int = 0
    lb_score: float = 0.0           # Open LLM Leaderboard 2 average
    lb_ifeval: float = 0.0
    lb_bbh: float = 0.0
    lb_math: float = 0.0
    lb_gpqa: float = 0.0
    lb_musr: float = 0.0
    lb_mmlu_pro: float = 0.0
    registry_date: str = ""

    @property
    def safe_name(self) -> str:
        """Filesystem-safe name: org__repo  (double-underscore separator)."""
        return self.hf_repo.replace("/", "__")

    @property
    def output_dir_name(self) -> str:
        return self.safe_name


@dataclass
class Registry:
    models: list[ModelEntry] = field(default_factory=list)

    @classmethod
    def load(cls, path: Path) -> "Registry":
        with open(path) as f:
            data = yaml.safe_load(f)
        entries = []
        for raw in data.get("models", []):
            entries.append(ModelEntry(
                hf_repo=raw["hf_repo"],
                family=raw.get("family", ""),
                tier=raw.get("tier", "A"),
                importance=raw.get("importance", "medium"),
                licence=raw.get("licence", "unknown"),
                requires_auth=bool(raw.get("requires_auth", False)),
                notes=raw.get("notes", ""),
                parent_model=raw.get("parent_model"),
                method=raw.get("method"),
                params_b=float(raw.get("params_b") or 0),
                arch=raw.get("arch", "") or "",
                merged=bool(raw.get("merged", False)),
                hf_downloads=int(raw.get("hf_downloads") or 0),
                hf_likes=int(raw.get("hf_likes") or 0),
                lb_score=float(raw.get("lb_score") or 0),
                lb_ifeval=float(raw.get("lb_ifeval") or 0),
                lb_bbh=float(raw.get("lb_bbh") or 0),
                lb_math=float(raw.get("lb_math") or 0),
                lb_gpqa=float(raw.get("lb_gpqa") or 0),
                lb_musr=float(raw.get("lb_musr") or 0),
                lb_mmlu_pro=float(raw.get("lb_mmlu_pro") or 0),
                registry_date=raw.get("registry_date", "") or "",
            ))
        return cls(models=entries)

    def filter(
        self,
        tier: Optional[str] = None,
        importance: Optional[str] = None,
        family: Optional[str] = None,
    ) -> list[ModelEntry]:
        results = self.models
        if tier:
            results = [m for m in results if m.tier == tier.upper()]
        if importance:
            results = [m for m in results if m.importance == importance.lower()]
        if family:
            results = [m for m in results if m.family == family.lower()]
        return results
