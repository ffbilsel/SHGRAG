"""Load and validate scenario YAML files."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .schema import Scenario

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"  # dev split
TEST_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "test_scenarios"  # held-out split


class _Loader(yaml.SafeLoader):
    """YAML 1.2-style booleans: only true/false are booleans, so device values
    like `on`, `off`, `yes`, `no` stay strings."""


_Loader.yaml_implicit_resolvers = {
    k: [(tag, rx) for tag, rx in v if tag != "tag:yaml.org,2002:bool"]
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
for _first in "tTfF":
    _Loader.yaml_implicit_resolvers.setdefault(_first, []).insert(
        0, ("tag:yaml.org,2002:bool", re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$"))
    )


def load_scenario(path: str | Path) -> Scenario:
    with open(path, encoding="utf-8") as f:
        raw = yaml.load(f, Loader=_Loader)  # noqa: S506 - SafeLoader subclass
    return Scenario.model_validate(raw)


def apply_errata(scenarios: list[Scenario], errata_path: Path) -> list[Scenario]:
    """Return copies of the scenarios with post-freeze label corrections applied."""
    with open(errata_path, encoding="utf-8") as f:
        fixes = {e["case"]: e for e in yaml.load(f, Loader=_Loader) or []}
    out = []
    for s in scenarios:
        cases = []
        for c in s.cases:
            e = fixes.get(c.id)
            if e:
                c = c.model_copy(update=dict(label=e["label"], type=e.get("type"), situation=e.get("situation"),
                                             undesired_outcome=e.get("undesired_outcome"), hard=False))
            cases.append(c)
        out.append(Scenario.model_validate({**s.model_dump(), "cases": [c.model_dump() for c in cases]}))
    return out


def load_scenarios(data_dir: str | Path = DEFAULT_DATA_DIR, errata: bool = False) -> list[Scenario]:
    if errata:
        base = load_scenarios(data_dir)
        p = Path(data_dir) / "errata.yaml"
        return apply_errata(base, p) if p.exists() else base
    paths = sorted(p for p in Path(data_dir).glob("*.yaml") if p.name != "errata.yaml")
    if not paths:
        raise FileNotFoundError(f"no scenario files in {data_dir}")
    scenarios = [load_scenario(p) for p in paths]
    ids = [s.id for s in scenarios]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate scenario ids: {sorted(dupes)}")
    case_ids = [c.id for s in scenarios for c in s.cases]
    dupes = {i for i in case_ids if case_ids.count(i) > 1}
    if dupes:
        raise ValueError(f"duplicate case ids: {sorted(dupes)}")
    return scenarios
