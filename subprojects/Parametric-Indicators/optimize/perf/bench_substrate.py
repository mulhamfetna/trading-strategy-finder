"""Issue #58 Question A — is the cache SUBSTRATE a bottleneck? (measure, don't reason)

Reads REAL cached vote arrays from the live cache and times retrieval through every substrate we could
plausibly switch to, at 1 and N concurrent readers:

  dict        in-process dict            — the theoretical floor (pure RAM, no I/O, no parse)
  npy_tmp     np.load from /tmp          — CURRENT (ext4 on NVMe, but page-cache-hot on a 123 GB box)
  npy_shm     np.load from /dev/shm      — tmpfs (RAM-backed file, identical code path)
  npy_mmap    np.load(mmap_mode='r')     — lazy paging, no full parse
  shared_mem  multiprocessing.shared_memory — zero-copy numpy view across processes
  redis       redis GET + frombuffer     — only if a server is reachable (skipped loudly otherwise)

The number that decides the issue is not the winner — it is the **ratio of read latency to the cold
COMPUTE time it saves**. If a read costs microseconds and computing the array costs milliseconds-to-
seconds, the substrate is irrelevant no matter which one wins.

Run: /home/dev/Mulham/.venv/bin/python3 -m optimize.perf.bench_substrate --n-files 300 --readers 30
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np

CACHE = Path("/tmp/wsh_vote_cache")
SHM = Path("/dev/shm/issue58_bench")


def _pct(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    k = min(len(xs) - 1, int(round((p / 100.0) * (len(xs) - 1))))
    return xs[k]


def _stats(lat_us, n_bytes):
    return {"n_reads": len(lat_us),
            "p50_us": round(_pct(lat_us, 50), 2), "p99_us": round(_pct(lat_us, 99), 2),
            "mean_us": round(statistics.fmean(lat_us), 2),
            "MB_per_s": round((n_bytes / 1e6) / (sum(lat_us) / 1e6), 1) if sum(lat_us) else None}


# --- worker bodies (module level so ProcessPoolExecutor can pickle them) ---------------------------
def _read_npy(paths):
    lat, nb = [], 0
    for p in paths:
        t0 = time.perf_counter()
        a = np.load(p, allow_pickle=False)
        lat.append((time.perf_counter() - t0) * 1e6)
        nb += a.nbytes
    return lat, nb


def _read_mmap(paths):
    lat, nb = [], 0
    for p in paths:
        t0 = time.perf_counter()
        a = np.load(p, allow_pickle=False, mmap_mode="r")
        s = int(a[0]) if a.size else 0      # touch a page so the read is real
        lat.append((time.perf_counter() - t0) * 1e6)
        nb += a.nbytes + (s * 0)
    return lat, nb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-files", type=int, default=300)
    ap.add_argument("--readers", type=int, default=30)
    ap.add_argument("--redis-url", default=os.environ.get("ISSUE58_REDIS", ""))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    files = sorted(CACHE.glob("*.npy"))[: args.n_files]
    if not files:
        print(f"[substrate] NO cached arrays in {CACHE} — run a sweep first", flush=True)
        return 1
    sizes = [f.stat().st_size for f in files]
    arrays = {f.name: np.load(f, allow_pickle=False) for f in files}
    total_bytes = sum(a.nbytes for a in arrays.values())
    print(f"[substrate] {len(files)} real cached arrays | file bytes p50={_pct(sizes,50)} "
          f"max={max(sizes)} | in-RAM total={total_bytes/1e6:.1f} MB", flush=True)

    res = {"n_files": len(files), "readers": args.readers,
           "file_bytes_p50": _pct(sizes, 50), "file_bytes_max": max(sizes),
           "arrays_total_bytes": int(total_bytes), "substrates": {}, "skipped": {}}

    # ---- dict (floor) ----------------------------------------------------------------------------
    lat, nb = [], 0
    for name in arrays:
        t0 = time.perf_counter()
        a = arrays[name]
        lat.append((time.perf_counter() - t0) * 1e6)
        nb += a.nbytes
    res["substrates"]["dict"] = _stats(lat, nb)

    # ---- npy from /tmp (current) ----------------------------------------------------------------
    lat, nb = _read_npy(files)
    res["substrates"]["npy_tmp"] = _stats(lat, nb)

    # ---- npy from /dev/shm (tmpfs) ---------------------------------------------------------------
    shutil.rmtree(SHM, ignore_errors=True)
    SHM.mkdir(parents=True, exist_ok=True)
    shm_files = []
    for f in files:
        d = SHM / f.name
        shutil.copyfile(f, d)
        shm_files.append(d)
    lat, nb = _read_npy(shm_files)
    res["substrates"]["npy_shm"] = _stats(lat, nb)

    # ---- mmap ------------------------------------------------------------------------------------
    lat, nb = _read_mmap(files)
    res["substrates"]["npy_mmap"] = _stats(lat, nb)

    # ---- multiprocessing.shared_memory -----------------------------------------------------------
    from multiprocessing import shared_memory
    segs = {}
    try:
        for name, a in arrays.items():
            sm = shared_memory.SharedMemory(create=True, size=max(a.nbytes, 1))
            np.ndarray(a.shape, dtype=a.dtype, buffer=sm.buf)[:] = a[:]
            segs[name] = (sm, a.shape, a.dtype)
        lat, nb = [], 0
        for name, (sm, shape, dt) in segs.items():
            t0 = time.perf_counter()
            v = np.ndarray(shape, dtype=dt, buffer=sm.buf)
            _ = int(v[0]) if v.size else 0
            lat.append((time.perf_counter() - t0) * 1e6)
            nb += v.nbytes
        res["substrates"]["shared_mem"] = _stats(lat, nb)
    finally:
        for sm, _, _ in segs.values():
            sm.close()
            sm.unlink()

    # ---- redis (only if reachable) ---------------------------------------------------------------
    if args.redis_url:
        try:
            import redis  # type: ignore
            r = redis.Redis.from_url(args.redis_url)
            r.ping()
            for name, a in arrays.items():
                r.set(name, a.tobytes())
            lat, nb = [], 0
            for name, a in arrays.items():
                t0 = time.perf_counter()
                raw = r.get(name)
                v = np.frombuffer(raw, dtype=a.dtype)
                lat.append((time.perf_counter() - t0) * 1e6)
                nb += v.nbytes
            res["substrates"]["redis"] = _stats(lat, nb)
            for name in arrays:
                r.delete(name)
        except Exception as e:  # noqa: BLE001
            res["skipped"]["redis"] = f"{type(e).__name__}: {e}"
            print(f"[substrate] redis SKIPPED — {type(e).__name__}: {e}", flush=True)
    else:
        res["skipped"]["redis"] = "no --redis-url / ISSUE58_REDIS given (no server installed)"
        print("[substrate] redis SKIPPED — no server URL given", flush=True)
    res["skipped"]["arrow_plasma"] = "REMOVED from Apache Arrow in 12.0.0 (GH-33243) — not a valid option"

    # ---- concurrency: N processes hammering the two realistic candidates --------------------------
    chunks = [files[i::args.readers] for i in range(args.readers)]
    shm_chunks = [shm_files[i::args.readers] for i in range(args.readers)]
    for label, cks in (("npy_tmp", chunks), ("npy_shm", shm_chunks)):
        t0 = time.perf_counter()
        with ProcessPoolExecutor(max_workers=args.readers) as ex:
            out = list(ex.map(_read_npy, cks))
        wall = time.perf_counter() - t0
        all_lat = [x for lat_, _ in out for x in lat_]
        res["substrates"][f"{label}_x{args.readers}"] = {
            **_stats(all_lat, sum(nb_ for _, nb_ in out)), "wall_s": round(wall, 3)}

    shutil.rmtree(SHM, ignore_errors=True)

    outp = Path(args.out) if args.out else (Path(__file__).resolve().parent / "results" / "substrate_bench.json")
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(res, indent=2))
    print(json.dumps(res["substrates"], indent=2), flush=True)
    print(f"[substrate] WROTE {outp}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
