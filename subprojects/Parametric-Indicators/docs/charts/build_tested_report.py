"""Build the 'WHAT WAS ACTUALLY TESTED' baby report (docs/WS-I_WHAT_WAS_TESTED.md).

Answers one question in plain language: did the search tune each indicator's *internal* params
(EMA period, Keltner m/n, ...) or only flip them on/off? (Answer: it tuned BOTH.) Supported by:
  • Mermaid diagrams (search-space tree + how-one-trial-is-scored) — render on GitHub/VS Code.
  • Inline Plotly charts (CDN) — knobs-per-indicator, and champions' tuned values vs defaults.
  • The per-TF champion full recipes (box params + every enabled indicator's tuned internals),
    read from optimize/results/wsi_champions_full.json.

Run:  python3 docs/charts/build_tested_report.py
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DOCS = os.path.abspath(os.path.join(_HERE, ".."))
_ROOT = os.path.abspath(os.path.join(_DOCS, ".."))
sys.path.insert(0, _ROOT)

import plotly.graph_objects as go  # noqa: E402
from indicators import library  # noqa: E402

CHAMP = json.load(open(os.path.join(_ROOT, "optimize/results/wsi_champions_full.json")))
TFS = ["4h", "2h", "1h", "15m", "5m", "2m", "1m"]
PAL = dict(bar="#5472d3", bar2="#2e7d32", def_="#c62828", grid="rgba(0,0,0,0.08)")


def _schema_rows():
    rows = []
    for key in library.REGISTRY:
        m = library.SCHEMA[key]
        ps = m.get("params", [])
        rows.append((key, m.get("mode", "?"), ps))
    return rows


def fig_knobs_per_indicator():
    """Horizontal bar: how many *internal* dials each indicator exposed to the search (+ the 1 on/off
    switch every indicator also has)."""
    rows = sorted(_schema_rows(), key=lambda r: len(r[2]))
    names = [f"{k}  ({mode})" for k, mode, ps in rows]
    nparam = [len(ps) for _, _, ps in rows]
    text = [f"{n} dial{'s' if n != 1 else ''}" + (" (only on/off)" if n == 0 else "") for n in nparam]
    fig = go.Figure(go.Bar(x=nparam, y=names, orientation="h", marker_color=PAL["bar"],
                           text=text, textposition="outside"))
    total = sum(nparam)
    fig.update_layout(
        title=f"Tunable INTERNAL dials per indicator (15 on/off switches + {total} internal dials searched)",
        xaxis_title="number of internal parameters the search tuned",
        margin=dict(l=10, r=30, t=50, b=40), height=460,
        plot_bgcolor="white", xaxis=dict(gridcolor=PAL["grid"]))
    return fig


def fig_champ_vs_default(key, pnames):
    """Grouped bar: a recurring indicator's tuned internal value per TF vs its schema default."""
    meta = library.SCHEMA[key]
    defs = {p["name"]: p["default"] for p in meta["params"]}
    fig = go.Figure()
    for pn in pnames:
        xs, ys = [], []
        for tf in TFS:
            inds = CHAMP.get(tf, {}).get("indicators", {})
            if key in inds and pn in inds[key]:
                xs.append(tf); ys.append(inds[key][pn])
        fig.add_bar(name=f"{pn} (tuned)", x=xs, y=ys)
        fig.add_hline(y=defs[pn], line_dash="dot", line_color=PAL["def_"],
                      annotation_text=f"{pn} default={defs[pn]}", annotation_position="top left")
    fig.update_layout(
        title=f"'{key}' — tuned internal value per timeframe vs its default (dotted red)",
        barmode="group", xaxis_title="timeframe (champion)", yaxis_title="parameter value",
        margin=dict(l=10, r=20, t=50, b=40), height=440,
        plot_bgcolor="white", yaxis=dict(gridcolor=PAL["grid"]),
        legend=dict(orientation="h", y=1.12))
    return fig


def _inline(fig, first):
    return fig.to_html(full_html=False, include_plotlyjs=("cdn" if first else False),
                       default_width="100%", default_height="460px")


def _recipe_block(tf):
    c = CHAMP.get(tf)
    if not c or "box" in c is False:
        return f"_{tf}: no feasible champion._\n"
    b = c["box"]
    lines = [f"**Box / risk knobs** — softSL `{b['sl_soft']}` · hardSL `{b['sl_hard']}` · TP `{b['tp']}` · "
             f"vol-gate `{b['gate_pct']}%` · dd-breaker `${b['dd_limit']:,.0f}` · cooldown `{b['cooldown']}` · "
             f"flip `{b['flip']}` · **K=`{b['k']}`** (need K agreeing confirmers)", "",
             "| indicator | tuned internal params |", "|---|---|"]
    for k, vals in c["indicators"].items():
        vs = ", ".join(f"`{pk}={pv}`" for pk, pv in vals.items()) or "_(no internal params — vwap)_"
        lines.append(f"| **{k}** | {vs} |")
    return "\n".join(lines) + "\n"


def main():
    f_knobs = _inline(fig_knobs_per_indicator(), True)
    f_ema = _inline(fig_champ_vs_default("ema_trend", ["fast", "slow"]), False)
    f_macd = _inline(fig_champ_vs_default("macd", ["fast", "slow", "signal"]), False)

    # mermaid: search-space tree
    smrows = _schema_rows()
    tree = ["```mermaid", "graph LR",
            "  T[One trial = one full strategy] --> BOX[Box / risk knobs]",
            "  T --> INDS[15 indicators]",
            "  BOX --> b1[softSL]; BOX --> b2[hardSL]; BOX --> b3[TP]; BOX --> b4[vol-gate %]",
            "  BOX --> b5[dd-breaker $]; BOX --> b6[cooldown]; BOX --> b7[flip on/off]; BOX --> b8[K confirmers]"]
    for i, (k, mode, ps) in enumerate(smrows):
        pid = f"I{i}"
        plist = ", ".join(p["name"] for p in ps) if ps else "(none — only on/off)"
        tree.append(f"  INDS --> {pid}[\"{k} — {mode}<br/>on/off + {plist}\"]")
    tree.append("```")

    score = ["```mermaid", "flowchart TD",
             "  A[Pick values for every knob<br/>box + all 15 indicators' on/off + internals] --> B[Run backtest on history]",
             "  B --> C[Split history into 5 chunks<br/>score each chunk]",
             "  C --> D{{3 objectives}}",
             "  D --> O1[median P/L ↑]; D --> O2[worst losing streak ↓]; D --> O3[win-rate ↑]",
             "  D --> E{full-period maxDD ≤ 25% of P/L?}",
             "  E -- no --> X[infeasible — thrown out]",
             "  E -- yes --> K[kept on the Pareto menu]",
             "  K --> N[NSGA-III breeds the survivors → next batch of trials]",
             "  N --> A",
             "```"]

    total_internal = sum(len(ps) for _, _, ps in smrows)
    head = (
        "---\n"
        "name: ws-i-what-was-tested\n"
        "description: WS-I — plain-language breakdown of EXACTLY what the search tuned (indicator on/off "
        "AND every internal param) with mermaid + inline plotly, plus per-TF champion full recipes incl. "
        "tuned indicator internals. Generated by docs/charts/build_tested_report.py.\n"
        "type: reference\nstatus: generated\nworkstream: WS-I\n---\n\n"
        "# WS-I — What was *actually* tested? 🍼🔬\n\n"
        "> You asked: *\"the indicators were tested on/off, but were their own internal params (EMA period, "
        "Keltner m/n, …) ever changed?\"* — **Short answer: yes, both were searched.** Read on.\n\n"
        "---\n\n"
        "## 1. The one-line answer\n\n"
        "Every indicator had **two kinds of knob searched at the same time**:\n\n"
        "1. **A switch** — use this indicator, yes or no? (`on/off`)\n"
        "2. **Its own internal dials** — *and when it was on, its internal settings were tuned too* "
        "(e.g. EMA's `fast`/`slow` lengths, Keltner's `n` window and `m` multiplier, MACD's "
        "`fast`/`slow`/`signal`).\n\n"
        f"So it was **not** \"15 on/off switches with frozen defaults.\" It was **15 switches + "
        f"{total_internal} internal dials**, all moved together by the search.\n\n"
        "**Proof in the winners:** the 4h champion runs `ema_trend` at `fast=244, slow=373` — nowhere near "
        "the textbook default `20/50`. The 1m champion runs `ema_trend` at `fast=3, slow=311`. If internals "
        "had been frozen, every champion would show the same default numbers. They don't.\n\n"
        "---\n\n"
        "## 2. The full search space (one picture)\n\n"
        "Each trial = pick a value for **every** box knob **and** every indicator's switch **and** its "
        "internals. One trial is one complete strategy.\n\n"
        + "\n".join(tree) + "\n\n"
        "---\n\n"
        "## 3. The internal dials behind each switch\n\n"
        "Every indicator's switch hides this many tunable internal dials (only **vwap** has none — there is "
        "nothing to tune on it):\n\n"
        + f_knobs + "\n\n"
        "<sub>📊 standalone copies of these charts live in `docs/charts/` once exported.</sub>\n\n"
        "### Exact ranges the search was allowed to explore\n\n"
        "| indicator | role | internal params (range / default) |\n|---|---|---|\n"
    )
    rows_md = []
    for k, mode, ps in _schema_rows():
        if ps:
            cell = "; ".join(f"`{p['name']}` {p['min']}–{p['max']} (def {p['default']})" for p in ps)
        else:
            cell = "_none — on/off only_"
        rows_md.append(f"| **{k}** | {mode} | {cell} |")
    body2 = (
        "\n".join(rows_md) + "\n\n"
        "<sub>role: **confirm** = adds a yes-vote; **veto** = can block a trade; **both** = can do either. "
        "`K` = how many confirmers must agree before a trade is allowed (also searched, 1–5).</sub>\n\n"
        "---\n\n"
        "## 4. Did the internals really move? (yes — see the winners)\n\n"
        "`ema_trend` and `macd` were the most-picked indicators. Here are the **actual tuned values the "
        "winning strategy used on each timeframe**, against the textbook default (dotted red). If internals "
        "were frozen, every bar would sit on the dotted line — they're all over the place.\n\n"
        + f_ema + "\n\n" + f_macd + "\n\n"
        "---\n\n"
        "## 5. How one trial was judged (the loop)\n\n"
        + "\n".join(score) + "\n\n"
        "---\n\n"
        "## 6. ⚠️ Correcting the \"apply directly\" assumption\n\n"
        "You said you can take the winning parameters and apply them directly. **Half-true — mind this gap:**\n\n"
        "- ✅ The **box knobs** (softSL/hardSL/TP/gate/dd/cooldown/flip/K) are in the leaderboard CSV.\n"
        "- ⚠️ The **indicator internal values** (the EMA periods etc.) were **NOT** in that CSV — the CSV only "
        "lists *which* indicators are on. The tuned internals lived only in the search database on the server.\n"
        "- ✅ **Now fixed:** I extracted the full recipes (box **+** every enabled indicator's tuned internals) "
        "into `optimize/results/wsi_champions_full.json` and laid them out in §7 below. *Those* are what you "
        "apply directly.\n\n"
        "Also remember: a champion is just the **highest-P/L** feasible point. The full per-TF **menu** "
        "(`optimize/results/<tf>_wsi_pareto.csv`) trades P/L against risk — but note that menu, too, currently "
        "carries only the on/off list, not internals (ask if you want the internals dumped for the whole front).\n\n"
        "---\n\n"
        "## 7. The full winning recipes (box + tuned indicator internals)\n\n"
        "Everything you need to reproduce each per-TF champion, including the internal values:\n\n"
    )
    chunks = [head, body2]
    for tf in TFS:
        med = CHAMP.get(tf, {}).get("median_pnl")
        chunks.append(f"### {tf}  —  median fold P/L ${med:,.0f}\n\n" + _recipe_block(tf) + "\n")
    chunks.append(
        "---\n\n## 8. The honest caveats\n\n"
        "- **Sampled, not exhaustive.** The space is astronomically large (continuous internals × on/off × "
        "box knobs). 3,000 trials/TF *samples* it intelligently (NSGA-III breeding) — it does not try every "
        "combo. Good combos may remain unfound.\n"
        "- **n=1 history (2025→2026).** Candidate generation, not proof. Re-validate any chosen recipe on the "
        "exact dashboard engine before trusting it.\n"
        "- **Some tuned internals look extreme** (e.g. an EMA `fast=3` on 1m, or `signal=94` on MACD). That's a "
        "sign of fitting to one history — sanity-check before use, especially on the fast timeframes.\n")
    out = os.path.join(_DOCS, "WS-I_WHAT_WAS_TESTED.md")
    open(out, "w").write("\n".join(chunks))
    print(f"wrote {os.path.relpath(out, _ROOT)} ({os.path.getsize(out)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
