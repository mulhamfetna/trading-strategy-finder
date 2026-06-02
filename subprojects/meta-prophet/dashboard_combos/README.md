# WS-G per-combo dashboard clones

Sibling standalone dashboards for the Workstream-G combination tournament — **one folder per
volatility lever** (`none`, `S`, `G`, `S+G`), each cloned from the verified `../dashboard/index.html`
with the config dropdown repurposed to the **three entry modes**: `normal` / `flipped` /
`cusum_flip` (CUSUM dynamic flip). The **main `dashboard/` is never touched.**

Each dashboard keeps the original window picker (2025 / 2026 / full) and panels (candlesticks +
trade markers, adaptive SL/TP distances, regime gate, equity curve). Open any
`dashboard_combos/<lever>/index.html` directly in a browser (data is embedded in `data.js`, no
server needed).

## Generate / regenerate
```bash
python3 subprojects/meta-prophet/scripts/45_wsg_dashboard_factory.py
```
The `data.js` files (~3 MB each) are **git-ignored** (regenerable); the `index.html` clones + this
README are tracked.

## Reading them — important caveat
- `normal` and `flipped` are exact engine runs.
- `cusum_flip` is the **realizable** per-trade flip: each trade follows the causal CUSUM decision
  (notes/32), taking the real flipped trade when one exists at that entry bar, else staying normal.
  Because **flipping changes the trade set** (772 normal vs 750 flipped trades), this is an
  approximation — a *true* dynamic flip needs per-bar flip support in the engine (entry **and**
  exit), logged as a follow-up. See `../notes/41_phase_G_combination_tournament.md` §2b.
- All flip results are **n=1-illustrative** (one regime change). The robust, exact edge is the
  volatility **gate** (`G` / `S+G`), which halves drawdown without any flipping.

Engine: verified single-contract clone only (`../engine_clone/`). No 1-1-2 ladder.
