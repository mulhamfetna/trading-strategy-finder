"""Phase B — market-structure TABLES (LL/HL/HH/LH) + IFVG / breaker / CISD events.

Delivers the new task: classify every confirmed CLOSE-based swing pivot as HH/LH (highs) or HL/LL (lows) on
the 4h decision frame across 2024–2026, at swing strengths swing_l ∈ {2,3,5}; plus per-bar IFVG, breaker-block
and CISD (standard) event tables. All detectors are causal (`indicators/smc.py`). Definitions: DEFINITION_BOOK.md.

Emits to results/:
  structure_swings_l{2,3,5}.csv   — chronological labeled pivots (time, price, kind, label, prior_ref, delta)
  structure_swings_summary.csv    — HH/HL/LH/LL counts per swing_l and per year
  structure_events_l3.csv         — non-zero IFVG/breaker/CISD signal bars at the headline swing_l=3
  STRUCTURE_TABLES.md             — rendered markdown tables

Usage:  python3 study_range_regime/structure_tables.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

_PI = Path(__file__).resolve().parents[1]
if str(_PI) not in sys.path:
    sys.path.insert(0, str(_PI))
from indicators import smc                                # noqa: E402
from optimize.sub.data_2024_2026 import load_bundle       # noqa: E402

HERE = Path(__file__).resolve().parent
RES = HERE / "results"
SWINGS = [2, 3, 5]
HEADLINE = 3


def swing_table(df4: pd.DataFrame, swing_l: int) -> pd.DataFrame:
    """Chronological labeled swing pivots for one swing strength."""
    c = df4["Close"].to_numpy(float)
    date = pd.to_datetime(df4["Date"]).to_numpy()
    kind, label, conf = smc.swing_labels(c, swing_l)
    rows = []
    last_high = last_low = None
    for i in np.nonzero(kind != 0)[0]:
        k = "high" if kind[i] == 1 else "low"
        prior = last_high if kind[i] == 1 else last_low
        rows.append(dict(
            pivot_time=pd.Timestamp(date[i]), pivot_price=round(float(c[i]), 2), kind=k,
            label=label[i] or "FIRST",
            prior_ref=(round(float(prior), 2) if prior is not None else np.nan),
            delta_pts=(round(float(c[i] - prior), 2) if prior is not None else np.nan),
            confirmed_time=pd.Timestamp(date[conf[i]]) if 0 <= conf[i] < len(date) else pd.NaT))
        if kind[i] == 1:
            last_high = c[i]
        else:
            last_low = c[i]
    return pd.DataFrame(rows)


def _md_table(df: pd.DataFrame, cols, title: str, limit: int | None = None) -> str:
    d = df[cols].copy()
    for tc in [x for x in cols if x.endswith("_time")]:
        d[tc] = pd.to_datetime(d[tc]).dt.strftime("%Y-%m-%d %H:%M")
    if limit is not None and len(d) > limit:
        d = pd.concat([d.head(limit // 2), d.tail(limit // 2)])
        note = f"\n\n*(showing first/last {limit} of {len(df)} rows; full data in CSV)*"
    else:
        note = ""
    head = "| " + " | ".join(cols) + " |"
    sep = "|" + "|".join(["---"] * len(cols)) + "|"
    lines = [head, sep] + ["| " + " | ".join(str(r[c]) for c in cols) + " |" for _, r in d.iterrows()]
    return f"### {title}\n" + "\n".join(lines) + note


def main() -> int:
    RES.mkdir(parents=True, exist_ok=True)
    df4, _df1, _box, _vf, _months = load_bundle()
    yr = pd.to_datetime(df4["Date"]).dt.year

    md = ["# Market-structure tables — LL/HL/HH/LH + IFVG/breaker/CISD (4h, 2024–2026)\n",
          "Close-based swing pivots (`indicators/smc.py`), causal (a pivot confirms `swing_l` bars later). "
          "Definitions & locked decisions: `DEFINITION_BOOK.md`.\n"]

    # ---- swing label tables at each strength ----
    summ = []
    for L in SWINGS:
        t = swing_table(df4, L)
        t.to_csv(RES / f"structure_swings_l{L}.csv", index=False)
        cnt = t["label"].value_counts().to_dict()
        row = dict(swing_l=L, n_pivots=len(t),
                   HH=cnt.get("HH", 0), HL=cnt.get("HL", 0), LH=cnt.get("LH", 0), LL=cnt.get("LL", 0),
                   FIRST=cnt.get("FIRST", 0))
        summ.append(row)
        print(f"swing_l={L}: {len(t)} pivots  HH={row['HH']} HL={row['HL']} LH={row['LH']} LL={row['LL']}")
        if L == HEADLINE:
            md.append(_md_table(t, ["pivot_time", "pivot_price", "kind", "label", "prior_ref", "delta_pts",
                                    "confirmed_time"], f"Swing pivots (swing_l={L}, headline)", limit=40))

    # per-year label breakdown at headline strength
    t3 = swing_table(df4, HEADLINE)
    t3 = t3.assign(year=pd.to_datetime(t3["pivot_time"]).dt.year)
    by_year = t3.pivot_table(index="year", columns="label", values="pivot_price", aggfunc="count",
                             fill_value=0).reset_index()
    pd.DataFrame(summ).to_csv(RES / "structure_swings_summary.csv", index=False)
    md.append("### Label counts per swing strength\n" +
              pd.DataFrame(summ).to_markdown(index=False))
    md.append(f"### Per-year label counts (swing_l={HEADLINE})\n" + by_year.to_markdown(index=False))

    # ---- IFVG / breaker / CISD events at headline strength ----
    o = df4["Open"].to_numpy(float); h = df4["High"].to_numpy(float)
    lo = df4["Low"].to_numpy(float); c = df4["Close"].to_numpy(float)
    ev = pd.DataFrame({"time": pd.to_datetime(df4["Date"]), "close": np.round(c, 2),
                       "ifvg": smc.ifvg(h, lo, c),
                       "breaker": smc.breaker_blocks(o, h, lo, c, swing_l=HEADLINE),
                       "cisd": smc.cisd(o, c)})
    nz = ev[(ev[["ifvg", "breaker", "cisd"]] != 0).any(axis=1)].reset_index(drop=True)
    nz.to_csv(RES / "structure_events_l3.csv", index=False)
    ev_summ = pd.DataFrame([
        dict(signal="ifvg", bullish=int((ev.ifvg == 1).sum()), bearish=int((ev.ifvg == -1).sum())),
        dict(signal="breaker", bullish=int((ev.breaker == 1).sum()), bearish=int((ev.breaker == -1).sum())),
        dict(signal="cisd", bullish=int((ev.cisd == 1).sum()), bearish=int((ev.cisd == -1).sum())),
    ])
    md.append("### IFVG / breaker / CISD — bar counts (swing_l=3)\n" + ev_summ.to_markdown(index=False))
    print("\nevent bar-counts:\n", ev_summ.to_string(index=False))
    print(f"non-zero event bars: {len(nz)} / {len(ev)}")

    (RES / "STRUCTURE_TABLES.md").write_text("\n\n".join(md) + "\n")
    print(f"\nwrote structure_swings_l*.csv, _summary.csv, _events_l3.csv, STRUCTURE_TABLES.md to {RES}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
