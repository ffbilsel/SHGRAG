"""Freeze the held-out test set before any LLM sees it.

The manifest stores a hash of the label-bearing content of every test home
(devices, effects, rules, cases). `home_conflicts` and `home_clean_notes` are
excluded because pooled adjudication after the whole-home scan may add to
them; such additions are marked `added_by: adjudication` and reported
separately.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from .loader import load_scenarios

FROZEN_KEYS = ("id", "name", "split", "family", "rooms", "devices", "environment", "effects", "rules", "cases")


def content_hash(scenario) -> str:
    d = scenario.model_dump(mode="json")
    blob = json.dumps({k: d[k] for k in FROZEN_KEYS}, sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()


def write_manifest(data_dir: Path, prompt_fp: str) -> dict:
    scenarios = load_scenarios(data_dir)
    m = dict(frozen_on=date.today().isoformat(), prompt_fingerprint=prompt_fp,
             homes={s.id: content_hash(s) for s in scenarios})
    (Path(data_dir) / "MANIFEST.json").write_text(json.dumps(m, indent=2) + "\n")
    return m


def check_manifest(data_dir: Path) -> list[str]:
    m = json.loads((Path(data_dir) / "MANIFEST.json").read_text())
    current = {s.id: content_hash(s) for s in load_scenarios(data_dir)}
    problems = [f"{h}: changed after freezing" for h, v in m["homes"].items() if current.get(h) != v]
    problems += [f"{h}: added after freezing" for h in current if h not in m["homes"]]
    return problems
