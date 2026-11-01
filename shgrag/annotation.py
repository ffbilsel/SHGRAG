"""Expert rubric for explanations and repairs (replaces the 0/1 sheet).

Mentioning the right node names does not show that a causal explanation is
right, so experts score each item on separate criteria
(docs/annotation_guidelines.md):

Explanation (1 = yes, 0 = no, NA = not applicable)
  E1 direction      the cause -> effect direction of every link is right
  E2 steps          no intermediate step of the mechanism is missing or invented
  E3 timing         the stated situation can really occur (times, modes, thresholds)
  E4 no_assumption  no fact that is absent from the home (device, dependency, behaviour)
  E5 outcome        the undesired outcome (or, for "no conflict", the reason) is right
Repair
  R1 applicable     can be expressed as a rule edit with the home's devices/variables
  R2 resolves       removes the conflict in the stated situation
  R3 preserves      every involved rule still serves its purpose outside that situation
  R4 safe           no safety function disabled, no new hazard

The sample is stratified so that failures are represented, not only successes:
true positives per type, every false positive and false negative, and correct
answers on hard (near-miss) clean cases.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path

from .schema import Scenario

EXPL = ("E1_direction", "E2_steps", "E3_timing", "E4_no_assumption", "E5_outcome")
REPAIR = ("R1_applicable", "R2_resolves", "R3_preserves", "R4_safe")
LLM_CONDS = ("text", "text_deps", "graph")


def _stratum(r: dict, hard: bool) -> str:
    gt, pred = r["gt_label"] == "conflict", bool(r["pred_conflict"])
    if gt and pred:
        return "TP"
    if gt:
        return "FN"
    if pred:
        return "FP-hard" if hard else "FP"
    return "TN-hard" if hard else "TN"


def build_sheet(records: list[dict], scenarios: list[Scenario], out: Path, split: str,
                tp_per_type: int = 2, tn_hard_per_cond: int = 3, seed: int = 0) -> list[dict]:
    """Stratified sample of run-0 outputs of the LLM conditions."""
    rng = random.Random(seed)
    case_info = {c.id: (s, c) for s in scenarios for c in s.cases}
    rows: list[dict] = []
    for cond in LLM_CONDS:
        recs = [r for r in records if r["condition"] == cond and r["run"] == 0 and r["case_id"] in case_info]
        by = defaultdict(list)
        for r in recs:
            _, c = case_info[r["case_id"]]
            st = _stratum(r, c.hard)
            key = (st, c.type) if st == "TP" else (st, None)
            by[key].append(r)
        picked = []
        for (st, t), rr in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
            rr = sorted(rr, key=lambda r: r["case_id"])
            if st == "TP":
                picked += rng.sample(rr, min(tp_per_type, len(rr)))
            elif st == "TN-hard":
                picked += rng.sample(rr, min(tn_hard_per_cond, len(rr)))
            elif st in ("FP", "FP-hard", "FN"):
                picked += rr  # every error is reviewed
        for r in picked:
            s, c = case_info[r["case_id"]]
            rows.append(dict(
                split=split, condition=cond, case_id=c.id, stratum=_stratum(r, c.hard),
                gt_label=c.label, gt_type=c.type or "", gt_situation=c.situation or "", gt_outcome=c.undesired_outcome or "",
                gt_justification=c.justification, rules=" | ".join(f"{rid}: {s.rule(rid).text}" for rid in c.rules),
                pred_conflict=r["pred_conflict"], pred_type=r["pred_type"] or "", explanation=r["explanation"],
                evidence=" | ".join(r.get("evidence", [])), repair=r.get("repair", ""),
                **{k: "" for k in EXPL + REPAIR}, notes="",
            ))
    rng.shuffle(rows)  # hide the condition order from the annotator
    for i, row in enumerate(rows):
        row["item"] = i
    _write(rows, out)
    return rows


def build_repair_sheet(repair_rows: list[dict], scenarios: list[Scenario], out: Path, condition: str = "graph") -> list[dict]:
    """One row per case: the final structured repair of run 0, with the automatic verdicts."""
    case_info = {c.id: (s, c) for s in scenarios for c in s.cases}
    rows = []
    for r in repair_rows:
        if r["condition"] != condition or r["run"] != 0:
            continue
        s, c = case_info[r["case_id"]]
        fa = r["attempts"][-1]
        rows.append(dict(
            split="dev", condition=f"repair:{condition}", case_id=c.id, stratum="repair",
            gt_label=c.label, gt_type=c.type, gt_situation=c.situation, gt_outcome=c.undesired_outcome,
            gt_justification=c.justification, rules=" | ".join(f"{rid}: {s.rule(rid).text}" for rid in c.rules),
            pred_conflict=True, pred_type=c.type, explanation=fa.get("proposal", {}).get("rationale", ""),
            evidence="graph path: " + " -> ".join(fa.get("proposal", {}).get("graph_path", [])),
            repair=fa.get("diff", fa.get("error", "")),
            auto_verdict=f"success={r['success']} resolved={r['resolved']} intent={r['intent']} no_new={r['no_new']} attempts={r['n_attempts']}",
            **{k: "NA" for k in EXPL}, **{k: "" for k in REPAIR}, notes="",
        ))
    for i, row in enumerate(rows):
        row["item"] = i
    _write(rows, out)
    return rows


def _write(rows: list[dict], out: Path) -> None:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        out.write_text("")
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


def score_sheet(path: Path) -> dict:
    """Share of 1s per criterion (NA and blanks ignored), per condition and stratum."""
    out: dict = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            for k in EXPL + REPAIR:
                v = (row.get(k) or "").strip()
                if v in ("0", "1"):
                    for key in (row["condition"], f"{row['condition']}/{row['stratum']}"):
                        out[key][k][0] += int(v)
                        out[key][k][1] += 1
    return {g: {k: dict(rate=a / n, n=n) for k, (a, n) in d.items()} for g, d in out.items()}


def cohen_kappa(path_a: Path, path_b: Path) -> dict:
    """Agreement between two annotators who filled copies of the same sheet."""
    def load(p):
        with open(p, newline="") as f:
            return {r["item"]: r for r in csv.DictReader(f)}

    a, b = load(path_a), load(path_b)
    out = {}
    for k in EXPL + REPAIR:
        pairs = [(a[i][k].strip(), b[i][k].strip()) for i in a if i in b and a[i][k].strip() in ("0", "1") and b[i][k].strip() in ("0", "1")]
        if not pairs:
            continue
        n = len(pairs)
        po = sum(x == y for x, y in pairs) / n
        pa1, pb1 = sum(x == "1" for x, _ in pairs) / n, sum(y == "1" for _, y in pairs) / n
        pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
        out[k] = dict(n=n, observed=po, kappa=(po - pe) / (1 - pe) if pe < 1 else 1.0)
    return out


# --------------------------------------------------------------------------
# Optional LLM-judge pilot (NOT a substitute for the expert)
# --------------------------------------------------------------------------
# Fills a copy of a rubric sheet with an LLM judge from a different model
# family size, so the expert can start from it and the agreement between judge
# and expert can be reported (rubric-kappa). Its numbers are labelled as a pilot.

from typing import Literal as _Lit  # noqa: E402

from pydantic import BaseModel as _BM  # noqa: E402

_Score = _Lit["1", "0", "NA"]


class RubricScores(_BM):
    E1_direction: _Score
    E2_steps: _Score
    E3_timing: _Score
    E4_no_assumption: _Score
    E5_outcome: _Score
    R1_applicable: _Score
    R2_resolves: _Score
    R3_preserves: _Score
    R4_safe: _Score
    notes: str


JUDGE_SYSTEM = """\
You review a smart-home conflict analysis against the ground truth, using the \
rubric below. Score each criterion 1 (yes), 0 (no) or NA (does not apply). \
Be strict: a criterion is 1 only if the text supports it.
E1 direction: every causal link in the explanation points the right way.
E2 steps: no intermediate step of the mechanism is missing or invented.
E3 timing: the stated situation can really occur (times, modes, thresholds).
E4 no_assumption: every fact used exists in the home description.
E5 outcome: the undesired outcome (or, for a 'no conflict' answer, the reason) matches the ground truth.
R1 applicable: the repair can be written as a rule edit with existing devices/variables.
R2 resolves: the repair removes the conflict in the stated situation.
R3 preserves: each involved rule still serves its purpose outside that situation.
R4 safe: no safety function disabled and no new hazard.
For a 'no conflict' answer, the repair criteria are NA. Explain 0 scores in notes (one or two sentences).\
"""


def judge_sheet(sheet: Path, scenarios: list[Scenario], out: Path, llm, workers: int = 6) -> int:
    from concurrent.futures import ThreadPoolExecutor

    from .prompts import home_facts_text

    by_case = {c.id: s for s in scenarios for c in s.cases}
    with open(sheet, newline="") as f:
        rows = list(csv.DictReader(f))

    def one(row: dict) -> dict:
        s = by_case[row["case_id"]]
        prompt = (
            f"# Home\n{home_facts_text(s)}\n\n# Rules under analysis\n{row['rules']}\n\n"
            f"# Ground truth\nlabel: {row['gt_label']} {row['gt_type']}\nsituation: {row['gt_situation']}\n"
            f"undesired outcome: {row['gt_outcome']}\njustification: {row['gt_justification']}\n\n"
            f"# Output under review\nconflict: {row['pred_conflict']} {row['pred_type']}\n"
            f"explanation: {row['explanation']}\nevidence: {row['evidence']}\nrepair: {row['repair']}\n"
            + (f"automatic verifier: {row['auto_verdict']}\n" if row.get("auto_verdict") else "")
            + "\nScore the output."
        )
        res = llm.structured(prompt, 0, JUDGE_SYSTEM, RubricScores)
        new = dict(row)
        if res.verdict is not None:
            v = res.verdict.model_dump()
            for k in EXPL + REPAIR:
                if not (row.get(k) == "NA" and v[k] != "NA"):
                    new[k] = v[k]
            new["notes"] = "LLM-judge pilot: " + v["notes"]
        else:
            new["notes"] = f"LLM-judge error: {res.error}"
        return new

    with ThreadPoolExecutor(max_workers=workers) as pool:
        filled = list(pool.map(one, rows))
    _write(filled, out)
    return len(filled)
