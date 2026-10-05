"""Load and validate scenario YAML files."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from .schema import Scenario

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "scenarios"


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


def load_scenarios(data_dir: str | Path = DEFAULT_DATA_DIR) -> list[Scenario]:
    paths = sorted(Path(data_dir).glob("*.yaml"))
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
