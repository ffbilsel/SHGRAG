"""Graph drawings and result plots (static PNGs for the report)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import networkx as nx  # noqa: E402

from .evaluation import TYPES  # noqa: E402
from .graph_builder import node_label  # noqa: E402

# Fixed colour per entity (never by rank) - validated categorical slots 1-4.
CONDITION_COLORS = {
    "text": "#2a78d6",
    "graph": "#eb6834",
    "graph_noaffects": "#1baf7a",
    "symbolic": "#eda100",
    "symbolic_noaffects": "#e87ba4",
}
CONDITION_LABELS = {
    "text": "Text-only LLM",
    "graph": "Graph-assisted LLM",
    "graph_noaffects": "Graph w/o AFFECTS",
    "symbolic": "Symbolic checker",
    "symbolic_noaffects": "Symbolic w/o AFFECTS",
}
NODE_COLORS = {"Room": "#c3c2b7", "Device": "#2a78d6", "State": "#9fc5f0", "EnvVar": "#1baf7a", "Rule": "#eb6834"}
EDGE_STYLES = {
    "HAS_DEVICE": ("#b5b4ad", "solid"),
    "HAS_STATE": ("#b5b4ad", "solid"),
    "HAS_ENV": ("#b5b4ad", "solid"),
    "TRIGGERED_BY": ("#4a3aa7", "dashed"),
    "CONDITIONED_ON": ("#4a3aa7", "dotted"),
    "TARGETS": ("#eb6834", "solid"),
    "AFFECTS": ("#e34948", "solid"),
}
INK, MUTED = "#0b0b0b", "#52514e"


def _style(ax) -> None:
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d6d5ce")
    ax.tick_params(colors=MUTED)
    ax.yaxis.grid(True, color="#ecebe6", linewidth=0.8)
    ax.set_axisbelow(True)


def draw_graph(g: nx.MultiDiGraph, path: str | Path, title: str | None = None, highlight: set[str] | None = None) -> Path:
    """Draw a (sub)graph; nodes in `highlight` are emphasised."""
    path = Path(path)
    fig, ax = plt.subplots(figsize=(13, 9))
    pos = nx.spring_layout(nx.Graph(g), k=1.2 / max(1, g.number_of_nodes()) ** 0.5, seed=7, iterations=200)
    for etype, (color, style) in EDGE_STYLES.items():
        edges = [(u, v) for u, v, d in g.edges(data=True) if d["type"] == etype]
        if edges:
            nx.draw_networkx_edges(
                g, pos, edgelist=edges, ax=ax, edge_color=color, style=style,
                width=2.2 if etype == "AFFECTS" else 1.2, arrows=True, arrowsize=12,
                connectionstyle="arc3,rad=0.05", label=etype,
            )
    for ntype, color in NODE_COLORS.items():
        nodes = [n for n, d in g.nodes(data=True) if d["type"] == ntype]
        if nodes:
            sizes = [900 if highlight and n in highlight else 500 for n in nodes]
            nx.draw_networkx_nodes(g, pos, nodelist=nodes, node_color=color, node_size=sizes, ax=ax,
                                   edgecolors="#fcfcfb", linewidths=2, label=ntype)
    nx.draw_networkx_labels(g, pos, labels={n: node_label(n) for n in g}, font_size=7, font_color=INK, ax=ax)
    ax.legend(loc="upper left", fontsize=7, frameon=False, ncol=2)
    ax.set_title(title or g.graph.get("name", ""), color=INK, loc="left")
    ax.axis("off")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _bars(ax, groups: list[str], conds: list[str], values, errors) -> None:
    n = len(conds)
    width = 0.8 / n
    for i, c in enumerate(conds):
        xs = [g + (i - (n - 1) / 2) * width for g in range(len(groups))]
        ax.bar(xs, values[c], width * 0.92, yerr=errors[c], color=CONDITION_COLORS.get(c, "#888"),
               label=CONDITION_LABELS.get(c, c), capsize=2, error_kw=dict(ecolor=MUTED, lw=1))
    ax.set_xticks(range(len(groups)), groups)
    ax.set_ylim(0, 105)
    ax.set_ylabel("%", color=MUTED)
    _style(ax)


def plot_results(summary: dict, out_dir: str | Path) -> list[Path]:
    out_dir = Path(out_dir)
    conds = [c for c in CONDITION_COLORS if c in summary] + [c for c in summary if c not in CONDITION_COLORS]
    paths = []

    def agg(c, k):
        a = summary[c]["aggregate"][k]
        return 100 * a["mean"], 100 * a["std"]

    # Overall metrics
    metrics = [("precision", "Precision"), ("recall", "Recall"), ("f1", "F1"), ("accuracy", "Accuracy")]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    _bars(ax, [m[1] for m in metrics], conds,
          {c: [agg(c, m)[0] for m, _ in metrics] for c in conds},
          {c: [agg(c, m)[1] for m, _ in metrics] for c in conds})
    ax.set_title("Conflict vs. clean detection (mean ± std over runs)", loc="left", color=INK)
    ax.legend(frameon=False, fontsize=8, ncol=len(conds), loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    paths.append(out_dir / "overall_metrics.png")
    fig.savefig(paths[-1], dpi=150)
    plt.close(fig)

    # Per-type recall
    fig, ax = plt.subplots(figsize=(8, 4.2))
    _bars(ax, [t.capitalize() for t in TYPES], conds,
          {c: [agg(c, f"{t}_detection_recall")[0] for t in TYPES] for c in conds},
          {c: [agg(c, f"{t}_detection_recall")[1] for t in TYPES] for c in conds})
    ax.set_title("Detection recall by conflict type", loc="left", color=INK)
    ax.legend(frameon=False, fontsize=8, ncol=len(conds), loc="upper center", bbox_to_anchor=(0.5, -0.1))
    fig.tight_layout()
    paths.append(out_dir / "per_type_recall.png")
    fig.savefig(paths[-1], dpi=150)
    plt.close(fig)

    # False positives / negatives
    fig, ax = plt.subplots(figsize=(6, 4))
    groups = ["False positives", "False negatives"]
    n = len(conds)
    width = 0.8 / n
    for i, c in enumerate(conds):
        a = summary[c]["aggregate"]
        xs = [g + (i - (n - 1) / 2) * width for g in range(2)]
        ax.bar(xs, [a["fp"]["mean"], a["fn"]["mean"]], width * 0.92, yerr=[a["fp"]["std"], a["fn"]["std"]],
               color=CONDITION_COLORS.get(c, "#888"), label=CONDITION_LABELS.get(c, c), capsize=2,
               error_kw=dict(ecolor=MUTED, lw=1))
    ax.set_xticks(range(2), groups)
    ax.set_ylabel("cases", color=MUTED)
    _style(ax)
    ax.set_title("Errors per run", loc="left", color=INK)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    paths.append(out_dir / "errors.png")
    fig.savefig(paths[-1], dpi=150)
    plt.close(fig)
    return paths
