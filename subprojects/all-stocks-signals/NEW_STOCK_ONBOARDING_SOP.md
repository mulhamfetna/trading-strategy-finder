# New-Stock Onboarding — Standard Operating Procedure (SOP)

The repeatable pipeline for adding any new instrument (a "stock": futures / ETF / equity) to the box-strategy
system end-to-end. Encodes the process the user approved on 2026-07-06 while onboarding COMEX Gold (GC) + Silver
(SI) and re-wiring E-mini S&P (ES).

---

## STEP 0 — Human-gate (ALWAYS FIRST) 🛑

Before running anything, **confirm with the user**:

1. **Same pipeline or modified?** — "Do you want this exact pipeline, or a modified one for this stock?"
   Do not proceed until they choose. If modified, capture the deltas before writing code.
2. **Contract point-value** — dollars per 1.0 point of price move. This drives every P/L number and CANNOT be
   guessed from a "Continuous" data label. Full vs micro:
   - Gold: full GC = $100/pt · micro MGC = $10/pt
   - Silver: full SI = $5,000/pt · micro SIL = $1,000/pt
   - Index E-minis: NQ = $20/pt · ES = $50/pt (micros MNQ $2 / MES $5)
3. **Shift or not** — default is **−1 workday** (business-day) box shift, applied to EVERY non-NQ instrument.
   **NQ is never shifted** (it is the frozen golden anchor).

Only after these three answers do you start.

---

## STEP 1 — Place the data

Drop the vendor files into the canonical tree the registry anchors on
(`<repo>/ALL_STOCKS`):

- Candles → `ALL_STOCKS/CANDLES/<EXCHANGE>/<PREFIX>_Continuous_Data/<PREFIX>_<TF>.csv`
  for `TF ∈ {1m,2m,5m,15m,1h,2h,4h}`. Schema: `datetime,open,high,low,close,volume`.
- Raw box → `ALL_STOCKS/BOXS/<EXCHANGE>/<TOKEN>/<TOKEN>_full_data.csv`
  (same 53-column set as `NQ_full_data.csv`; column ORDER may differ — the engine reads by name).

Guard test: `subprojects/all-stocks-signals/tests/test_comex_data_placed.py` (adapt the token list).

## STEP 2 — Shift boxes −1 workday + generate signals

Add the instrument to the `ONBOARD` table in `subprojects/all-stocks-signals/onboard_stock.py`:

```python
'<TOKEN>': dict(candle_dir=_cdir('<EXCHANGE>', '<PREFIX>_Continuous_Data'), prefix='<PREFIX>',
                box=_box('<EXCHANGE>', '<TOKEN>', '<TOKEN>_full_data.csv')),
```

Then run:

```bash
python3 subprojects/all-stocks-signals/onboard_stock.py --tokens <TOKEN>
```

**Speed / where to run it.** The Stage-1 engine is a per-candle Python loop; the 1-minute pass (millions of rows)
dominates and needs ~1 GB RAM per concurrent worker. The local box (14 GB, ~3.5 GB free) can only run it
**serially** — parallelizing the 1m pass locally risks OOM. For a fast run, offload to the **AMD server**
(32 threads, 128 GB RAM, SSH `amd-trading`) and use the parallel flag:

```bash
# on the server, in the wsg-i scratch, venv /home/dev/Mulham/.venv:
python3 onboard_stock.py --jobs 16          # fans (token,tf,preset) units across 16 processes
```

`--jobs N` is byte-identical to the serial path (proven: server-parallel SUMMARY == local-serial SUMMARY,
2026-07-06) — it only changes concurrency. Keep `--jobs 1` (default) on the laptop. `--tf 4h` restricts to one
timeframe for quick checks. Server prerequisites: rsync `src/`, `subprojects/signals/`,
`subprojects/all-stocks-signals/`, and `ALL_STOCKS/{CANDLES,BOXS}/<EXCHANGE>/` into `~/Mulham/wsg-i/`.

This shifts the box back one business day (Mon→Fri, Tue→Mon, …; loud asserts on any weekend/collision/non-backward
date), writes `shifted_boxes/<TOKEN>_full_data_shifted.csv` (**the file the backtester reads**), regenerates
Stage 1 + Stage 2 signals for 7 TF × 3 presets against the shifted box, validates the 5 invariants, and packages
`<TOKEN>_SIGNALS_DELIVERY/`. Shift bijection is unit-tested in `tests/test_onboard_shift.py`.

## STEP 3 — Register (backtester + dashboard)

1. `subprojects/all-stocks-signals/instruments.py` — add a `REGISTRY` entry with `box_csv=_shifted_box('<TOKEN>')`.
2. `subprojects/Parametric-Indicators/optimize/instruments.py` — add `<TOKEN>` to `TOKENS` and its
   `POINT_VALUE`.
3. **`subprojects/Parametric-Indicators/frontend/dashboard.html` — add `<option value="<TOKEN>"><TOKEN> (Name)</option>`
   to `#inst_select`.** ⚠ The dropdown `<option>` list is **hardcoded HTML**, NOT auto-populated from `TOKENS` — a
   backend token with no `<option>` is invisible in the UI (and `select_option` fails in headless verification).
   Then `dash.sh refresh` so the served page picks it up. (Discovered onboarding HG 2026-07-08.)
4. Update `optimize/test_instruments.py` + `test_instruments_comex.py` (`TOKENS` assertion + point-value) + a
   resolve test.

The backend accepts the token via `TOKENS`; the dashboard shows it once the `<option>` above is added. Until
optimized, it backtests with
the auto **price-scaled permissive default** (`optimize/l2/payload.instrument_l1_default`). If the instrument had a
prior champion tuned on a DIFFERENT box (e.g. a raw-box champion before a shift), retire it:
`mv optimize/results/wsh4_champions_full_<TOKEN>.json …_<TOKEN>.stale-<reason>.json` so it falls back to the
scaled default instead of being served on mismatched data.

## STEP 4 — Verify + optimizer smoke

```bash
cd subprojects/Parametric-Indicators
python3 -m pytest optimize/test_instruments.py optimize/test_instruments_comex.py -q
python3 -c "from optimize import data; d,_,b,_,_=data.load_inputs('4h','<TOKEN>'); print(len(d),len(b))"
python3 perf/check_golden.py                                   # MUST be 6/6 (NQ untouched)
python3 optimize/optimizer.py 4h --trials 1 --folds 2 --study-prefix <token>1 --instrument <TOKEN>
```

Golden 6/6 is the hard gate — a mismatch means NQ moved and is a STOP.

## STEP 5 — GATE: optimize on the server (never local)

Real per-instrument campaigns run **only on the AMD server**, only after explicit user go. Local compute is
capped at the 1-trial smoke above (a local campaign nearly broke the box on 2026-06-30). When approved: run
`--auto-trials` on 4h first, then other TFs; extract champion → `wsh4_champions_full_<TOKEN>.json`; verify the
dashboard default; run the 2026 out-of-sample check.

---

## Invariants that must always hold
- NQ is never shifted; golden stays 6/6 byte-identical after every change.
- The backtester reads the SHIFTED box for every non-NQ instrument (signals + backtest agree).
- No heavy compute on the local machine — server only, with explicit permission.
- Point-value is confirmed with the user per contract before any P/L is trusted.
- Sensitive files (`keypass.txt`, `login.txt`, `kw-full.ovpn`, `SERVER_DETIALS.md`) are never committed.
