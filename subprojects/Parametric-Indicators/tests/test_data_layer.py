"""Tier 4 — data layer: opt-in Parquet load must be byte-identical to CSV; dataset registry hashing."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pandas as pd

_PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJ))

from loader import load_data  # noqa: E402
from optimize import to_parquet, dataset_registry  # noqa: E402


def _write_csv(p: Path):
    p.write_text(
        "datetime,open,high,low,close,volume\n"
        "2025-01-01 18:00:00,21000.25,21010.5,20995.75,21005.0,1234\n"
        "2025-01-01 22:00:00,21005.0,21030.0,21001.0,21025.5,2222\n"
        "2025-01-02 02:00:00,21025.5,21040.0,21010.0,21012.25,999\n"
    )


def test_parquet_load_is_identical_to_csv(tmp_path, monkeypatch):
    csv = tmp_path / "NQ_4h.csv"
    _write_csv(csv)
    monkeypatch.delenv("WSH_USE_PARQUET", raising=False)
    df_csv = load_data(str(csv))                       # CSV path (default)

    to_parquet.convert(str(csv))                        # writes NQ_4h.csv.parquet from the post-load frame
    assert (tmp_path / "NQ_4h.csv.parquet").exists()

    monkeypatch.setenv("WSH_USE_PARQUET", "1")
    df_parq = load_data(str(csv))                       # parquet path (opt-in)

    assert list(df_csv.columns) == list(df_parq.columns)
    assert (df_csv.dtypes == df_parq.dtypes).all(), f"{df_csv.dtypes}\n!=\n{df_parq.dtypes}"
    assert df_csv.equals(df_parq)                       # exact: shape + values + dtypes (incl. Date datetime64)


def test_parquet_disabled_by_default(tmp_path, monkeypatch):
    # with the env var unset, even if a parquet sibling exists, the CSV is read (default unchanged)
    csv = tmp_path / "NQ_1m.csv"
    _write_csv(csv)
    monkeypatch.delenv("WSH_USE_PARQUET", raising=False)
    to_parquet.convert(str(csv))
    # corrupt the parquet sibling; default path must still succeed via CSV
    (tmp_path / "NQ_1m.csv.parquet").write_bytes(b"not a parquet")
    df = load_data(str(csv))                            # must NOT touch the parquet → no error
    assert len(df) == 3 and "Close" in df.columns


def test_registry_hash_matches_hashlib(tmp_path):
    f = tmp_path / "d.csv"
    f.write_bytes(b"hello,world\n1,2\n")
    want = hashlib.sha256(f.read_bytes()).hexdigest()
    d = dataset_registry.describe(f)
    assert d["sha256"] == want and d["bytes"] == f.stat().st_size and d["path"].endswith("d.csv")


def test_registry_writes_json(tmp_path):
    f = tmp_path / "d.csv"
    f.write_bytes(b"x\n1\n")
    out = tmp_path / "reg.json"
    rec = dataset_registry.register([f], out=out)
    assert out.exists() and rec["datasets"][0]["sha256"]
