#!/usr/bin/env python3
"""Build LTFS/tape allocation plan: PAR2-adjusted sizes, Tier-A family grouping, capacity ceiling."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import yaml


def _tape_archive_root() -> Path:
    """``tape-archive/`` (parent of ``scripts/``)."""
    return Path(__file__).resolve().parents[1]


def _cfg_root() -> Path:
    return _tape_archive_root() / "config"


def _registry_yaml() -> Path:
    """Archiver registry lives alongside this subtree in ``../config/registry.yaml``."""
    return _tape_archive_root().parent / "config" / "registry.yaml"


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _tiers_by_repo(registry_path: Path) -> dict[str, str]:
    data = _load_yaml(registry_path)
    out: dict[str, str] = {}
    for m in data.get("models", []):
        repo = m.get("hf_repo") or m.get("id")
        if repo:
            out[str(repo)] = str(m.get("tier", "?"))
    return out


def _par2_for_hf_model(tier: str, nbytes: int, policy: dict) -> float:
    gib = nbytes / (1024**3)
    key = "tier_a" if tier.upper() == "A" else "non_a"
    tiers = policy[key]["tiers_by_size_gib"]
    for band in tiers:
        if gib <= float(band["max_model_gib"]):
            return float(band["par2_fraction"])
    return float(tiers[-1]["par2_fraction"])


def _family_label(hf_repo: str, fam: dict) -> str:
    org, _, model = hf_repo.partition("/")
    if not model:
        return hf_repo
    splits = (fam.get("org_splits") or {}).get(org)
    if not splits:
        return org
    for rule in splits:
        pre = rule.get("match_prefix")
        if pre and model.startswith(pre):
            return str(rule["family_label"])
    for rule in splits:
        if not rule.get("match_prefix") and rule.get("family_label"):
            return str(rule["family_label"])
    return org


def _version_cohort_slug(model_id: str, fam: dict) -> str:
    vc = fam.get("version_cohort") or {}
    suffixes = vc.get("strip_suffixes") or []
    m = model_id
    changed = True
    while changed:
        changed = False
        for suf in sorted(suffixes, key=len, reverse=True):
            if m.endswith(suf):
                m = m[: -len(suf)]
                changed = True
                break
    return m or model_id


def _cohort_key(hf_repo: str, fam: dict) -> tuple[str, str, str]:
    org, _, model = hf_repo.partition("/")
    family = _family_label(hf_repo, fam)
    slug = _version_cohort_slug(model, fam)
    key = f"{family}::{slug}"
    return key, family, slug


def _bundle_family_label(bundle: list[dict], fam: dict) -> str | None:
    if not bundle:
        return None
    _, fam_lbl, _ = _cohort_key(bundle[0]["hf_repo"], fam)
    return fam_lbl


def _group_into_cohorts(
    models: list[dict],
    tiers: dict[str, str],
    policy: dict,
    fam: dict,
    *,
    tier_a_only: bool,
) -> list[dict]:
    """Atomic packing unit = family + version cohort (e.g. base + instruct of same release)."""

    groups: dict[str, list[dict]] = {}
    meta: dict[str, tuple[str, str]] = {}
    for row in models:
        repo = row["hf_repo"]
        tier = tiers.get(repo, "?").upper()
        if tier_a_only:
            if tier != "A":
                continue
        else:
            if tier == "A":
                continue
        if row.get("drive") == "d5":
            continue
        ck, family, slug = _cohort_key(repo, fam)
        meta.setdefault(ck, (family, slug))
        g = row.copy()
        p = _par2_for_hf_model("A" if tier_a_only else tiers.get(repo, "?"), g["bytes"], policy)
        g["par2_fraction"] = p
        g["effective_bytes"] = int(round(g["bytes"] * (1 + p)))
        groups.setdefault(ck, []).append(g)

    out = []
    for ck, items in groups.items():
        family, slug = meta[ck]
        items.sort(key=lambda x: -x["bytes"])
        total = sum(x["effective_bytes"] for x in items)
        out.append(
            {
                "cohort_key": ck,
                "family_label": family,
                "version_slug": slug,
                "models": items,
                "total_effective_bytes": total,
            }
        )
    out.sort(key=lambda x: -x["total_effective_bytes"])
    return out


def _pack_cohorts_exclusive_tapes(cohorts: list[dict], cap: int) -> list[list[dict]]:
    """Tier-A: one version cohort per tape when it fits (same family+version stay together).
    If a cohort exceeds ``cap``, strip-fill across consecutive tapes for that cohort only."""

    tapes: list[list[dict]] = []

    for g in sorted(cohorts, key=lambda x: -x["total_effective_bytes"]):
        tot = g["total_effective_bytes"]
        if tot <= cap:
            tapes.append(list(g["models"]))
            continue

        remaining = list(g["models"])
        while remaining:
            cur: list[dict] = []
            used = 0
            i = 0
            while i < len(remaining):
                m = remaining[i]
                if used + m["effective_bytes"] <= cap:
                    cur.append(m)
                    used += m["effective_bytes"]
                    remaining.pop(i)
                else:
                    i += 1
            if not cur:
                raise SystemExit(
                    f"Single model exceeds tape cap: cohort={g['cohort_key']} "
                    f"{remaining[0]['hf_repo']} effective={remaining[0]['effective_bytes']} cap={cap}"
                )
            tapes.append(cur)

    return tapes


def _pack_cohorts_ffd(
    cohorts: list[dict],
    cap: int,
    fam: dict,
    *,
    same_family_only: bool,
) -> list[list[dict]]:
    """Cohorts stay atomic; multiple cohorts may share a tape (first-fit decreasing).

    If ``same_family_only``, only merge onto a non-empty tape when its ``family_label``
    matches the cohort's (from ``tape_family_policy`` org_splits).
    """

    def _may_merge(bundle: list[dict], cohort_family: str) -> bool:
        if not same_family_only:
            return True
        bfam = _bundle_family_label(bundle, fam)
        return bfam is None or bfam == cohort_family

    tapes: list[list[dict]] = []
    for g in sorted(cohorts, key=lambda x: -x["total_effective_bytes"]):
        fam_g = g["family_label"]
        tot = g["total_effective_bytes"]
        if tot <= cap:
            placed = False
            for bundle in tapes:
                if not _may_merge(bundle, fam_g):
                    continue
                used = sum(m["effective_bytes"] for m in bundle)
                if used + tot <= cap:
                    bundle.extend(g["models"])
                    placed = True
                    break
            if not placed:
                tapes.append(list(g["models"]))
            continue

        remaining = list(g["models"])
        while remaining:
            cur: list[dict] = []
            used = 0
            i = 0
            while i < len(remaining):
                m = remaining[i]
                if used + m["effective_bytes"] <= cap:
                    cur.append(m)
                    used += m["effective_bytes"]
                    remaining.pop(i)
                else:
                    i += 1
            if not cur:
                raise SystemExit(
                    f"Single model exceeds tape cap: cohort={g['cohort_key']} "
                    f"{remaining[0]['hf_repo']} effective={remaining[0]['effective_bytes']} cap={cap}"
                )
            placed = False
            for bundle in tapes:
                if not _may_merge(bundle, fam_g):
                    continue
                u = sum(m["effective_bytes"] for m in bundle)
                if u + used <= cap:
                    bundle.extend(cur)
                    placed = True
                    break
            if not placed:
                tapes.append(cur)

    return tapes


def _directory_bundle(jobs: list[dict], frac: float, cap: int, label: str) -> tuple[list[dict], int]:
    """Returns list of tape bundles (each bundle list of jobs with effective sizes)."""

    enriched = []
    total_eff = 0
    for j in jobs:
        b = int(j["bytes"])
        eff = int(round(b * (1 + frac)))
        total_eff += eff
        enriched.append({**j, "par2_fraction": frac, "effective_bytes": eff, "kind": label})
    if total_eff <= cap:
        return [enriched], len(enriched)
    # split jobs across tapes — each job usually whole; if one job > cap, fatal
    tapes = []
    cur = []
    used = 0
    for j in enriched:
        if j["effective_bytes"] > cap:
            raise SystemExit(f"Directory job exceeds tape cap: {j}")
        if used + j["effective_bytes"] > cap:
            tapes.append(cur)
            cur = []
            used = 0
        cur.append(j)
        used += j["effective_bytes"]
    if cur:
        tapes.append(cur)
    return tapes, sum(len(t) for t in tapes)


def _hf_snapshot_job_row(m: dict) -> dict:
    return {
        "kind": "hf_snapshot",
        "drive": m["drive"],
        "hf_repo": m["hf_repo"],
        "revision": m["revision"],
        "bytes": m["bytes"],
        "par2_fraction": m["par2_fraction"],
        "effective_bytes": m["effective_bytes"],
        "rel_path": m["rel_path"],
    }


def _hf_snapshot_jobs(bundle: list[dict]) -> list[dict]:
    return [_hf_snapshot_job_row(m) for m in sorted(bundle, key=lambda x: -x["bytes"])]


def _atom_hf(bundle: list[dict], profile: str) -> dict:
    return {
        "effective_bytes": sum(m["effective_bytes"] for m in bundle),
        "profile": profile,
        "models": bundle,
    }


def _atom_dir(bundle: list[dict], profile: str, refresh_expectation: str | None) -> dict:
    return {
        "effective_bytes": sum(j["effective_bytes"] for j in bundle),
        "profile": profile,
        "dir_jobs": bundle,
        "refresh_expectation": refresh_expectation,
    }


def _ffd_pack_atoms(atoms: list[dict], cap: int) -> list[list[dict]]:
    """Each atom is indivisible; pack into fewest tapes (first-fit decreasing order)."""

    tapes_atoms: list[list[dict]] = []
    for atom in sorted(atoms, key=lambda x: -x["effective_bytes"]):
        placed = False
        for tape in tapes_atoms:
            used = sum(a["effective_bytes"] for a in tape)
            if used + atom["effective_bytes"] <= cap:
                tape.append(atom)
                placed = True
                break
        if not placed:
            tapes_atoms.append([atom])
    return tapes_atoms


def _tape_entry_from_atoms(tape_atoms: list[dict], fam: dict, tape_id: str) -> dict:
    jobs: list[dict] = []
    cohort_labels: set[str] = set()
    profiles: set[str] = set()
    refresh: str | None = None
    for a in tape_atoms:
        profiles.add(a["profile"])
        if a.get("models"):
            jobs.extend(_hf_snapshot_jobs(a["models"]))
            for m in a["models"]:
                cohort_labels.add(_cohort_key(m["hf_repo"], fam)[0])
        else:
            jobs.extend(a["dir_jobs"])
            if a.get("refresh_expectation"):
                refresh = a["refresh_expectation"]
    eff = sum(a["effective_bytes"] for a in tape_atoms)
    prof_list = sorted(profiles)
    out: dict = {
        "id": tape_id,
        "profile": prof_list[0] if len(prof_list) == 1 else "mixed",
        "effective_bytes": eff,
        "constituent_profiles": prof_list,
        "jobs": jobs,
    }
    if cohort_labels:
        out["cohorts_on_tape"] = sorted(cohort_labels)
    if refresh and "self_hosted" in profiles:
        out["refresh_expectation"] = refresh
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="Write tape_allocation_plan.yaml")
    args = ap.parse_args()

    cfg = _cfg_root()
    policy = _load_yaml(cfg / "tape_par2_policy.yaml")
    pools = _load_yaml(cfg / "tape_pools_snapshot.yaml")
    fam = _load_yaml(cfg / "tape_family_policy.yaml")
    inv_path = cfg / "tape_inventory_snapshot.json"
    reg_path = _registry_yaml()

    cap = int(pools["tape_capacity_bytes"])
    inv = json.loads(inv_path.read_text(encoding="utf-8"))
    models = inv["models"]
    tiers = _tiers_by_repo(reg_path)

    d5 = pools["d5"]
    d5_net = int(d5["volume_total_bytes"]) - int(d5["tmp_exclude_bytes"])
    dir_pol = policy["directory_pool_par2_fraction"]

    tier_a_mode = str((fam.get("tier_a_packing") or {}).get("mode", "ffd_same_family")).strip()
    if tier_a_mode not in {"exclusive", "ffd", "ffd_same_family"}:
        raise SystemExit(
            f"tape_family_policy.yaml tier_a_packing.mode must be exclusive|ffd|ffd_same_family, got {tier_a_mode!r}"
        )

    cross_profile = bool((fam.get("tape_packing") or {}).get("cross_profile_ffd", False))

    notes = [
        "Tier-A packing mode from tape_family_policy.yaml tier_a_packing.mode "
        "(exclusive | ffd | ffd_same_family); cohorts stay atomic (base+instruct/version slug).",
        "Non-A raw: cohorts stay atomic; cohorts may share a tape (FFD).",
        "d5 raw snapshots appear only on D5 volume tape (drive=d5 rows excluded from raw pools).",
        "HOME / quantized = self_hosted directory pool (GGUF etc.); may share a cartridge with other profiles when cross_profile_ffd is true.",
    ]
    if cross_profile:
        notes.insert(
            0,
            "tape_packing.cross_profile_ffd: one global FFD across HF + specialist + ablated + quantized atoms → V-* tape ids (~ceil(total_eff/cap) besides D5).",
        )

    plan: dict = {
        "tape_capacity_bytes": cap,
        "tier_a_packing_mode": tier_a_mode,
        "cross_profile_ffd": cross_profile,
        "notes": notes,
        "tapes": [],
    }
    tape_counter = {"D5": 0, "A": 0, "R": 0, "SPE": 0, "ABL": 0, "HOME": 0, "V": 0}

    def next_id(prefix: str) -> str:
        tape_counter[prefix] += 1
        return f"{prefix}-{tape_counter[prefix]:02d}"

    def next_vault_id() -> str:
        tape_counter["V"] += 1
        return f"V-{tape_counter['V']:02d}"

    # D5 system snapshot
    plan["tapes"].append(
        {
            "id": next_id("D5"),
            "profile": "d5_system",
            "payload_bytes": d5_net,
            "par2_fraction": float(policy["d5_system_snapshot"]["par2_fraction"]),
            "effective_bytes": d5_net,
            "jobs": [
                {
                    "kind": "d5_volume",
                    "exclude_paths": [".tmp"],
                    "note": "Full models-d5 filesystem image excluding /.tmp",
                }
            ],
        }
    )

    cohorts_a = _group_into_cohorts(models, tiers, policy, fam, tier_a_only=True)
    if tier_a_mode == "exclusive":
        a_bundles = _pack_cohorts_exclusive_tapes(cohorts_a, cap)
    else:
        a_bundles = _pack_cohorts_ffd(
            cohorts_a,
            cap,
            fam,
            same_family_only=(tier_a_mode == "ffd_same_family"),
        )

    cohorts_na = _group_into_cohorts(models, tiers, policy, fam, tier_a_only=False)
    na_bundles = _pack_cohorts_ffd(cohorts_na, cap, fam, same_family_only=False)

    dj = pools["directory_jobs"]
    spe_frac = float(dir_pol["specialist"])
    spe_bundles, _ = _directory_bundle(dj["specialist"], spe_frac, cap, "specialist")
    abl_frac = float(dir_pol["ablated"])
    abl_bundles, _ = _directory_bundle(dj["ablated"], abl_frac, cap, "ablated")
    sh = dj["self_hosted"]
    home_jobs = sh["jobs"]
    sh_frac = float(dir_pol["quantized"])
    home_bundles, _ = _directory_bundle(home_jobs, sh_frac, cap, "self_hosted")

    if cross_profile:
        atoms: list[dict] = []
        for b in a_bundles:
            atoms.append(_atom_hf(b, "tier_a_raw"))
        for b in na_bundles:
            atoms.append(_atom_hf(b, "non_a_raw"))
        for b in spe_bundles:
            atoms.append(_atom_dir(b, "specialist", None))
        for b in abl_bundles:
            atoms.append(_atom_dir(b, "ablated", None))
        for b in home_bundles:
            atoms.append(_atom_dir(b, "self_hosted", sh.get("refresh_expectation")))
        for tape_atoms in _ffd_pack_atoms(atoms, cap):
            plan["tapes"].append(_tape_entry_from_atoms(tape_atoms, fam, next_vault_id()))
    else:
        for bundle in a_bundles:
            eff = sum(m["effective_bytes"] for m in bundle)
            cohort_labels = sorted({_cohort_key(m["hf_repo"], fam)[0] for m in bundle})
            plan["tapes"].append(
                {
                    "id": next_id("A"),
                    "profile": "tier_a_raw",
                    "effective_bytes": eff,
                    "cohorts_on_tape": cohort_labels,
                    "jobs": _hf_snapshot_jobs(bundle),
                }
            )

        for bundle in na_bundles:
            eff = sum(m["effective_bytes"] for m in bundle)
            plan["tapes"].append(
                {
                    "id": next_id("R"),
                    "profile": "non_a_raw",
                    "effective_bytes": eff,
                    "jobs": _hf_snapshot_jobs(bundle),
                }
            )

        for bundle in spe_bundles:
            eff = sum(j["effective_bytes"] for j in bundle)
            plan["tapes"].append(
                {
                    "id": next_id("SPE"),
                    "profile": "specialist",
                    "effective_bytes": eff,
                    "jobs": bundle,
                }
            )

        for bundle in abl_bundles:
            eff = sum(j["effective_bytes"] for j in bundle)
            plan["tapes"].append(
                {
                    "id": next_id("ABL"),
                    "profile": "ablated",
                    "effective_bytes": eff,
                    "jobs": bundle,
                }
            )

        for bundle in home_bundles:
            eff = sum(j["effective_bytes"] for j in bundle)
            plan["tapes"].append(
                {
                    "id": next_id("HOME"),
                    "profile": "self_hosted",
                    "refresh_expectation": sh.get("refresh_expectation", "high"),
                    "effective_bytes": eff,
                    "jobs": bundle,
                }
            )

    # Sanity: warn over-cap
    warnings = []
    for t in plan["tapes"]:
        if t["effective_bytes"] > cap:
            warnings.append(f"{t['id']} effective {t['effective_bytes']} > cap {cap}")

    plan["warnings"] = warnings
    vault_eff = sum(t["effective_bytes"] for t in plan["tapes"] if t.get("profile") != "d5_system")
    plan["summary"] = {
        "tape_count": len(plan["tapes"]),
        "profiles": {},
        "vault_effective_bytes": vault_eff,
        "theoretical_min_tapes_vault": math.ceil(vault_eff / cap) if cap > 0 else 0,
    }
    for t in plan["tapes"]:
        plan["summary"]["profiles"][t["profile"]] = plan["summary"]["profiles"].get(t["profile"], 0) + 1

    out_path = cfg / "tape_allocation_plan.yaml"
    text = yaml.safe_dump(plan, sort_keys=False, allow_unicode=True)
    print(text)
    if warnings:
        print("WARNINGS:", warnings, file=__import__("sys").stderr)
    if args.write:
        out_path.write_text(text, encoding="utf-8")
        print(f"Wrote {out_path}", file=__import__("sys").stderr)


if __name__ == "__main__":
    main()
