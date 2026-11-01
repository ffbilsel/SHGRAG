"""Provenance and leakage checks for the benchmark.

* `check_sources` fetches every `source.url` of adapted rules and checks that
  the recorded `excerpt` appears verbatim in the fetched file.
* `similarity_report` compares every held-out home with every dev home, so
  small variations of one scenario cannot sit on both sides of the split.
"""

from __future__ import annotations

import re
import urllib.request
from itertools import product

from .schema import Scenario


def raw_url(url: str) -> str:
    m = re.match(r"https://github\.com/([^/]+)/([^/]+)/blob/(.+)", url)
    return f"https://raw.githubusercontent.com/{m.group(1)}/{m.group(2)}/{m.group(3)}" if m else url


def check_sources(scenarios: list[Scenario], timeout: int = 20) -> list[dict]:
    cache: dict[str, str | Exception] = {}
    out = []
    for s in scenarios:
        for r in s.rules:
            src = r.source
            if src is None or src.kind != "adapted":
                continue
            url = raw_url(src.url)
            if url not in cache:
                try:
                    with urllib.request.urlopen(url, timeout=timeout) as f:  # noqa: S310 - fixed https URLs from the dataset
                        cache[url] = f.read().decode("utf-8", "replace")
                except Exception as e:  # network errors are reported, not raised
                    cache[url] = e
            body = cache[url]
            ok = isinstance(body, str) and src.excerpt in body
            out.append(dict(scenario=s.id, rule=r.id, app=src.app, url=src.url, ok=ok,
                            error=None if isinstance(body, str) else str(body)))
    return out


def _signature(s: Scenario) -> dict[str, set]:
    """Content features of a home that would be shared by variants of one scenario."""
    return dict(
        device_types={d.type for d in s.devices},
        dependencies={(s.device(e.source.split(".")[0]).type,
                       s.device(e.target.split(".")[0]).type if "." in e.target else f"env:{e.target}")
                      for e in s.effects},
        rule_words={w for r in s.rules for w in re.findall(r"[a-z]{4,}", r.text.lower())},
    )


def _jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def similarity_report(dev: list[Scenario], test: list[Scenario]) -> list[dict]:
    """For each test home, the most similar dev home on each feature."""
    rows = []
    sig_dev = {s.id: _signature(s) for s in dev}
    for t in test:
        st = _signature(t)
        best = {}
        for k in ("device_types", "dependencies", "rule_words"):
            sid, val = max(((d, _jaccard(st[k], sig_dev[d][k])) for d in sig_dev), key=lambda x: x[1])
            best[k] = (sid, round(val, 2))
        shared_deps = sorted({x for d in sig_dev.values() for x in d["dependencies"]} & st["dependencies"])
        rows.append(dict(test=t.id, family=t.family, closest=best, shared_dependency_types=shared_deps))
    return rows


def family_overlap(dev: list[Scenario], test: list[Scenario]) -> set[str]:
    return {d.family for d in dev} & {t.family for t in test}


def name_overlap(dev: list[Scenario], test: list[Scenario]) -> set[str]:
    return {d.name for d in dev} & {t.name for t in test}


__all__ = ["check_sources", "similarity_report", "family_overlap", "name_overlap", "raw_url", "product"]
