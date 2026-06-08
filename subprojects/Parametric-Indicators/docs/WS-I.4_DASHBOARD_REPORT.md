---
name: ws-i4-dashboard-report
description: WS-I.4 completion report — the standalone Parametric-Indicators dashboard that drives the confirmation/veto layer end-to-end. Schema-driven indicator panel (no hardcoding), backend wiring through build_payload, server /api/config schema endpoint, two-phase generation report, and per-entry vote-attribution logging. Off-by-default ⇒ exact box parity; bad params surface as ParamError → HTTP 400 (no silent fallback). 80 tests + parity locks green.
type: report
status: complete
created: 2026-06-08
workstream: WS-I
---

# WS-I.4 — Indicator Dashboard: Completion Report

## 0. TL;DR
The I.3 engine layer (15 indicators + confirm/veto K-rule + retrace-fill + live-B1 carry engine) is
now **driven end-to-end from an independent dashboard**. Every indicator parameter is exposed and
**nothing is hardcoded in the frontend** — the panel is built from a schema the backend publishes. A
bad parameter is **never silently clamped**: it raises `ParamError`, which the server returns as an
HTTP **400** banner in the UI. Two new observability surfaces were added per the directive: a
**Phase-1 generation report** (how many SMC structures were generated, with which params) and
**per-entry vote attribution** (every indicator's opinion at the signal bar, with an `active` flag,
in both the trade-log line and as colour-coded chips). Off-by-default still reproduces the box+vol
strategy **exactly**. Built test-first: **80 tests green** + the original engine parity locks.

This closes I.4. The workstream is now at the **I.5 hard pause** for team-leader sign-off.

---

## 1. What I.4 had to deliver (from task.md)
The dashboard step required, verbatim in intent:
1. An **independent dashboard** for the indicator layer (not a fork of the box dashboard's internals).
2. **All indicator params exposed** — no hidden constants, no magic numbers buried in code.
3. **No silent fallbacks** — an invalid/missing param must fail loudly and visibly, never be
   silently corrected.
4. **Logs and reports updated** — the generation phase and the per-trade decision must be
   observable, including *why* each entry was (or was not) confirmed.

All four are delivered. The sections below map each to its implementation and its test.

---

## 2. Architecture — how a click becomes a backtest
```
frontend/index.html                         server.py (stdlib HTTP, no deps)
  GET /api/config ───────────────────────►  /api/config → {preset, bounds, windows,
   │  buildIndicatorPanel(schema)                          indicator_schema: library.schema()}
   │  (panel built from schema — NO hardcoded keys)
   ▼
  user toggles enabled/mode/params/retrace/wait,
  sets K + gen(swing_l, golf_n), hits "Run Backtest"
   │  params() → {sl_soft,…, window, indicators:[…], k, gen:{…}}
   ▼
  POST /api/backtest ───────────────────►  strategy.build_payload(DF4,DF1,BOX,VF,N2025, params)
                                              │  validate_params  → ParamError ⇒ 400 (no clamp)
                                              │  library.from_specs(indicators)
                                              │  runner.build_layer(df, box, inds, k, vol_gate)
                                              │     → (gate_used, entry_resolver, veto_mask)
                                              │  generate.generate_structures(…)  → gen_report
                                              │  engine.backtest(entry_gate, entry_resolver, veto_mask)
                                              │  attrib(signal_idx) per ENTRY  → ev["indicators"]
                                              ▼
                                            payload {events, equity, meta:{summary, gen_report, …}}
   ◄──────────────────────────────────────  200 (or 400 {error} / 500 {error})
  renders: equity curve · event log w/ vote chips · #genpanel gen report · summary
```
Key property: **`entry_resolver=None` / no enabled indicator ⇒ byte-for-byte the verified engine** ⇒
the dashboard with everything off is the box+vol strategy, exactly.

---

## 3. Deliverable 1 — schema-driven panel (no hardcoding)

### Backend: `library.schema()` (`indicators/library.py`)
`SCHEMA` is a per-indicator metadata table (display label, the tunable params with their types/
defaults/bounds, and which `mode`s the indicator supports). `schema()` returns
`[{key, label, params, modes, …}, …]` for every key in `REGISTRY` — the single source of truth for
what the UI may show. `from_specs(specs)` is the inverse: it takes the panel's `indicators` list of
`{key, enabled, mode, params, retrace, wait}` dicts and constructs the live `Indicator` objects,
validating strictly (unknown key, bad mode, bad param → `IndicatorParamError`).

### Server: `/api/config` (`server.py`)
`/api/config` now embeds `"indicator_schema": library.schema()` alongside the existing preset/
bounds/windows. The frontend pulls keys, param names, defaults, bounds and the mode enum **from this
payload** — there is no indicator list, no param name, and no default literal hardcoded in
`index.html`.

### Frontend: `buildIndicatorPanel` / `indicatorSpecs` / `applyIndicatorSpecs`
On load, `buildIndicatorPanel(schema)` renders `#indpanel` row-per-indicator: an enable checkbox,
the mode selector (confirm/veto/both), the per-indicator numeric params, and the per-indicator
`retrace` + `wait` inputs. `indicatorSpecs()` serialises the panel back into the `indicators` list
for the request; `applyIndicatorSpecs(...)` restores it from a saved form. A separate **Confirmation**
group holds `K`, `gen_swing_l`, `gen_golf_n`. Because the panel is generated, adding a 16th indicator
later requires **zero** frontend edits — it appears automatically from the schema.

**Test:** `tests/test_library.py` covers `schema()` shape and `from_specs` round-trip/validation.

---

## 4. Deliverable 2 — backend wiring through `build_payload`

`strategy.build_payload` is the live entrypoint shared by the server. I.4 wired the indicator layer
into it without disturbing the box path:

- `validate_params` now accepts and strictly validates `indicators` / `k` / `gen` (each bad case →
  `ParamError`; e.g. `k=0`, unknown key, `K > N_confirm`).
- When `specs` is non-empty it builds the layer via `runner.build_layer(df, box, inds, k, vol_gate)`
  → `(gate_used, entry_resolver, veto_mask)`, and for SMC indicators produces
  `meta.gen_report` from `generate.generate_structures(ctx, swing_l, golf_n)`.
- The engine is then run with `(entry_gate=gate_used, entry_resolver=entry_resolver,
  veto_mask=veto_mask)`. With no specs all three collapse to the box defaults and the
  `entry_resolver=None` carve-out keeps the engine byte-for-byte identical.

**Tests (`tests/test_build_payload.py`, 9):** empty `indicators` == baseline summary; a disabled
indicator == baseline `n_taken`/`pnl`; an enabled **veto** never increases trades; `K>N` / unknown
key / `k=0` each raise `ParamError`; an SMC indicator yields a `gen_report` with the requested params.

---

## 5. Deliverable 3 — no silent fallback (loud failure)

The whole chain is fail-loud:
- `strategy.validate_params` raises `ParamError` on any invalid/missing/contradictory parameter.
- `library.from_specs` raises `IndicatorParamError` on a bad indicator spec.
- `server.do_POST` catches `ParamError` and returns **HTTP 400 `{"error": …}`** (a red banner in the
  UI), explicitly **not** clamping — the server comment says so. Genuine exceptions return 500.

There is no code path that quietly substitutes a default for a bad input. (This also removed the
earlier "3-bar expiry" silent default that an earlier draft had — deleted as a hidden fallback.)

**Tests:** the three `pytest.raises(ParamError)` cases above; manual UI check = a 400 banner on
`K=3` with a single confirmer, and on an unknown key.

---

## 6. Deliverable 4 — logs & reports (observability)

### 6a. Phase-1 generation report (`meta.gen_report`)
When any SMC indicator is enabled, the two-phase generator runs first and emits a report:
`{params:{swing_l, golf_n}, bars, n_bull_fvg, n_bear_fvg, …}` — i.e. *what was generated and with
which knobs*, before any backtest decision is made (decision #11: generate structures, then
backtest). The frontend renders this in `#genpanel`.

**Test:** `test_smc_indicator_produces_generation_report` asserts the report is present, echoes the
exact `{swing_l, golf_n}`, and reports a positive bar count + FVG counts.

### 6b. Per-entry vote attribution (the new logging)
This is the headline observability add. On **every ENTRY event**, `build_payload` attaches the
opinion of **every** indicator at that entry's `signal_idx`:

```python
attrib = None    # per-entry indicator vote attribution
...
_ctx = runner.market_context(d4); _bdir = runner.box_direction_int(d4, box)
_votes = {id(i): i.vote(_ctx, _bdir) for i in inds}   # computed once, reused per entry
def attrib(sidx):
    rows = []
    for i in inds:
        v = int(_votes[id(i)][sidx]) if 0 <= sidx < len(_votes[id(i)]) else 0
        rows.append({"key": i.key, "active": int(i.config.enabled), "mode": i.config.mode,
                     "vote": ("confirm" if v == 1 else "veto" if v == -1 else "neutral"),
                     "params": dict(i.config.params)})
    return rows
```

The ENTRY event then carries:
- `ev["indicators"]` — the full row list (decision #1: **every** indicator is logged, even disabled
  ones, which appear with `active: 0`), and
- a human summary appended to the log line: `… | K={k}: {nc} confirm / {nv} veto of {N} active`.

The frontend renders these as colour-coded chips per entry (`.chip.confirm/veto/neutral/off`) so a
reviewer can see at a glance *which* indicators carried each trade and which were merely present.
The votes array is computed **once** per backtest and indexed by `signal_idx`, so attribution is
O(entries), not O(entries × bars).

**Tests:** `test_entry_events_carry_vote_attribution` (all indicators present incl. the disabled one
with `active:0`; the summary text contains "confirm"/"veto") and `test_no_indicators_no_attribution`
(with no specs, ENTRY events carry **no** `indicators` key — i.e. the box-only path is untouched).

---

## 7. Parity & invariants (still held)
- **Off-by-default ⇒ exact box parity** — no specs / all-disabled ⇒ `gate_used==vol_gate`,
  `entry_resolver=None`, `veto_mask` all-false; engine path is byte-for-byte the verified engine.
  Original locks unchanged: `test_parity.py` **+$7,735 / $3,670 / 66**, `test_fast_parity.py` OK.
- **No-look-ahead** — attribution reads the same closed-bar vote series the gate used; nothing peeks
  forward.
- **No silent fallback** — bad params → `ParamError` → 400 banner.

---

## 8. Test evidence (80 tests, all green)
| Suite | n | Adds in I.4 |
|---|---:|---|
| test_classic | 15 | (I.3) primitive math |
| test_confirm | 14 | (I.3) config/vote/K-rule/wait |
| test_library | 9 | **+2**: `schema()` shape, `from_specs` round-trip/validation |
| test_smc | 8 | (I.3) FVG/structure/golf/OB |
| test_timing | 6 | (I.3) retrace resolver |
| test_generate | 3 | (I.3) two-phase generator |
| test_integration | 12 | (I.3) real-data parity/carry/veto-abort |
| test_layer | 4 | `build_layer` / `veto_mask` composition |
| test_build_payload | 9 | **+2**: vote attribution present / absent; (plus gen-report, parity, ParamError) |
| **Total** | **80** | + original engine parity locks |

`python3 -m pytest tests/ -q` → **80 passed**.

---

## 9. File map (changed/added in I.4, all under `subprojects/Parametric-Indicators/`)
- `strategy.py` — `validate_params` accepts indicators/k/gen; `build_payload` builds the layer,
  runs the engine with (gate_used, entry_resolver, veto_mask), emits `meta.gen_report`, and attaches
  **vote attribution** to ENTRY events (the `attrib` closure above).
- `server.py` — `/api/config` returns `indicator_schema`; `/api/backtest` forwards full params;
  `ParamError → 400` (no clamp).
- `indicators/library.py` — `SCHEMA`, `schema()`, `from_specs()`.
- `indicators/runner.py` — `build_layer`, `veto_mask` (composition helpers).
- `frontend/index.html` — schema-built `#indpanel`, Confirmation group (K/gen), `params()`/`setForm`
  send+restore indicators/k/gen, `#genpanel` gen report, per-entry vote chips.
- `tests/test_layer.py` (4), `tests/test_build_payload.py` (+2), `tests/test_library.py` (+2).
- `WS-I_PROGRESS.md` — I.4 → ✅ complete, I.5 → 🚦 READY (hard pause).

---

## 10. How to review (I.5)
1. `python3 server.py --port 8200` → open `http://localhost:8200/`.
2. **Parity:** leave all indicators off, Run Backtest — confirm the summary matches the box+vol
   winner; ENTRY log lines have **no** vote chips.
3. **Veto:** enable **ADX** in `veto` mode (threshold 25), K=1 — trade count should **drop**; chips
   show ADX veto on filtered entries.
4. **Confirm + attribution:** enable **RSI** confirm, K=1 — every ENTRY line shows
   `K=1: n confirm / m veto of … active` and chips per indicator (disabled ones greyed `off`).
5. **Loud failure:** set **K=3** with a single confirmer → expect a red **400** banner (no silent
   clamp). Same for an unknown indicator key.
6. **Generation report:** enable an SMC indicator (e.g. FVG), set `gen_swing_l`/`gen_golf_n`, Run —
   `#genpanel` shows the structures generated with those exact params.

---

## 11. Deferred to later phases
- **I.6** — full docs + `docs/PLAYBOOK.md`.
- **I.7** — vectorize the indicator/confirm-mask path into `fast_engine` + parity test (the live-B1
  carry semantics here inform that port).
- **I.8** — NSGA-II → NSGA-III + **win-rate as a 3rd objective** + extended search space.
- **I.9** — optimizer smoke-run on 4h.
- **I.10** — full all-TF sweep + best-combo extraction per timeframe.

## 12. Status
**I.4 complete. WS-I is paused at the I.5 hard pause for team-leader sign-off** before any I.6+ work
begins.
