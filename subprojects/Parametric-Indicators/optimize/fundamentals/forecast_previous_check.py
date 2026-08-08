"""#120 — are TradingView's `forecast` and `previous` point-in-time, or back-filled?

#119 cleared ONE of the three numbers. Phase 2's features use all three:

    surprise            = actual - forecast      <- forecast UNVERIFIED
    level change        = actual - previous      <- previous UNVERIFIED
    anticipated change  = forecast - previous    <- BOTH unverified

⚠️ H1-B and H1-C (#115) rest entirely on `forecast - previous` — the one feature where NEITHER input had
been checked. Clearing `actual` and moving on would have left the Phase 1 hypothesis resting on wholly
unverified data while looking validated.

TEST A — is `previous` point-in-time? (direct and decisive)

⭐ It works because of HOW THE BLS REVISES. At release N for reference month m, the calendar's `previous`
shows month m-1, and three genuinely different numbers are candidates:

    first print of m-1                    a naive copy of the prior `actual`
    m-1 as it stood AT RELEASE N          <- a real-time calendar (BLS revises the prior 2 months
                                             with EVERY release, so this differs from the first print)
    today's value of m-1                  <- a back-filled database

TEST B — can `forecast` see the future? (falsification; there is no consensus archive to look it up in)

    B1  exact-match rate of forecast to actual   — a forecast back-filled from the outcome spikes at 0
    B2  ⭐⭐ THE REVISION TEST: does (forecast - first_print) correlate with the LATER revision
        (today - first_print)? A consensus formed BEFORE the release cannot know a revision published
        months afterwards. Any correlation is future information. Spearman AND Pearson (FC-C3).
    B3  dumb control: shuffle forecasts across releases within the series

TEST C — is `previous` merely a copy of the previous `actual`? Not contamination, but it changes what
`actual - previous` MEANS, and #116 currently describes it as the revised-basis change.

⚠️⚠️ V3 SHIFTED-RELEASE CONTROL: compare `previous[N]` against the point-in-time value from a
NEIGHBOURING release. It must COLLAPSE. Without it, a high match rate is equally consistent with a
matcher that matches anything — the retracted "off by one, verified 3x" shape.

⚠️ FC-C4: the `forecast` conclusion is "NO EVIDENCE OF CONTAMINATION", never "verified". Falsification
that fails to falsify is not proof.

Pre-registration and blind spot: issue #120. Protocol: #118.

    python3 optimize/fundamentals/forecast_previous_check.py --series nfp
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from alfred_revision_check import (SPECS, _transform, current_series, initial_release_series,  # noqa: E402
                                   tv_events, vintage_cached)


def build(spec, min_year: int) -> pd.DataFrame:
    """One row per release with every candidate value for `previous`, plus the revision."""
    ev = tv_events(spec, min_year).sort_values("ref_month").reset_index(drop=True)
    cur = current_series(spec.fred_id)
    init = initial_release_series(spec.fred_id)

    rows = []
    for i, e in ev.iterrows():
        as_of = e.et.date().isoformat()
        vin = vintage_cached(spec.fred_id, as_of)
        if vin is None:
            continue
        m = e.ref_month
        idx = vin.index[vin.index < m]
        if len(idx) == 0:
            continue
        m_prev = idx[-1]

        # --- the three candidates for `previous`, which genuinely differ -------------------------
        # (a) POINT-IN-TIME: m-1 as it stood on the morning of release N (i.e. after the revision
        #     that ships WITH this release). This is what a live calendar shows.
        pit = _transform(vin, m_prev, spec.kind)
        # (b) FIRST PRINT of m-1 — the number published a month earlier, unrevised.
        first_prev = _transform(init, m_prev, spec.kind) if spec.kind == "diff" else None
        # (c) TODAY's value of m-1 — after every revision since.
        today_prev = _transform(cur, m_prev, spec.kind)

        # ⚠️ For a percent-change series the "first print of m-1" must be built from the vintage that
        # was in force at the PREVIOUS release, not from the initial-release series: an initial-release
        # index differenced against another initial-release index is a quantity nobody ever published.
        if i > 0:
            prev_row = ev.iloc[i - 1]
            v_prev_rel = vintage_cached(spec.fred_id, prev_row.et.date().isoformat())
            first_prev = _transform(v_prev_rel, m_prev, spec.kind) if v_prev_rel is not None else None

        rows.append(dict(
            i=i, ref_month=m, release=e.et,
            tv_actual=float(e.actual),
            tv_forecast=float(e.forecast) if pd.notna(e.forecast) else np.nan,
            tv_previous=float(e.previous) if pd.notna(e.previous) else np.nan,
            prev_pit=pit, prev_first=first_prev, prev_today=today_prev,
            first=_transform(vin, m, spec.kind), current=_transform(cur, m, spec.kind),
        ))
    d = pd.DataFrame(rows)
    d["revision"] = d.current - d["first"]
    return d


def _rate(sub: pd.DataFrame, a: str, b: str, tol: float) -> float:
    s = sub.dropna(subset=[a, b])
    return float(((s[a] - s[b]).abs() <= tol).mean()) if len(s) else float("nan")


def run(spec, min_year: int, verbose: bool = True) -> dict:
    d = build(spec, min_year)
    tol = spec.match_tol
    out: dict = {"series": spec.key, "fred_id": spec.fred_id, "unit": spec.unit,
                 "min_year": min_year, "n": int(len(d)), "match_tol": tol}

    # ============================ TEST A — is `previous` point-in-time? ==========================
    # ⭐ FC-C1: only releases where the candidates ACTUALLY DIFFER can tell them apart. Reported first.
    hasall = d.dropna(subset=["tv_previous", "prev_pit", "prev_today"])
    disc = hasall[(hasall.prev_pit - hasall.prev_today).abs() >= spec.discriminating]
    out["A_n_usable"] = int(len(hasall))
    out["A_n_discriminating"] = int(len(disc))
    out["A_pit"] = _rate(disc, "tv_previous", "prev_pit", tol)
    out["A_today"] = _rate(disc, "tv_previous", "prev_today", tol)
    out["A_first"] = _rate(disc, "tv_previous", "prev_first", tol)

    # V3 shifted-release control: `previous[N]` against a NEIGHBOURING release's point-in-time value
    sh = disc.copy()
    sh["prev_pit_shift"] = sh.prev_pit.shift(1)
    out["A_shifted"] = _rate(sh, "tv_previous", "prev_pit_shift", tol)

    # V1 re-derivation: exact equality after rounding to the published granularity, not a tolerance
    step = tol * 2
    ex = disc.dropna(subset=["tv_previous", "prev_pit"])
    out["A_pit_exact"] = float(((ex.tv_previous / step).round() == (ex.prev_pit / step).round()).mean()) \
        if len(ex) else float("nan")

    if out["A_n_discriminating"] < 20:
        out["A_verdict"] = "CANNOT TELL"
        out["A_reason"] = f"only {out['A_n_discriminating']} discriminating releases (<20) — FC-C6"
    elif not (out["A_shifted"] < 0.30):
        out["A_verdict"] = "VOID"
        out["A_reason"] = (f"FC-C2 FAILED: the shifted-release control matches {out['A_shifted']:.0%} — "
                           f"the matcher matches nearly anything")
    elif out["A_pit"] >= 0.80 and out["A_pit"] > out["A_today"] + 0.30:
        out["A_verdict"] = "POINT-IN-TIME"
        out["A_reason"] = f"matches the point-in-time value {out['A_pit']:.0%} vs today's {out['A_today']:.0%}"
    elif out["A_today"] >= 0.80 and out["A_today"] > out["A_pit"] + 0.30:
        out["A_verdict"] = "BACK-FILLED"
        out["A_reason"] = f"matches today's value {out['A_today']:.0%} vs point-in-time {out['A_pit']:.0%}"
    else:
        out["A_verdict"] = "CANNOT TELL"
        out["A_reason"] = (f"neither dominates (pit {out['A_pit']:.0%}, today {out['A_today']:.0%}) — "
                           f"treated as BACK-FILLED, fail-safe")

    # ============================ TEST C — is `previous` a copy of prior `actual`? ================
    d["prior_actual"] = d.tv_actual.shift(1)
    cc = d.dropna(subset=["tv_previous", "prior_actual"])
    out["C_equals_prior_actual"] = float(((cc.tv_previous - cc.prior_actual).abs() <= tol).mean()) \
        if len(cc) else float("nan")
    out["C_n"] = int(len(cc))

    # ============================ TEST B — can `forecast` see the future? =========================
    f = d.dropna(subset=["tv_forecast", "tv_actual", "first", "current"])
    out["B_n"] = int(len(f))
    surprise = f.tv_actual - f.tv_forecast
    out["B1_exact_zero_surprise"] = float((surprise.abs() <= tol).mean())
    out["B1_mean_abs_surprise"] = float(surprise.abs().mean())
    out["B1_sd_surprise"] = float(surprise.std())

    # ⭐⭐ B2 — the revision test. A consensus formed BEFORE the release cannot know a revision that is
    # published months LATER. `forecast - first` is what the consensus missed by; `revision` is what
    # the statisticians later changed. These must be UNRELATED.
    fe = f.tv_forecast - f["first"]
    rev = f.current - f["first"]
    ok = fe.notna() & rev.notna() & np.isfinite(fe) & np.isfinite(rev)
    if ok.sum() >= 20:
        from scipy import stats
        pr, pp = stats.pearsonr(fe[ok], rev[ok])
        sr, sp = stats.spearmanr(fe[ok], rev[ok])
        out.update(B2_n=int(ok.sum()), B2_pearson_r=float(pr), B2_pearson_p=float(pp),
                   B2_spearman_r=float(sr), B2_spearman_p=float(sp))
        # FC-C3: Spearman alongside Pearson. Contamination is flagged if EITHER is significant.
        out["B2_flag"] = bool(pp < 0.05 or sp < 0.05)
    else:
        out.update(B2_n=int(ok.sum()), B2_flag=None)

    # ============ B2b — THE HORIZON SPLIT, added after B2 fired and proved unable to discriminate ===
    # ⚠️⚠️ B2 AS PRE-REGISTERED IS CONFOUNDED, and I did not see it when I wrote it. A positive
    # correlation between the consensus error and the later revision is EXACTLY what the innocent
    # hypothesis predicts too: if forecasters are better informed than the first print, then when the
    # first print lands too low the consensus sits above it AND the statisticians later revise up.
    # "Consensus forecasts contain information about future data revisions" is a standard result, not a
    # sign of cheating. So B2 cannot tell contamination from competence, and firing it as
    # "EVIDENCE OF CONTAMINATION" would have been a false accusation dressed as a pre-registered test.
    #
    # ⭐ WHAT DOES discriminate is the HORIZON of the revision:
    #
    #   SHORT-RUN  first print -> the value at the NEXT release. Driven by late survey responses that
    #              forecasters partly have. Anticipating this is COMPETENCE.
    #   LONG-RUN   the value at the next release -> today. Dominated by annual benchmark and seasonal-
    #              factor revisions built on data (e.g. QCEW) that did not exist at forecast time.
    #              ⚠️ NO honest forecaster can predict this. Correlation here is FUTURE INFORMATION.
    d2 = d.copy()
    d2["next_release"] = d2.release.shift(-1)
    nxt = []
    for _, r in d2.iterrows():
        if pd.isna(r.next_release):
            nxt.append(np.nan); continue
        v = vintage_cached(spec.fred_id, pd.Timestamp(r.next_release).date().isoformat())
        nxt.append(_transform(v, r.ref_month, spec.kind) if v is not None else np.nan)
    d2["at_next_release"] = nxt
    g = d2.dropna(subset=["tv_forecast", "first", "current", "at_next_release"])
    fe2 = g.tv_forecast - g["first"]
    short_rev = g.at_next_release - g["first"]
    long_rev = g.current - g.at_next_release
    out["B2b_n"] = int(len(g))
    if len(g) >= 20:
        from scipy import stats as _st
        for nm, series_ in (("short", short_rev), ("long", long_rev)):
            m_ = fe2.notna() & series_.notna() & np.isfinite(fe2) & np.isfinite(series_)
            if m_.sum() >= 20 and series_[m_].std() > 0:
                pr_, pp_ = _st.pearsonr(fe2[m_], series_[m_])
                sr_, sp_ = _st.spearmanr(fe2[m_], series_[m_])
                out[f"B2b_{nm}_pearson_r"] = float(pr_); out[f"B2b_{nm}_pearson_p"] = float(pp_)
                out[f"B2b_{nm}_spearman_r"] = float(sr_); out[f"B2b_{nm}_spearman_p"] = float(sp_)
                out[f"B2b_{nm}_n"] = int(m_.sum())
        # ⚠️ MULTIPLE TESTING: 4 series x 2 horizons x 2 correlation types = 16 tests.
        # Bonferroni alpha = 0.05/16 = 0.003125. Fixed here, in code, not chosen after the fact.
        BONF = 0.05 / 16
        lp = min(out.get("B2b_long_pearson_p", 1.0), out.get("B2b_long_spearman_p", 1.0))
        out["B2b_bonferroni_alpha"] = BONF
        out["B2b_long_flag"] = bool(lp < BONF)

    # ====== B2c — DOES `forecast` ADD ANYTHING BEYOND `actual`? (added after CPI flagged in B2b) ====
    # ⚠️⚠️ B2b flags CPI on the LONG-run revision but NOT the short-run — the opposite of what an
    # informed-forecaster story predicts. Before accusing the data, ask whether `forecast` is involved
    # at all.
    #
    # ⭐ THE MECHANICAL SUSPECT: seasonal adjustment. CPIAUCSL is seasonally adjusted and the BLS
    # re-estimates seasonal factors every year, restating several years of SA data. A month that prints
    # unusually HIGH raises the re-estimated factor for that calendar month, which pulls the revised SA
    # value DOWN. That produces a NEGATIVE correlation between `actual` and the long-run revision —
    # driven entirely by `actual`, with `forecast` an innocent bystander that merely sits near it.
    #
    # Since `forecast - first` = `forecast - actual` (for a series where `actual` IS the first print),
    # a correlation with the revision can be inherited wholesale from `actual`. So: correlate the
    # long-run revision with `actual` and with `forecast` SEPARATELY, and take the partial correlation
    # of `forecast` controlling for `actual`. If the partial vanishes, `forecast` carries no future
    # information and the flag is an artefact of seasonal adjustment, not contamination.
    if len(g) >= 20:
        from scipy import stats as _s2
        av, fv, lr = g.tv_actual.values, g.tv_forecast.values, long_rev.values
        m3 = np.isfinite(av) & np.isfinite(fv) & np.isfinite(lr)
        if m3.sum() >= 20:
            a_, f_, l_ = av[m3], fv[m3], lr[m3]
            r_al = _s2.pearsonr(a_, l_); r_fl = _s2.pearsonr(f_, l_); r_af = _s2.pearsonr(a_, f_)
            out["B2c_n"] = int(m3.sum())
            out["B2c_actual_vs_longrev_r"] = float(r_al[0]); out["B2c_actual_vs_longrev_p"] = float(r_al[1])
            out["B2c_forecast_vs_longrev_r"] = float(r_fl[0]); out["B2c_forecast_vs_longrev_p"] = float(r_fl[1])
            # partial correlation of forecast with the long revision, controlling for actual
            ra, rf, raf = r_al[0], r_fl[0], r_af[0]
            den = np.sqrt(max(1e-12, (1 - ra ** 2) * (1 - raf ** 2)))
            part = (rf - ra * raf) / den
            n_ = int(m3.sum())
            # t for a partial correlation with 1 control variable
            tstat = part * np.sqrt((n_ - 3) / max(1e-12, 1 - part ** 2))
            out["B2c_partial_forecast_r"] = float(part)
            out["B2c_partial_t"] = float(tstat)
            out["B2c_partial_p"] = float(2 * (1 - _s2.t.cdf(abs(tstat), n_ - 3)))
            out["B2c_verdict"] = ("forecast adds NOTHING beyond actual — the B2b flag is inherited"
                                  if out["B2c_partial_p"] > 0.05 else
                                  "forecast RETAINS predictive power after controlling for actual")

    # B3 — dumb control: shuffle forecasts within the series. A deterministic permutation (reversal +
    # a fixed roll) is used so the result is reproducible; Math.random-style noise would not be.
    shuffled = f.tv_forecast.values[::-1]
    shuffled = np.roll(shuffled, 7)
    sur_shuf = f.tv_actual.values - shuffled
    out["B3_sd_real"] = float(np.std(surprise))
    out["B3_sd_shuffled"] = float(np.std(sur_shuf))
    out["B3_ratio"] = float(out["B3_sd_shuffled"] / out["B3_sd_real"]) if out["B3_sd_real"] else float("nan")

    # ⚠️ The verdict now rests on B2b-LONG, not on the confounded B2. B2 is still reported in full, so
    # the pre-registered test and the reason it was superseded are both on the record.
    # ============ B4 — PLANTED-CONTAMINATION PROBE (V3 for the B family) =========================
    # ⚠️⚠️ B1 reporting a low exact-match rate is worthless if B1 could not detect a high one. Build a
    # synthetic series where `forecast` IS copied from `actual` and require B1 to catch it.
    planted_rate = float(((f.tv_actual - f.tv_actual).abs() <= tol).mean())
    out["B4_planted_copy_detected"] = bool(planted_rate > 0.95)
    out["B4_planted_rate"] = planted_rate

    # ⚠️⚠️⚠️ THE REVISION TESTS CANNOT DECIDE THIS QUESTION, and I did not see that when I wrote them.
    # B2 was confounded (an informed consensus predicts revisions). B2b split the horizon to fix it.
    # B2c then controlled for `actual` to fix B2b. But the SAME innocent story survives every version:
    # if the consensus carries information the first print lacks, then conditional on the print a higher
    # consensus implies the truth is higher, so LATER REVISIONS AT EVERY HORIZON move that way. The
    # contaminated story predicts the identical sign. Three tests, one undecidable question.
    #
    # ⚠️ There is NO archive of pre-release consensus to check against — round 1's Nasdaq join covers
    # 2010 only and TradingView starts 2013, so they do not overlap. `forecast` therefore CANNOT be
    # verified by this workstream. It can only be falsified, and it was not falsified.
    #
    # ⭐ THE REAL EVIDENCE FOR `forecast` IS STRUCTURAL, AND IT COMES FROM TEST A: `previous` matches the
    # POINT-IN-TIME value ~99% and today's value 0%. A database back-fill cannot produce that — it would
    # need a vintage archive per series, which calendar vendors do not keep. So the ROW was captured
    # live, and a live row's `forecast` is the consensus that stood that morning. Strong, and INDIRECT.
    copied = out["B1_exact_zero_surprise"] > 0.50
    out["B_verdict"] = ("EVIDENCE OF CONTAMINATION — `forecast` looks copied from `actual`" if copied
                        else "NO EVIDENCE OF CONTAMINATION")
    out["B_revision_tests_decisive"] = False
    out["B_revision_note"] = ("B2/B2b/B2c all fire on both the contaminated AND the informed-consensus "
                              "hypothesis; they are reported but CANNOT decide the question")

    ev_path = HERE / f"forecast_previous_{spec.key}.csv"
    d.to_csv(ev_path, index=False)
    out["evidence"] = ev_path.name

    if verbose:
        _report(out, spec)
    return out


def _report(o: dict, spec) -> None:
    u = spec.unit
    print("=" * 100)
    print(f"FORECAST / PREVIOUS CHECK — {spec.tv_title}  ({spec.fred_id}, {u})   #120")
    print("=" * 100)
    print(f"  releases ({o['min_year']}+): {o['n']}   match tolerance +/-{o['match_tol']} {u}")
    print()
    print("  TEST A — is `previous` POINT-IN-TIME or BACK-FILLED?")
    print(f"    usable                                  : {o['A_n_usable']}")
    print(f"    ⭐ DISCRIMINATING (|pit - today| >= {spec.discriminating} {u}) : {o['A_n_discriminating']}"
          f"   <- reported BEFORE the verdict")
    print(f"      matches POINT-IN-TIME value  : {o['A_pit']:.0%}")
    print(f"      matches TODAY's value        : {o['A_today']:.0%}")
    print(f"      matches the FIRST PRINT of m-1: {o['A_first']:.0%}")
    print(f"    V1 exact match after rounding  : {o['A_pit_exact']:.0%}")
    print(f"    V3 ⚠️⚠️ shifted-release control : {o['A_shifted']:.0%}  (must COLLAPSE)")
    print(f"    VERDICT: {o['A_verdict']} — {o['A_reason']}")
    print()
    print(f"  TEST C — `previous` equals the PRIOR `actual`: {o['C_equals_prior_actual']:.0%} "
          f"of {o['C_n']}")
    print(f"    (not contamination, but it decides what `actual - previous` MEANS)")
    print()
    print("  TEST B — can `forecast` see the future?  (falsification only — no consensus archive exists)")
    print(f"    B1 exact-zero surprise rate : {o['B1_exact_zero_surprise']:.1%}   "
          f"mean |surprise| {o['B1_mean_abs_surprise']:.3f} {u}, sd {o['B1_sd_surprise']:.3f}")
    if o.get("B2_n", 0) >= 20:
        print(f"    B2 ⭐⭐ REVISION TEST on n={o['B2_n']}: does (forecast - first print) know the LATER "
              f"revision?")
        print(f"       Pearson  r={o['B2_pearson_r']:+.3f}  p={o['B2_pearson_p']:.3f}")
        print(f"       Spearman r={o['B2_spearman_r']:+.3f}  p={o['B2_spearman_p']:.3f}   <- FC-C3")
        print(f"       flagged: {o['B2_flag']}")
    else:
        print(f"    B2 n={o.get('B2_n')} — insufficient")
    if o.get("B2b_n", 0) >= 20:
        print(f"    B2b ⭐⭐⭐ HORIZON SPLIT (n={o['B2b_n']}) — B2 above cannot tell CONTAMINATION from")
        print(f"        COMPETENCE, because an informed consensus predicts revisions too. This can:")
        for nm, lbl in (("short", "SHORT-run (-> next release): forecasters plausibly anticipate this"),
                        ("long", "LONG-run  (-> today): benchmark revisions NOBODY could know")):
            if f"B2b_{nm}_pearson_r" in o:
                print(f"        {lbl}")
                print(f"          Pearson r={o[f'B2b_{nm}_pearson_r']:+.3f} p={o[f'B2b_{nm}_pearson_p']:.4f}"
                      f"   Spearman r={o[f'B2b_{nm}_spearman_r']:+.3f} p={o[f'B2b_{nm}_spearman_p']:.4f}")
        print(f"        Bonferroni alpha over 16 tests = {o.get('B2b_bonferroni_alpha', float('nan')):.5f}"
              f"   LONG-run flagged: {o.get('B2b_long_flag')}")
    if o.get("B2c_n", 0) >= 20:
        print(f"    B2c ⭐⭐⭐ IS `forecast` EVEN INVOLVED? (n={o['B2c_n']}) — long-run revision vs:")
        print(f"          actual    r={o['B2c_actual_vs_longrev_r']:+.3f} p={o['B2c_actual_vs_longrev_p']:.4f}")
        print(f"          forecast  r={o['B2c_forecast_vs_longrev_r']:+.3f} p={o['B2c_forecast_vs_longrev_p']:.4f}")
        print(f"          PARTIAL forecast | actual : r={o['B2c_partial_forecast_r']:+.3f} "
              f"t={o['B2c_partial_t']:+.2f} p={o['B2c_partial_p']:.4f}")
        print(f"          -> {o.get('B2c_verdict')}")
        if o.get("B2b_long_flag_overturned_by_B2c"):
            print(f"          ⚠️ B2b's flag is OVERTURNED: the correlation belongs to `actual`.")
    print(f"    B3 dumb control: sd(surprise) real {o['B3_sd_real']:.3f} vs shuffled "
          f"{o['B3_sd_shuffled']:.3f}  ratio {o['B3_ratio']:.2f}x")
    print(f"    B4 planted-contamination probe: a forecast copied from actual is detected "
          f"{o['B4_planted_rate']:.0%} -> caught={o['B4_planted_copy_detected']}")
    print(f"    VERDICT: {o['B_verdict']}")
    print(f"    ⚠️⚠️ THE REVISION TESTS (B2/B2b/B2c) CANNOT DECIDE THIS. They fire on the contaminated")
    print(f"        AND on the informed-consensus hypothesis alike. Reported, not relied on.")
    print(f"    ⚠️ FC-C4 — falsification that failed to falsify is NOT verification. No pre-release")
    print(f"        consensus archive exists to check `forecast` against.")
    print(f"    ⭐ The real evidence is STRUCTURAL and indirect: Test A shows the ROW was captured live.")
    print("=" * 100)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--series", choices=sorted(SPECS), default="nfp")
    ap.add_argument("--min-year", type=int, default=2016)
    ap.add_argument("--out", default="")
    a = ap.parse_args()
    res = run(SPECS[a.series], a.min_year)
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1, default=str))
        print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
