---
name: Champion proposal
about: Propose a new champion set for a market/timeframe (merges only once VERIFIED)
labels: ["type:champion", "status:needs-verification"]
---

## Proposed champion
- Market / timeframe:
- Source study / optimizer run (prefix):
- Params (sl_soft / sl_hard / tp / gate_pct / cap):

## Numbers (full + OOS window)
| window | P&L | max DD | trades | win% |
|---|---|---|---|---|

## Verification (ALL required before merge)
- [ ] Reproduces on the dashboard UI to the dollar (not just the API)
- [ ] Gap-aware fills (`gap_fills=True`)
- [ ] Golden gate green
- [ ] Params PRINTED and confirmed (no silent defaults)
- [ ] Beats the incumbent OOS, or explicit rationale
