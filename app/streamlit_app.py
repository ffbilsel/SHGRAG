"""Demo UI: pick a scenario/case, inspect rules and graph evidence, compare verdicts.

    streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shgrag.loader import load_scenarios  # noqa: E402
from shgrag.prompts import text_only_prompt  # noqa: E402
from shgrag.reasoners import SymbolicReasoner, get_retrieval, make_reasoner  # noqa: E402
from shgrag.visualize import draw_graph  # noqa: E402

st.set_page_config(page_title="SHGRAG demo", layout="wide")


@st.cache_resource
def _scenarios():
    return {s.id: s for s in load_scenarios()}


@st.cache_resource
def _llm():
    from shgrag.llm import LLMClient

    return LLMClient()


scenarios = _scenarios()
st.title("SHGRAG - graph-assisted rule conflict detection")

with st.sidebar:
    sid = st.selectbox("Scenario", list(scenarios), format_func=lambda k: f"{k} - {scenarios[k].name}")
    s = scenarios[sid]
    cid = st.selectbox("Case", [c.id for c in s.cases])
    case = next(c for c in s.cases if c.id == cid)
    ablation = st.checkbox("Ablation: drop AFFECTS edges", value=False)
    use_llm = st.checkbox("Ask the LLM (uses API credits, cached)", value=False)

st.caption(s.description)
st.subheader("Rules under analysis")
for rid in case.rules:
    st.markdown(f"**{rid}** - {s.rule(rid).text}")

retrieval = get_retrieval(s, case.rules, include_effects=not ablation)
col_graph, col_ctx = st.columns([3, 2])
with col_graph:
    st.subheader("Retrieved subgraph")
    img = Path(".cache/figures") / f"{cid}{'_noaffects' if ablation else ''}.png"
    if not img.exists():
        draw_graph(retrieval.subgraph, img, title=f"{cid} ({retrieval.num_nodes} nodes, {retrieval.num_edges} edges)")
    st.image(str(img))
with col_ctx:
    st.subheader("Graph evidence sent to the LLM")
    st.code(retrieval.text, language="text")

st.subheader("Verdicts")
sym = SymbolicReasoner(include_effects=not ablation).predict(s, case.rules)
rows = [("Ground truth", case.label, case.type or "-", case.justification, "")]
rows.append(("Symbolic checker", "conflict" if sym.conflict else "clean", sym.conflict_type or "-", sym.explanation, sym.repair))
if use_llm:
    with st.spinner("Querying the LLM..."):
        for name in ("text", "graph_noaffects" if ablation else "graph"):
            p = make_reasoner(name, _llm()).predict(s, case.rules)
            label = "error: " + p.error if p.error else ("conflict" if p.conflict else "clean")
            rows.append((name, label, p.conflict_type or "-", p.explanation, p.repair))
st.table({"system": [r[0] for r in rows], "label": [r[1] for r in rows], "type": [r[2] for r in rows],
          "explanation": [r[3] for r in rows], "repair": [r[4] for r in rows]})

with st.expander("Text-only baseline prompt"):
    st.code(text_only_prompt(s, case.rules), language="text")
