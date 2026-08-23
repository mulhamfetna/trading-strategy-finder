# DATA & KNOWLEDGE MAP — where everything lives (authoritative, 2026-08-22)

**Read this before any workstream touches data.** On 2026-08-22 the owner unified all market
data on the AMD server and deleted the local copies. Two consequences every future agent must
internalize:

1. **Market data exists ONLY on the server** (`ssh amd-trading`, user `dev`). The local
   checkout `/mnt/data/projects/trading/` has **no** `Full_Canldes_Data/`, `ALL_STOCKS/`,
   `data/`, `2024_data/`, `2026_last_20_days_data/`, delivery bundles, or vendor zips — and
   must never grow them back. `roots.py` still *defaults* the data root to the checkout, so a
   local data-backed run fails with `FileNotFoundError` **by design** (the no-local-compute
   rule). That failure is not a bug in the code; it is the rule working.
2. **Code, evidence and records live in git** (branches `research/legacy-18-baseline` →
   `dev` → `main`) and are mirrored into server worktrees. "Local = source of truth" means
   *git*; "server = source of truth" means *data*. Never confuse the two.

Machine-generated inventory behind this page: `optimize/fwd/phase0_data_audit.py` (per-frame
coverage) and the 2026-08-22 checksum merge (131 identical / 0 conflicts / 28 pushed / 22
archives verified) recorded on issue #176.

---

## 1. The machine and how to reach it

| item | value |
|---|---|
| host | `ssh amd-trading` (78.89.209.212 / LAN 192.168.50.62), user `dev`, 32 cores / 123 GB RAM, **no GPU** |
| python | `/home/dev/Mulham/.venv/bin/python3` (numpy 2.4 · pandas 3.0 · optuna 4.9 · numba 0.65 · playwright + chromium-1228 in `~/.cache/ms-playwright`) |
| code worktrees | `~/Mulham/code` = production checkout (serves dashboard **:8200**) · `~/Mulham/earn1` = `research/legacy-18-baseline` (branch dashboard **:8250**) · `~/Mulham/wsg-i` = the **data root** (also an old rsync checkout — ⚠️ its code is STALE, never run from it) |
| env for ANY data-backed run | `WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data WSH_16Y_ROOT=/home/dev/Mulham/data_2010_1s` |
| env for the EXTENDED tape | `WSH_DATA_BASE=/home/dev/Mulham/wsg-i/FWD_EXTENDED WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/FWD_EXTENDED/data TMPDIR=/home/dev/Mulham/wsg-i/FWD_EXTENDED/tmp` |
| optimizer storage | Postgres container `wsh-pg` at `127.0.0.1:55432`, creds `~/Mulham/wsg-i/pg.env` (⚠️ `get_all_study_summaries()` hangs — use `docker exec wsh-pg psql`) |
| dashboards | :8200 prod (`~/Mulham/wsg-i/dash.sh refresh` / supervisor), :8250 branch (`cd ~/Mulham/earn1/subprojects/Parametric-Indicators && nohup env <vars> .venv python3 server.py --port 8250`) — **restart after any backend change**; kill by PORT, never `pkill` by name |
| L1 disk cache | `$TMPDIR/wsh_l1_cache/*.pkl` — keyed on PARAMS, blind to data ⇒ **every distinct data root needs its own TMPDIR**; clear after any P/L-affecting change |

---

## 2. The data roots (exact paths)

### 2.1 `~/Mulham/wsg-i` — the PRODUCTION engine root (what :8200 and every champion run read)

| what | exact path | coverage | schema / notes |
|---|---|---|---|
| NQ candles (engine's own) | `Full_Canldes_Data/drive-download-20260602T124702Z-3-001/NQ_{1m,2m,5m,15m,1h,2h,4h}.csv` | 2025-01-01 → **2026-05-19** | `datetime,open,high,low,close,volume`; ET-naive; bars labeled by START; 4h grid 18/22/02/06/10/14 |
| NQ candles, with20d variant | same dir, `NQ_<tf>_with20d.csv` | → 2026-06-09 | built by `build_plus20d_data.py`; NOT live |
| NQ box (engine reads this) | `data/full_data/NQ_full_data.csv` | box days 2025-01-01 → **2026-05-22** | 53 cols; engine uses Date + 16 W* + 16 M* level columns; daily rows = CLOSING day; `hour>=18 ⇒ next day` mapping |
| NQ box with20d | `data/full_data/NQ_full_data_with20d.csv` | → 2026-06-09 | real scraped rows, shifted by the proven script; superseded by the aug2026 box below |
| NQ box aug2026 (#179) | `data/full_data/NQ_full_data_aug2026.csv` | → **2026-08-06** | with20d + the 2026-08-22 owner export, gate E exact; **the live NQ box of the extended root** (copied there as `NQ_full_data.csv`); prod engine file still the 05-22 one |
| NQ per-year backend (dashboard 4h view) | `data/{2025_data,2026_data}/NQ_{4h,1m}_<yr>.csv`, `NQ_full_data_<yr>.csv` (+`_with20d`) | 2026 → 05-19 (with20d → 06-09) | the dashboard's second NQ backend; must stay consistent with the box above |
| 2024 NQ history | `2024_data/NQ2024_Candles/NQ2024_Continuous_Data/NQ2024_<tf>.csv` + `2024_data/NQ2024-Boxs/NQ2024/NQ_{full,day,week,month}_data.csv` | 2024-01-01 → 2024-12-31 | pushed from local 2026-08-22; used by the NQ2024 signal delivery only |
| NQ 20-day drop (raw) | `2026_last_20_days_data/NQ-2026-last-20-days-{candles,boxs}/NQ-5-6-2026*/` | 2026-05-18 → 06-09 | the source of the with20d files |
| Non-NQ candles | `ALL_STOCKS/CANDLES/<EXCH>/<TOK>_Continuous_Data/<TOK>_<tf>.csv` — EXCH: CME{ES,RTY,YM} · COMEX{GC,SI,HG} · NYMEX{CL,NG} | ES → 05-19 · GC/SI → 07-02 · RTY/YM → 07-05 · HG → 07-07 · CL/NG → 07-08 | same schema as NQ |
| ETF candles | `ALL_STOCKS/CANDLES/ETF/{QQQ,SQQQ}_Data/{ETH,RTH}/` | 2025-01-02 → 2026-05-19 | not in the 9-instrument engine; signal deliveries only |
| Non-NQ boxes RAW (scraped) | `ALL_STOCKS/BOXS/<EXCH>/<TOK>/<TOK>_full_data.csv` (RTY/YM/ES/NQ/ETFs also have `_day/_week/_month`) | all 9 → **2026-08-07** (raw dates; ETF → 05-22) | raw = UNshifted (row D = levels built from session D−1). ⚠️ NQ's file is stored in the SHIFTED convention (never re-shifted). ⚠️ ES's file WAS delivered shifted and got shifted twice (#179) — corrected 2026-08-23 to raw convention (`.pre179` backup). NQ/ES `_day/_week/_month` keep old convention; the Aug export sits alongside as `*_aug2026.csv`. Pre-merge copies: `*.csv.pre179` |
| Box export archive (2026-08-22 scrape) | `vendor_drops_local/last levels-20260823T103031Z-1-001.zip` (+ unzipped `last levels/FUTURES/<EXCH>/<TOK>/`) | 2026-05-18 → 08-07 raw, 60 rows × 9 | the drop merged by `optimize/fwd/fwd_merge_boxes.py` (gate E report in `optimize/fwd/data/fwd_box_merge_report.json`) |
| Non-NQ boxes SHIFTED (engine reads) | **in the CODE checkout**: `subprojects/all-stocks-signals/shifted_boxes/<TOK>_full_data_shifted.csv` | → **2026-08-06** (= raw 08-07 shifted −1 business day) | produced by `subprojects/all-stocks-signals/onboard_stock.py`; travels with git, so `earn1`/`code` each carry a copy |
| bundle data snapshots | `bundle_data_all/` (9 inst, → 07-08) · `bundle_data_clng/` | frozen inputs of the shareable backtester bundles | do not use as the engine root |
| delivery bundles | `<TOK>_SIGNALS_DELIVERY/` + `.zip` for CL ES GC HG NG RTY SI YM; zips only for NQ NQ2024 NQ2026L20 QQQ-ETH QQQ-RTH SQQQ-ETH SQQQ-RTH (at `wsg-i/` root) | — | customer-facing signal exports (WS-AS) |
| vendor drop archives | `vendor_drops_local/*.zip` (HG/RTY/YM July drops, drive-download-20260710 ×2, silver-gold candles/levels) | — | the raw files the onboarding SOP consumed; keep for provenance |
| champion bundles | `BOX_STRATEGY_CHAMPIONS_2026-07-14/`, `BOX_STRATEGY_CHAMPIONS_EOD_2026-07-13/` (+zips) | — | ⚠️ built on the 4-dp-rounded champions — STALE, do not ship |

### 2.2 `~/Mulham/wsg-i/FWD_EXTENDED` — the EXTENDED engine root (WS-FWD, #176)

Mirror of 2.1 for the files the engine reads, **candles extended to 2026-08-07 16:59 ET for all
9** under exact gates (Gate A splice parity 9/9 incl. volume; Gate B 54/54 resample proofs;
Gate C audit; prod checksums untouched). NQ box = the aug2026 box (→ **08-06**, since #179; was with20d → 06-09). Everything else
symlinked to prod. Own `tmp/` for the L1 cache (⚠️ params-keyed, DATA-BLIND — wipe `tmp/wsh_l1_cache`
and `tmp/wsh_vote_cache` after ANY candle or box change, or old-data books are served); `fwd_books/` =
round-1 books; `fwd_books_r2/` = round-2 books (#179: boxes → 08-06, ES corrected) + `shots/`.
Point a run here with the env line in §1. **Not yet swapped into production** (owner decision).

### 2.3 `~/Mulham/data_2010_1s` — the 16-YEAR tape (the news / earnings / extension source)

| what | exact path | coverage | notes |
|---|---|---|---|
| RAW vendor 1-second | `<TOK>.csv` (NQ ES GC SI HG CL NG RTY YM) | 2010-06-06 → 2026-08-07 | **UTC** Databento-style: `ts_event,rtype,publisher_id,instrument_id,open,high,low,close,volume,symbol`; per-contract symbols (roll-stitched) |
| derived frames | `<TOK>_Continuous_Data/<TOK>_{1s,2s,5s,15s,30s,1m,2m,5m,15m,1h,2h,4h}.csv` | same (RTY from 2017-07-09) | ET-naive, engine schema; built by `main_futures_seconds.py` in this dir. ⚠️ pre-2016 rows are DST-broken (WS-NEWS2) — fine for ≥2016 studies |
| sizes | 1s ≈ 1.7–6.8 GB per instrument; 1m ≈ 150–280 MB | ~130 GB total | |

**Proven 2026-08-21:** the 1m frames here are tick-for-tick identical to the engine's vendor
candles over their overlap (OHLC + volume, all 9). This is the legitimate source for every
future candle extension (`optimize/fwd/fwd_extend_candles.py`).

### 2.4 What is NOT on any server path and cannot be generated here

**The box levels.** The W*/M* levels are scraped output of the owner's TradingView-side
indicator; a derivability probe (ratio census, 4 instruments) showed per-period values, not
fixed multiples; no generator/Pine source exists in any repo. A new box drop is an **owner
action** (scrape → raw `<TOK>_full_data.csv` under `ALL_STOCKS/BOXS/...`, NQ under
`data/full_data/` → run the onboarding shift → commit `shifted_boxes/`). Since #179 the merge
is a script: `optimize/fwd/fwd_merge_boxes.py --probe` (tells you which convention each existing
file is in — raw files match a raw drop at shift 0, shifted files at −1 BDay) then `--apply`
(gate E: every engine column exact on the overlap; NaN↔value on the sparse xT* trend columns is
a scrape-repaint observation, recorded, existing rows kept). Current box frontier (2026-08-23):
**all 9 → 2026-08-06 in the engine convention** (NQ only in the extended root; prod NQ still 05-22).

**Box-date convention (load-bearing, #179).** Raw scrape row D = levels built from session D−1
(row 05-18 has `dOpen` = the open at 05-14 18:00). The engine convention = raw shifted −1 BDay:
row D carries D's own session/week/month (row 05-18 = first row of the new week, `dOpen` = the
open at 05-17 18:00). Check a new file against the 1m opens before shifting: if row D's `dOpen`
already equals the 18:00 open of the evening before D, the file is ALREADY shifted — shifting it
again puts next week's levels on Friday rows (that was ES until 2026-08-23).

---

## 3. Per-instrument coverage at a glance (2026-08-23)

| inst | prod candles | extended candles | 16y tape | raw box | shifted box (engine) |
|---|---|---|---|---|---|
| NQ | 2026-05-19 | 2026-08-07 | 2010→2026-08-07 | 08-07 (stored shifted = 08-06) | n/a — reads `data/full_data`: prod 05-22 · extended **08-06** |
| ES | 05-19 | 08-07 | 2010→08-07 | 08-07 | **08-06** (single shift since #179; was double-shifted → 05-21) |
| GC | 07-02 | 08-07 | 2010→08-07 | 08-07 | **08-06** |
| SI | 07-02 | 08-07 | 2010→08-07 | 08-07 | **08-06** |
| HG | 07-07 | 08-07 | 2010→08-07 | 08-07 | **08-06** |
| CL | 07-08 | 08-07 | 2010→08-07 | 08-07 | **08-06** |
| NG | 07-08 | 08-07 | 2010→08-07 | 08-07 | **08-06** |
| RTY | 07-05 | 08-07 | 2017→08-07 | 08-07 | **08-06** |
| YM | 07-05 | 08-07 | 2010→08-07 | 08-07 | **08-06** |

Point values (engine): NQ 20 · ES 50 · GC 100 · SI 5,000 · HG 25,000 · CL 1,000 · NG 10,000 ·
RTY 50 · YM 5 (`optimize/instruments.py`). The engine reads exactly three files per (inst, tf):
decision-TF CSV, 1m CSV, box CSV (`optimize/data.py::load_inputs`).

---

## 4. Knowledge that lives in GIT (evidence, calendars, champions) — committed, not on a data root

| what | path (repo) |
|---|---|
| deployed champion set `best` (+ `incumbent`/`eod`) | `subprojects/Parametric-Indicators/optimize/results/{best,cap1p,eod1p}_champions_full[_<TOK>].json` — ⚠️ `*.csv` there are gitignored |
| golden gate (NQ 6/6 byte-identical anchors) | `subprojects/Parametric-Indicators/perf/check_golden.py` |
| claims ledger (67/67) | `subprojects/Parametric-Indicators/optimize/verify/` (`run.py`, `claims_*.py`) |
| news calendar + release stamps (WS-NEWS2+) | `subprojects/Parametric-Indicators/optimize/fundamentals/data/` (+ `DATA_REQUEST_release_timestamps_2010_2026.csv` at repo root) |
| earnings acceptance stamps / E-S1 dataset | `subprojects/Parametric-Indicators/optimize/earnings/data/` |
| XNI / fusion / forward evidence | `optimize/xni/data/`, `optimize/fundamentals/*_result*`, `optimize/fwd/data/` (54 books, gate JSON, 54 screenshots) |
| deployed forecast layers + artifacts | `src/deploy/{power_forecast,two_calendar_forecast,regime_monitor}.py`; playbooks + bundles under `playbooks/` |
| workstream records | `docs/NEWS-MASTER-EXPERIMENT-RECORD.md` (eras 0–12), `docs/PROGRAMME-COMPLETE-EXPERIMENT-REPORT.md`, `docs/PROGRESS-RECORD.md`, `docs/SYSTEM-LAYERS-ANALYSIS.md`, `docs/WS-*-FULL-RECORD.md`, pre-registrations `docs/*-PREREGISTRATION.md` |

---

## 5. Recipes (copy-paste)

```bash
# any engine/champion run on PRODUCTION data
ssh amd-trading
cd ~/Mulham/earn1/subprojects/Parametric-Indicators     # or ~/Mulham/code/... for the released code
env WSH_DATA_BASE=/home/dev/Mulham/wsg-i WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/data \
    WSH_16Y_ROOT=/home/dev/Mulham/data_2010_1s /home/dev/Mulham/.venv/bin/python3 <script>

# the same on the EXTENDED tape (own cache!)
env WSH_DATA_BASE=/home/dev/Mulham/wsg-i/FWD_EXTENDED WSG_DATA_ROOT=/home/dev/Mulham/wsg-i/FWD_EXTENDED/data \
    TMPDIR=/home/dev/Mulham/wsg-i/FWD_EXTENDED/tmp /home/dev/Mulham/.venv/bin/python3 <script>

# audit coverage (prints first/last stamp of every frame the engine would load)
python3 optimize/fwd/phase0_data_audit.py
# extend candles from the 16y tape into a parallel root (gated)
WSH_FWD_ROOT=... python3 optimize/fwd/fwd_extend_candles.py
# onboard a new vendor/box drop (shift −1 BDay, signals, registry)
python3 subprojects/all-stocks-signals/onboard_stock.py --tokens <TOK> --jobs 16
# dashboard visual gate — browser ON THE SERVER (the local box froze under it)
env WSH_GATE_URL=http://127.0.0.1:8250/ WSH_GATE_CHROME=/home/dev/.cache/ms-playwright/chromium-1228/chrome-linux64/chrome \
    python3 optimize/fwd/fwd_dashboard_gate.py --books <dir> --shots <dir> --out <json>
# bring evidence home (git is the truth for evidence): scp → optimize/<ws>/data/ → gitignore `!` exception → commit
```

---

## 6. Legacy server directories (campaign scratch — NOT sources of truth)

`~/Mulham/{wsg-h, fa-m1, l2v2, gap2, gap3, gap4, q99, risk2, regime-edge, regime-hmm, chronos2,
tfm-repro, meta-prophet, shared, runs}` and the `*.rsync-retired-2026-08-01` copies are the
remains of closed workstreams (their verdicts live in the records). Read for archaeology only;
never point an engine at them. `~/Mulham/wsg-i` itself still contains an old code checkout
beside the data — use it for DATA paths only.

## 7. Failure modes this page exists to prevent

- *"FileNotFoundError: /mnt/data/projects/trading/Full_Canldes_Data/..."* → you ran locally; run on the server with the env line.
- *"The dashboard shows different numbers than my run"* → different data root (prod vs extended) or a shared `TMPDIR` cache; pin both.
- *"No entries after June"* → the box feed ends there (§2.4); candles are not the limit.
- *"The with20d / bundle_data / BOX_STRATEGY dirs look newer"* → they are variants/snapshots, not the engine root; the engine root is §2.1 as listed.
- *"Local test needs data"* → it must skip or run on the server; do not restore local trees.
