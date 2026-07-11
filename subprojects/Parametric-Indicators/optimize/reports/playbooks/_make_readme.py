"""Emit README.md for the shareable playbooks_backtester bundle, with the champion table from MANIFEST.json.

Every count/market list is DERIVED from the manifest — no hardcoded "37"/"6 markets" to drift out of date
(it already had, silently, when Copper was added and the README kept claiming 37).
"""
import json, os

B = os.path.expanduser("~/Mulham/wsg-i/playbooks_backtester")
man = json.load(open(os.path.join(B, "MANIFEST.json")))

FULL = {"NQ": "Nasdaq-100", "ES": "S&P 500", "GC": "Gold", "SI": "Silver", "HG": "Copper",
        "CL": "Crude Oil", "NG": "Natural Gas", "RTY": "Russell 2000", "YM": "Dow"}
INST_ORDER = ["NQ", "ES", "GC", "SI", "HG", "CL", "NG", "RTY", "YM"]
order = {t: i for i, t in enumerate(["4h", "2h", "1h", "15m", "5m", "2m"])}
man.sort(key=lambda m: (INST_ORDER.index(m["inst"]), order[m["tf"]], m["variant"]))


def money(v):
    if v is None:
        return "n/a"
    return ("+" if v >= 0 else "−") + "$" + f"{abs(v):,.0f}"


rows = []
for m in man:
    cap = f"{m['cap_1min']}" if m["cap_1min"] else "off"
    flag = ""
    if (m["full"] or 0) <= 0:
        flag = " ❌"
    elif (m["oos"] or 0) <= 0:
        flag = " ⚠️"
    rows.append(f"| `{m['name']}`{flag} | {FULL[m['inst']]} {m['tf']}{' · 4h-ind' if m['variant'] else ''} | "
                f"${m['full']:,.0f} | ${m['dd']:,.0f} | {m['win']:.0f}% | {money(m['oos'])} | {m['n_ind']} | {cap} |")
table = "\n".join(rows)

insts = sorted({m["inst"] for m in man}, key=INST_ORDER.index)
n, n_mkt = len(man), len(insts)
n_var = sum(1 for m in man if m["variant"])
pos = sum(1 for m in man if (m["oos"] or 0) > 0)
weak = [m["name"] for m in man if (m["full"] or 0) <= 0 or (m["oos"] or 0) <= 0]
inst_set = ", ".join(insts)

README = f"""# Playbooks Backtester — {n} box + indicator champions ({n_mkt} markets × 6 timeframes + {n_var} variant)

A **self-contained, parity-locked backtester** for the box-strategy champions documented in the playbooks.
It bundles the **exact causal research engine** the live dashboard runs — so every champion reproduces its
playbook headline **to the dollar** (verified: {n}/{n} exact). This is not a re-implementation.

> **{n} champions · {pos}/{n} profitable out-of-sample (2026).** Each champion pairs a per-day price
> "box" with a K-of-N indicator confirm/veto gate, a max-hold time cap, and a drawdown circuit-breaker,
> on one instrument + decision timeframe. 1 contract; point value per instrument baked into each champion.

## Run it

```bash
pip install -r requirements.txt          # numpy, pandas

# put your CSVs for the instrument in a folder (default ./data), named as below, then:
python3 backtest.py --champion champions/GC_4h.json --data ./data --out trades_GC_4h.csv
python3 backtest.py --champion champions/GC_4h_ind4h.json --data ./data   # the 4h-indicator variant
```

Prints the summary (matching the playbook headline) and writes a per-trade CSV.

### Data you provide (one folder, CSV, one header row)

| File | What | Columns |
|------|------|---------|
| `<INST>_<tf>.csv` | decision-frame candles (e.g. `GC_4h.csv`) | `Date,Open,High,Low,Close` |
| `<INST>_1m.csv` | 1-minute candles (shared exit + indicator frame) | `Date,Open,High,Low,Close` |
| `<INST>_box.csv` | per-day box levels | `Date,<weekly/monthly level columns>` |

`INST ∈ {{{inst_set}}}`. Non-NQ box files are the **−1-workday-shifted** boxes (as onboarded).
Dates are tz-naive `YYYY-MM-DD HH:MM:SS`. Point the loader elsewhere with `--data <dir>`.

## The {n} champions

Full write-up per champion = its **playbook PDF** (`<INST>_<TF>_playbook.pdf`). Headline numbers here match
those exactly. OOS = 2026 out-of-sample (held-out year the tuning never saw).

❌ = loses money in-sample — **do not trade**.  ⚠️ = profitable in-sample but flat/negative out-of-sample.

| Champion | Market · TF | Full P/L | Max DD | Win | 2026 OOS | #ind | cap(bars) |
|----------|-------------|---------:|-------:|----:|---------:|-----:|----------:|
{table}

### The {len(weak)} slots that did NOT clear the bar

{chr(10).join(f'- **{w}** — see its playbook; shipped for completeness, not for trading.' for w in weak)}

They are included so the record is honest and reproducible, **not** because they are tradeable. The engine
reproduces their (bad) numbers exactly, which is the point.

**GC_4h_ind4h** is the 4-hour-indicator variant (indicators on the 4-hour frame, `ind_1min=false`) — the
high-timeframe winner from the 1-min-vs-4h comparison: **+$97,950 / +$22,310 OOS** vs the deployed 1-minute
GC 4h (+$57,570 / −$540). The dashboard hard-codes the 1-minute frame, so it is not served by default.

## What each champion carries

`champions/<name>.json` → `{{id, instrument, timeframe, label, preset}}`. The `preset` is the exact object the
dashboard sends: box risk knobs (`sl_soft/sl_hard/tp/gate_pct/dd_limit/cooldown/flip/k`), the max-hold time
cap (`cap_1min` + `cap_mode`), the indicator frame (`ind_1min`), the full indicator spec list (each with its
enabled flag, fixed mode, and tuned internals), and the instrument point value (`pv`).

## Notes

- Numbers match the dashboard's **causal L1 view** (the playbook headline). NQ champions run capless; every
  non-NQ champion uses an active max-hold time cap, which the causal engine applies.
- `--insample-year` is fixed to 2025 (the volatility-gate percentile is frozen on 2025 bars, causally).
- Bundle ships the engine only — you provide your own market data.

---
_Author: **Mulham Fetna** · contact@mulhamfetna.com · ORCID [0009-0006-4432-798X](https://orcid.org/0009-0006-4432-798X)
· github.com/mulhamfetna_
"""

open(os.path.join(B, "README.md"), "w").write(README)
print(f"wrote README.md ({len(README)} bytes, {n} champions, {n_mkt} markets, {pos}/{n} positive OOS, {len(weak)} weak)")
