"""LLM pipeline with a fake Anthropic client (no network)."""

from types import SimpleNamespace

from shgrag.experiment import load_records, run_experiment
from shgrag.llm import LLMClient, LLMConfig
from shgrag.prompts import SYSTEM_PROMPT, Verdict
from shgrag.reasoners import GraphReasoner, TextOnlyReasoner


class FakeMessages:
    def __init__(self):
        self.calls = []

    def parse(self, **kw):
        self.calls.append(kw)
        prompt = kw["messages"][0]["content"]
        conflict = "AFFECTS[physical]" in prompt  # "sees" the hidden dependency only with the graph
        v = Verdict(conflict=conflict, conflict_type="physical" if conflict else "none", involved_rules=["R1", "R2"],
                    explanation="plug_hall powers camera_hall" if conflict else "no conflict",
                    evidence=[], repair="none")
        return SimpleNamespace(parsed_output=v, stop_reason="end_turn",
                               usage=SimpleNamespace(input_tokens=100, output_tokens=20))


def _client(tmp_path):
    fake = SimpleNamespace(messages=FakeMessages())
    return LLMClient(LLMConfig(cache_dir=tmp_path / "cache"), client=fake), fake


def test_same_system_prompt_and_model(cases, tmp_path):
    llm, fake = _client(tmp_path)
    s, c = cases["s01_c1"]
    TextOnlyReasoner(llm).predict(s, c.rules)
    GraphReasoner(llm).predict(s, c.rules)
    a, b = fake.messages.calls
    assert a["system"] == b["system"] == SYSTEM_PROMPT
    assert a["model"] == b["model"] and a["output_config"] == b["output_config"]
    assert a["output_format"] is b["output_format"] is Verdict
    assert "AFFECTS" not in a["messages"][0]["content"]
    assert "AFFECTS" in b["messages"][0]["content"]


def test_graph_beats_text_on_fake(cases, tmp_path):
    llm, _ = _client(tmp_path)
    s, c = cases["s01_c1"]
    assert not TextOnlyReasoner(llm).predict(s, c.rules).conflict
    p = GraphReasoner(llm).predict(s, c.rules)
    assert p.conflict and p.conflict_type == "physical" and p.context_nodes > 0


def test_cache_and_runs(cases, tmp_path):
    llm, fake = _client(tmp_path)
    s, c = cases["s01_c1"]
    r = TextOnlyReasoner(llm)
    r.predict(s, c.rules, run=0)
    r.predict(s, c.rules, run=0)
    assert len(fake.messages.calls) == 1  # cached
    r.predict(s, c.rules, run=1)
    assert len(fake.messages.calls) == 2  # new run index -> new sample


def test_refusal_is_recorded(cases, tmp_path):
    llm, fake = _client(tmp_path)
    fake.messages.parse = lambda **kw: SimpleNamespace(parsed_output=None, stop_reason="refusal",
                                                       usage=SimpleNamespace(input_tokens=1, output_tokens=0))
    s, c = cases["s01_c1"]
    p = TextOnlyReasoner(llm).predict(s, c.rules)
    assert p.conflict is None and p.error == "refusal"


def test_run_experiment_end_to_end(scenarios, tmp_path):
    llm, _ = _client(tmp_path)
    subset = [scenarios["s01_hallway_security"], scenarios["s05_router_dependency"]]
    out = tmp_path / "res"
    run_experiment(subset, ["text", "graph", "graph_noaffects", "symbolic"], runs=2, out_dir=out, llm=llm, workers=2, progress=False)
    recs = load_records(out)
    assert len(recs) == 8 * 4 * 2
    for f in ("metrics.json", "results.md", "annotations.csv", "overall_metrics.png", "per_type_recall.png"):
        assert (out / f).exists(), f
    md = (out / "results.md").read_text()
    assert "Ablation" in md and "McNemar" in md
