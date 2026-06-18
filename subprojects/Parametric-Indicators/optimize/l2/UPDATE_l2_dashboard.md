---
name: update_l2_dashboard
description: "L2 dashboard-inside-dashboard (#236) — BUILT. frontend/l2.html + 3 server.py routes + optimize/l2/payload.py (cached L1 + build_l2_payload). Runs the frozen lean L1, applies a manual L2 profile over its dropped signals, visualizes full context + combined guardrail, saves L2 profiles. 8 L2-dashboard tests green; golden 6/6; end-to-end smoke verified."
metadata:
  type: project
  workstream: second-layer-nonentry
  status: BUILT (2026-06-18) — next = optimizer (#237)
  date: 2026-06-18
---

# L2 dashboard-inside-dashboard — build report

> Spec: `docs/superpowers/specs/2026-06-18-l2-dashboard-design.md` ·
> Plan: `docs/superpowers/plans/2026-06-18-l2-dashboard.md`.

```mermaid
flowchart TB
    subgraph CLIENT["frontend/l2.html (vanilla JS + lightweight-charts)"]
        FORM["focused L2-levers form + indicator panel"] --> RUN["Run L2"]
        RUN -->|"POST /api/l2_backtest"| EP
        SAVE["Save L2 profile"] -->|"POST /api/l2_profiles"| EP2
        CFG["GET /api/l2_config"] --> FORM
        RENDER["render()"] --> VIS["price (L1-shading + dropped + agree/oppose + force-close) · equity (L1+L2 vs L1) · cards · ledger · dropped table"]
    end
    subgraph SRV["server.py (stdlib http.server — thin additive routes)"]
        EP["/api/l2_backtest"] --> BP["payload.build_l2_payload"]
        EP2["/api/l2_profiles"] --> SP["payload.save_l2_profile"]
        EP3["/api/l2_config"] --> CFGB["payload.l2_config"]
    end
    subgraph CORE["optimize/l2 (backtester, frozen)"]
        BP --> L1C["get_l1('4h') — run_l1 once/process (~38s, then cached)"]
        BP --> RL2["run_l2(l1, l2_params)"]
        BP --> MET["metrics.score + metrics.combined"]
    end
    BP -->|"JSON payload"| RENDER
    style CLIENT fill:#1a3a5a,stroke:#2962ff,color:#fff
    style CORE fill:#13241a,stroke:#00c853,color:#fff
```

## Modules / routes
| File | Purpose | Tests |
|---|---|---|
| `optimize/l2/payload.py` | `get_l1` cache + `build_l2_payload` (chart serialization) + `load/save_l2_profile` + `l2_config` | `test_payload.py` (3) + `test_payload_profiles.py` (3) |
| `server.py` (+routes) | `GET /api/l2_config`, `POST /api/l2_backtest`, `POST /api/l2_profiles` (thin; call payload) | `test_server_routes.py` (2) |
| `frontend/l2.html` | the page: focused L2 form, full-context charts, cards, L2 ledger, dropped table, save | manual smoke |

**8 L2-dashboard tests green; golden 6/6 unchanged** (all-new modules; `/api/backtest` + `index.html`
untouched). Note: `l2.html` is force-added — the repo-root `.gitignore` has a broad `*.html` rule with
per-file `index.html` exceptions; tracking `l2.html` directly avoids touching the already-modified `.gitignore`.

## End-to-end smoke (server on :8211, permissive stand-in L2 profile)
- `GET /l2.html` → HTTP 200 (14.7 KB).
- `GET /api/l2_config` → L1 = lean 4h champion: **255 trades, 492 dropped (286 veto + 206 vol-gate), 410 flat
  candidates**; 18 indicators in the schema.
- `POST /api/l2_backtest` (empty indicators, no gate) → all 8 payload keys present;
  **L2 n=349, P/L −$64,299, maxDD $108,453, win 54.4%, pf 0.87, L1-entry force-closes = 52**;
  **combined P/L $85,690, maxDD $50,574 (L1-only $15,491) → dd_not_worse = False**;
  2119 candles, 199 L1 in-position spans, 349 L2 trades. The L1 cache was warm from the config call ⇒ the
  backtest returned in **979 ms** (proving the run-once cache).

These match the backtester smoke exactly (n=349, −$64,299, 52 force-closes, combined maxDD $50,574).

## Reading
The permissive profile (take every flat dropped signal) loses money and worsens combined drawdown — the
expected counterfactual. The page makes the concurrency model visible (L1-flat shading, agree/oppose L2
arrows, purple `L1-entry` force-close marks) and the guardrail explicit (combined-vs-L1 equity + the
green/red `dd_not_worse` card). The *selective, profitable* L2 profile is the optimizer's job (#237).

## How to launch
```bash
python3 server.py --port 8200      # then open http://localhost:8200/l2.html
```

## Next (out of this plan)
Optimizer (#237): NSGA-III over the L2 levers, new prefix `l2v1`, min_trades=5, 4h; warm-start from
hand-found saved L2 profiles. Then speed (#210).
