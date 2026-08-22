"""WS-FWD Phase 0.5 (#176) — gated candle extension into a PARALLEL data root.

Splices the fresh tape (the 16-year dataset's 1m, through 2026-08-07) onto each instrument's
engine candle files, under the gates frozen in docs/WS-FWD-PREREGISTRATION.md:

  Gate A — 1m splice parity: last 21 days of engine coverage; timestamp-intersection coverage
           >= 99% and EXACT o/h/l/c AND volume equality (volume is load-bearing: vwap/obv/mfi).
           Fail => the instrument is NOT appended.
  Gate B — TF resample proof: vendor TF bars must be exactly reproducible from vendor 1m
           (bars labeled by start; 4h grid offset 2h for the 18:00 session anchor) over the
           vendor's own coverage, excluding the final (possibly partial) bar. Fail => that TF
           is not extended.
  Gate C — (separate) re-audit of the extended root + original-root checksum stability.

The production root is NEVER written. Extended files land in a mirror tree (WSH_FWD_ROOT),
same relative paths, so runs opt in via WSH_DATA_BASE/WSG_DATA_ROOT. Box CSVs are NOT touched
(owner-scraped externals — fabricating levels is forbidden); the NQ box dir is symlinked so the
loader finds the same box file.

Usage (server):
  env WSH_DATA_BASE=~/Mulham/wsg-i WSG_DATA_ROOT=~/Mulham/wsg-i/data \
      WSH_16Y_ROOT=~/Mulham/data_2010_1s WSH_FWD_ROOT=~/Mulham/wsg-i/FWD_EXTENDED \
      python3 optimize/fwd/fwd_extend_candles.py [--tokens NQ,ES,...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve()
PI = HERE.parents[2]
sys.path.insert(0, str(PI))

from optimize import instruments as INST          # noqa: E402

TFS = ("2m", "5m", "15m", "1h", "2h", "4h")
RULE = {"2m": "2min", "5m": "5min", "15m": "15min", "1h": "1h", "2h": "2h", "4h": "4h"}
OFFSET = {"4h": "2h"}                              # 18:00-anchored session grid: 2,6,10,14,18,22
OVERLAP_DAYS = 21
COVERAGE_MIN = 0.99

BASE = Path(os.environ["WSH_DATA_BASE"]).expanduser()
Y16 = Path(os.environ.get("WSH_16Y_ROOT", "~/Mulham/data_2010_1s")).expanduser()
FWD = Path(os.environ["WSH_FWD_ROOT"]).expanduser()


def _read(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df.sort_values("datetime").reset_index(drop=True)


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def gate_a(eng: pd.DataFrame, big: pd.DataFrame) -> dict:
    end = eng["datetime"].iloc[-1]
    lo = end - pd.Timedelta(days=OVERLAP_DAYS)
    e = eng[(eng["datetime"] > lo)].set_index("datetime")
    b = big[(big["datetime"] > lo) & (big["datetime"] <= end)].set_index("datetime")
    common = e.index.intersection(b.index)
    cov = len(common) / max(len(e), 1)
    res = {"engine_rows": len(e), "big_rows": len(b), "common": len(common),
           "coverage": round(cov, 6), "engine_only": len(e.index.difference(b.index)),
           "big_only": len(b.index.difference(e.index))}
    mism = {}
    for col in ("open", "high", "low", "close", "volume"):
        neq = (e.loc[common, col].to_numpy() != b.loc[common, col].to_numpy())
        mism[col] = int(neq.sum())
    res["mismatches"] = mism
    res["pass"] = cov >= COVERAGE_MIN and all(v == 0 for v in mism.values())
    return res


def _resample(m1: pd.DataFrame, tf: str) -> pd.DataFrame:
    g = m1.set_index("datetime").resample(RULE[tf], offset=OFFSET.get(tf, "0min"), label="left",
                                          closed="left")
    out = g.agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    out = out.dropna(subset=["open"]).reset_index()
    out["volume"] = out["volume"].astype("int64")
    return out


def gate_b(eng1m: pd.DataFrame, vendor_tf: pd.DataFrame, tf: str) -> dict:
    """Vendor TF bars reproducible from vendor 1m? Compares over vendor coverage minus the
    final (possibly partial) bar; bars before the 1m start are excluded."""
    rebuilt = _resample(eng1m, tf)
    v = vendor_tf.iloc[:-1]                                   # drop the final partial bar
    v = v[v["datetime"] >= eng1m["datetime"].iloc[0]]
    r = rebuilt.set_index("datetime")
    vv = v.set_index("datetime")
    missing = vv.index.difference(r.index)
    extra = r.index.intersection(  # bars we build inside vendor coverage that vendor lacks
        pd.Index([])) if len(vv) == 0 else r.loc[(r.index >= vv.index[0]) & (r.index <= vv.index[-1])].index.difference(vv.index)
    common = vv.index.intersection(r.index)
    mism = {}
    for col in ("open", "high", "low", "close", "volume"):
        neq = (vv.loc[common, col].to_numpy() != r.loc[common, col].to_numpy())
        mism[col] = int(neq.sum())
    res = {"vendor_bars": len(vv), "rebuilt_common": len(common), "vendor_only": len(missing),
           "rebuilt_only_inside": len(extra), "mismatches": mism}
    res["pass"] = len(missing) == 0 and len(extra) == 0 and all(v2 == 0 for v2 in mism.values())
    return res


def extend_token(tok: str, report: dict) -> None:
    dec4, minute_path, box_path = INST.resolve_paths(tok, "4h")
    big_path = Y16 / f"{tok}_Continuous_Data" / f"{tok}_1m.csv"
    eng1m = _read(minute_path)
    big1m = _read(big_path)
    rep = report[tok] = {"minute_path": str(minute_path), "big_path": str(big_path),
                         "engine_end": str(eng1m["datetime"].iloc[-1]),
                         "big_end": str(big1m["datetime"].iloc[-1])}

    rep["gate_a"] = ga = gate_a(eng1m, big1m)
    print(f"[{tok}] gate A: pass={ga['pass']} coverage={ga['coverage']} mism={ga['mismatches']} "
          f"(engine_only={ga['engine_only']} big_only={ga['big_only']})", flush=True)
    if not ga["pass"]:
        rep["appended"] = False
        return

    end = eng1m["datetime"].iloc[-1]
    fresh = big1m[big1m["datetime"] > end]
    ext1m = pd.concat([eng1m, fresh], ignore_index=True)
    rep["fresh_1m_rows"] = len(fresh)

    # Gate B per TF on VENDOR data only, then write extended frames for the passers.
    rep["gate_b"] = {}
    ok_tfs = []
    for tf in TFS:
        vend = _read(INST.resolve_paths(tok, tf)[0])
        gb = gate_b(eng1m, vend, tf)
        rep["gate_b"][tf] = gb
        print(f"[{tok}] gate B {tf}: pass={gb['pass']} common={gb['rebuilt_common']} "
              f"vendor_only={gb['vendor_only']} extra={gb['rebuilt_only_inside']} mism={gb['mismatches']}",
              flush=True)
        if gb["pass"]:
            ok_tfs.append(tf)

    def _dst(src: str | Path) -> Path:
        rel = Path(src).resolve().relative_to(BASE.resolve())
        d = FWD / rel
        d.parent.mkdir(parents=True, exist_ok=True)
        return d

    # 1m always written once gate A passed (needed by every TF's exit resolution)
    out1m = _dst(minute_path)
    ext1m.to_csv(out1m, index=False)
    rep["ext_1m"] = {"path": str(out1m), "rows": len(ext1m), "end": str(ext1m["datetime"].iloc[-1])}

    for tf in ok_tfs:
        # full-history rebuild — proven identical to vendor over vendor coverage by gate B
        ext_tf = _resample(ext1m, tf)
        p = _dst(INST.resolve_paths(tok, tf)[0])
        ext_tf.to_csv(p, index=False)
    rep["extended_tfs"] = ok_tfs
    rep["appended"] = True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tokens", default=",".join(INST.TOKENS))
    args = ap.parse_args()
    toks = [t.strip() for t in args.tokens.split(",") if t.strip()]

    FWD.mkdir(parents=True, exist_ok=True)
    # the loader finds the NQ box under WSG_DATA_ROOT=<FWD>/data — symlink the prod box dir (read-only)
    (FWD / "data").mkdir(exist_ok=True)
    link = FWD / "data" / "full_data"
    if not link.exists():
        link.symlink_to(BASE / "data" / "full_data")

    report: dict = {"pre_checksums": {}}
    for tok in toks:
        _, minute_path, _ = INST.resolve_paths(tok, "4h")
        report["pre_checksums"][tok] = _sha(Path(minute_path))
        extend_token(tok, report)
        # prove the production file was not touched
        report[tok]["prod_sha_stable"] = (_sha(Path(minute_path)) == report["pre_checksums"][tok])

    out = FWD / "fwd_extension_report.json"
    out.write_text(json.dumps(report, indent=1))
    print(f"\nreport -> {out}")
    bad = [t for t in toks if not report[t].get("appended")]
    print(f"appended: {[t for t in toks if report[t].get('appended')]}  blocked: {bad}")


if __name__ == "__main__":
    main()
