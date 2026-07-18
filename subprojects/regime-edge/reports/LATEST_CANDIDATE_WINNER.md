# Latest research candidate — 2026-07-18 (Agent B)

**Regime volatility size-ramp overlay** — the current best result of the volatility/regime research arc,
merged to dev as an **EXPERIMENTAL CANDIDATE** (off by default; NOT a confirmed edge).

- **Result:** +$10,356 (+6.8%) profit at **equal risk** on the NQ combined book (Ret/DD 5.52→5.90).
- **Status:** signal real (beats 96% of random, helps 4/5 purged folds) but **dollar magnitude unconfirmed at
  n=1** (bootstrap 90% CI [−$21k,+$61k]). Do **not** change defaults on it.
- **Insight:** for a **vol-seeking** strategy, size **WITH** volatility (textbook inverse-vol sizing HURTS).
- **Deployed:** `subprojects/regime-edge/apply_regime_sizing.py` (`--enable`, golden-safe off).
  Screenshot: `reports/figures/deploy_candidate_card.png`. Full report: `reports/MEGA_REPORT.md`.
- **Everything else NO-GO:** TimesFM, Chronos-2 (3 methods agree vol-gating is dead), regime veto, concentration.
- **Upgrade path:** a longer / bear-inclusive book (2010–23 box levels) to confirm or kill the magnitude.
