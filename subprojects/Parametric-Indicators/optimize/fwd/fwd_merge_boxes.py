"""WS-FWD box refresh (#179) — merge the owner's box export into the server data.

Drop layout: <zip>/last levels/FUTURES/<EXCH>/<TOK>/<TOK>_{full,day,week,month}_data.csv
(raw, UNshifted, scraped 2026-08-22; rows 2026-05-18 .. 2026-08-07).

Gate E (per file): on every date both the existing file and the drop carry, ALL shared
columns except Scraped_At must be exactly equal (string compare after float normalisation).
A mismatch is reported and blocks that file — nothing is patched silently.

--probe  : only print, for each target file, the overlap agreement for shift 0 and -1 BDay
           (tells us which convention each existing file is in). No writes.
--apply  : append the new rows (convention chosen per target) and write the merged files.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

PROD = Path("/home/dev/Mulham/wsg-i")
FWD = PROD / "FWD_EXTENDED"
DROP = PROD / "vendor_drops_local" / "last levels" / "FUTURES"
EXCH = {"NQ": "CME", "ES": "CME", "RTY": "CME", "YM": "CBOT", "GC": "COMEX", "SI": "COMEX",
        "HG": "COMEX", "CL": "NYMEX", "NG": "NYMEX"}
SERVER_EXCH = dict(EXCH, YM="CME")        # server keeps YM under CME
KINDS = ("full", "day", "week", "month")


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["_d"] = pd.to_datetime(df["Date"]).dt.normalize()
    return df


def _shift(df: pd.DataFrame, bdays: int) -> pd.DataFrame:
    df = _norm(df)
    if bdays:
        new = df["_d"] - pd.offsets.BDay(bdays)   # negative = forward
        assert new.dt.dayofweek.max() <= 4 and not new.duplicated().any()
        df["_d"] = new
        df["Date"] = new.dt.strftime("%Y-%m-%d")
    return df


ENGINE_COLS = {"dOpen", "wOpen", "mOpen"} | {f"{p}{k}" for p in "WM" for k in
               ("IHD", "IHU", "ILD", "ILU", "RHD", "RHU", "RLD", "RLU", "TH1", "TH2", "THD", "THU",
                "TL1", "TL2", "TLD", "TLU")}   # the 3 opens + 16 W + 16 M levels box_lookup reads


def compare(base: pd.DataFrame, add: pd.DataFrame) -> dict:
    """mismatch_cols: value != value (FAIL on engine cols). nan_vs_value: one side NaN (WARN:
    scrape repaint observation). Daily D* columns are not read by the engine -> info only."""
    cols = [c for c in base.columns if c in add.columns and c not in ("Date", "Scraped_At", "_d")]
    b = base.set_index("_d"); a = add.set_index("_d")
    common = b.index.intersection(a.index)
    bad_cols: dict[str, int] = {}; nanv: dict[str, int] = {}
    bad_dates: set = set(); nan_dates: set = set()
    for c in cols:
        bv = pd.to_numeric(b.loc[common, c], errors="coerce").round(8)
        av = pd.to_numeric(a.loc[common, c], errors="coerce").round(8)
        both = bv.notna() & av.notna()
        ne = both & (bv != av)
        one = bv.isna() ^ av.isna()
        if ne.any():
            bad_cols[c] = int(ne.sum()); bad_dates |= set(common[ne.to_numpy()])
        if one.any():
            nanv[c] = int(one.sum()); nan_dates |= set(common[one.to_numpy()])
    eng_fail = {c: n for c, n in bad_cols.items() if c in ENGINE_COLS}
    eng_warn = {c: n for c, n in nanv.items() if c in ENGINE_COLS}
    return {"overlap": len(common), "cols": len(cols), "mismatch_cols": bad_cols,
            "mismatch_dates": sorted(str(d.date()) for d in bad_dates),
            "nan_vs_value_cols": nanv, "nan_vs_value_dates": sorted(str(d.date()) for d in nan_dates),
            "engine_fail": eng_fail, "engine_warn": eng_warn,
            "base_only_cols": sorted(set(base.columns) - set(add.columns) - {"_d"}),
            "add_only_cols": sorted(set(add.columns) - set(base.columns) - {"_d"})}


def merge(base: pd.DataFrame, add: pd.DataFrame) -> pd.DataFrame:
    add = add.reindex(columns=base.columns)                 # drop lacks e.g. MTL* -> NaN
    m = (pd.concat([base, add], ignore_index=True)
         .drop_duplicates(subset="_d", keep="first")
         .sort_values("_d", kind="mergesort").reset_index(drop=True))
    return m.drop(columns="_d")


def targets() -> list[tuple[str, str, Path, Path, int, int]]:
    """(tok, kind, existing_file, drop_file, drop_shift_bdays, base_unshift_bdays)

    Probe (2026-08-23, on #179): the 7 non-NQ/ES raw files match the drop at shift 0 on all
    53 columns (31 dates). NQ's raw file and the engine box match the drop at shift -1 BDay
    (they are stored in the engine's shifted convention). ES's "raw" file ALSO matches at -1
    BDay, i.e. it was delivered already shifted, and onboard_stock.shift_box shifted it AGAIN:
    the engine ES box is one business day AHEAD (Friday rows carry next week's levels). Fix:
    un-shift the ES raw file (+1 BDay) back to raw convention before appending, so the single
    shift downstream is correct. NQ/ES day/week/month files are engine-irrelevant and in the
    wrong convention; the drop's versions are stored alongside as *_aug2026.csv, untouched.
    """
    out = []
    for tok, ex in EXCH.items():
        for k in KINDS:
            drop = DROP / ex / tok / f"{tok}_{k}_data.csv"
            cur = PROD / "ALL_STOCKS" / "BOXS" / SERVER_EXCH[tok] / tok / f"{tok}_{k}_data.csv"
            if not (drop.exists() and cur.exists()):
                continue
            if tok in ("NQ", "ES") and k != "full":
                out.append((tok, k, cur, drop, -1, 0))          # -1 = store-alongside only
            elif tok == "NQ":
                out.append((tok, k, cur, drop, 1, 0))           # raw file is in shifted convention
            elif tok == "ES":
                out.append((tok, k, cur, drop, 0, 1))           # un-shift base, then raw merge
            else:
                out.append((tok, k, cur, drop, 0, 0))
    # NQ engine box (shifted convention) — merged onto the with20d file, written to the FWD root
    out.append(("NQ", "engine", PROD / "data" / "full_data" / "NQ_full_data_with20d.csv",
                DROP / "CME" / "NQ" / "NQ_full_data.csv", 1, 0))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--out", default=str(FWD / "fwd_books" / "fwd_box_merge_report.json"))
    a = ap.parse_args()
    report = {}
    for tok, kind, cur, drop, sh, unsh in targets():
        base = _norm(pd.read_csv(cur)); add_raw = pd.read_csv(drop)
        key = f"{tok}:{kind}"
        if sh == -1:
            dst = cur.with_name(cur.stem + "_aug2026.csv")
            if a.apply:
                shutil.copy2(drop, dst)
            report[key] = {"action": "stored alongside (convention differs, engine-irrelevant)", "written": str(dst)}
            print(f"{key:12s} stored alongside -> {dst.name}")
            continue
        if unsh:
            base = _shift(base.drop(columns="_d"), -unsh)       # +1 BDay: back to raw convention
        if a.probe:
            r = {f"shift{s}": compare(base, _shift(add_raw, s)) for s in (0, 1)}
            r["base_last"] = str(base["_d"].max().date()); r["base_rows"] = len(base)
            report[key] = r
            s0, s1 = r["shift0"], r["shift1"]
            print(f"{key:12s} base→{r['base_last']} | shift0 overlap={s0['overlap']} badcols={len(s0['mismatch_cols'])}"
                  f" | shift1 overlap={s1['overlap']} badcols={len(s1['mismatch_cols'])}"
                  f" | colsdiff base_only={s0['base_only_cols']} add_only={s0['add_only_cols']}")
            continue
        add = _shift(add_raw, sh)
        r = compare(base, add)
        ok = not r["engine_fail"] and not r["add_only_cols"]
        r.update(base_rows=len(base), base_last=str(base["_d"].max().date()), shift_bdays=sh,
                 base_unshift_bdays=unsh, gate_e=ok)
        if ok and a.apply:
            m = merge(base, add)
            if kind == "engine":
                dst = FWD / "data" / "full_data" / "NQ_full_data.csv"
                m.to_csv(dst, index=False)
                y = m[pd.to_datetime(m["Date"]).dt.year == 2026]
                y.to_csv(FWD / "data" / "2026_data" / "NQ_full_data_2026.csv", index=False)
                # also keep a prod-side copy under a NEW name (prod engine file untouched)
                m.to_csv(PROD / "data" / "full_data" / "NQ_full_data_aug2026.csv", index=False)
            else:
                shutil.copy2(cur, cur.with_suffix(".csv.pre179"))
                m.to_csv(cur, index=False)
                dst = cur
            r.update(merged_rows=len(m), merged_last=str(pd.to_datetime(m["Date"]).max().date()), written=str(dst))
        print(f"{key:12s} gate_e={ok} overlap={r['overlap']} engine_fail={r['engine_fail']} "
              f"engine_warn(nan-vs-value)={r['engine_warn']} other_mism={ {c:n for c,n in r['mismatch_cols'].items() if c not in ENGINE_COLS} } "
              f"{'→ ' + r['merged_last'] + ' (' + str(r['merged_rows']) + ' rows)' if 'merged_rows' in r else ''}")
        report[key] = r
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(report, indent=1, default=str))
    print("report →", a.out)


if __name__ == "__main__":
    main()
