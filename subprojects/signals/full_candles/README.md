# Full-candles signals — all timeframes

This folder extends the Stage 1 / Stage 2 signal pipeline (previously run only on
the **4h** candle file) to **all seven timeframes** shipped in the project-root
`Full_Canldes_Data/` drop:

```
NQ_1m  NQ_2m  NQ_5m  NQ_15m  NQ_1h  NQ_2h  NQ_4h
```

All seven span **2025-01-01 → 2026-05-19** and are scored against the **same boxes**
(`data/full_data/NQ_full_data.csv`) using the **exact same methodology** as before —
the driver imports and reuses the frozen `generate_stage1.py` and
`stage1_0_reverse_signals/generate_stage2.py` code paths, so results cannot drift.
(Verified: the `NQ_4h` outputs are byte-identical to the committed originals.)

## What is produced per timeframe × preset

For each timeframe and each preset (`full`, `2025`, `2026`) the driver writes the
**three artifacts** the project defines:

| # | Artifact | Path | What it is |
|---|---|---|---|
| 1 | **all-signals** | `<TF>/signals_<TF>_<preset>.csv` | Stage 1 per-(candle, box) labels incl. `hold`. The "all signals" mirror. |
| 2 | **holds-dropped** | `<TF>/no_holds/signals_<TF>_<preset>_no_holds.csv` | Same rows filtered to `signal ∈ {long, short}`. The "holds dropped" mirror. |
| 3 | **reverse-signals** | `<TF>/reverse_signals_<TF>_<preset>.csv` + `<TF>/by_direction/{long_to_short,short_to_long}_<TF>_<preset>.csv` | Stage 2 reverse windows: `window_high` = **max high**, `window_low` = **min low**, direction-aware `tp`/`sl`, `holds_between`. |

### Folder layout

```
full_candles/
├── generate_full_candles.py     # the driver (reuses the frozen Stage 1 + Stage 2)
├── SUMMARY.csv                   # row/window counts for every (timeframe, preset)
├── README.md
└── <TF>/                         # one per timeframe, e.g. NQ_15m/
    ├── signals_<TF>_full.csv         # (1) all signals
    ├── signals_<TF>_2025.csv
    ├── signals_<TF>_2026.csv
    ├── no_holds/                     # (2) holds dropped, long/short only
    │   ├── signals_<TF>_full_no_holds.csv
    │   ├── signals_<TF>_2025_no_holds.csv
    │   └── signals_<TF>_2026_no_holds.csv
    ├── reverse_signals_<TF>_full.csv   # (3) reverse signals (max-high / min-low)
    ├── reverse_signals_<TF>_2025.csv
    ├── reverse_signals_<TF>_2026.csv
    └── by_direction/
        ├── long_to_short_<TF>_{full,2025,2026}.csv
        └── short_to_long_<TF>_{full,2025,2026}.csv
```

## Methodology (unchanged — see the parent specs)

- **Stage 1 rule** (per candle, per active box level-pair): `touched AND green AND
  close>upper → long`; `touched AND red AND close<lower → short`; else `hold`.
  Touch is inclusive (`<=`/`>=`), close-vs-edge is strict (`>`/`<`), doji is `hold`.
  See `../docs/MASTER.md` and `../truth_table.md`.
- **Stage 2 rule**: collapse to one state per candle (`long`/`short`/`hold`), scan for
  reverse windows (long→…→short or short→…→long, holds permitted between), emit
  `window_high`/`window_low` and tp/sl keyed to the anchor candle's color.
  See `../stage1_0_reverse_signals/docs/MASTER.md`.
- **Boxes are timeframe-independent**: weekly/monthly levels keyed to the box-date,
  so every timeframe reuses the one unified box CSV. The candle→box-date mapping
  (`hour >= 18 → +1 day`) is hour-based, hence identical across timeframes.
- **Preset split** matches the original: candles are filtered by **calendar year**
  (2025 rows ⊎ 2026 rows = full rows), and Stage 2 runs **independently** per preset
  — so a reverse window straddling the year boundary appears only in `full`.

## Regenerate

```bash
# all 7 timeframes × {full, 2025, 2026}
python3 subprojects/signals/full_candles/generate_full_candles.py

# subset
python3 subprojects/signals/full_candles/generate_full_candles.py --timeframes NQ_4h NQ_1h
python3 subprojects/signals/full_candles/generate_full_candles.py --presets full
```

> CSV outputs are git-ignored (regenerable); only the driver + this README are tracked,
> consistent with the rest of the project.
