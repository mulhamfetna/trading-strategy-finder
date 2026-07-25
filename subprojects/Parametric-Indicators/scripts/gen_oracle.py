"""Offline helper: print pandas-ta reference values for an indicator on the shared fixture, to
eyeball against a new primitive. NOT part of the test suite (tests use independent pandas/numpy
oracles). Usage:  python scripts/gen_oracle.py rsi 14

Requires the optional dev oracle: pip install -r requirements-dev.txt (pandas-ta). If pandas-ta is
unavailable/incompatible with your pandas, this prints a clear message instead of crashing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pandas as pd

from tests.oracle.fixture import ohlcv

try:
    import pandas_ta as ta
except Exception as exc:  # noqa: BLE001 - optional dependency
    print(f"pandas-ta unavailable ({exc}). Install requirements-dev.txt or write an independent "
          f"pandas/numpy oracle in the test instead.")
    raise SystemExit(1)


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python scripts/gen_oracle.py <indicator> [length ...]")
        raise SystemExit(2)
    name = sys.argv[1]
    args = [int(a) for a in sys.argv[2:]]
    d = ohlcv(300)
    df = pd.DataFrame(d)
    fn = getattr(ta, name, None)
    if fn is None:
        print(f"pandas-ta has no '{name}'")
        raise SystemExit(2)
    kwargs = {"close": df.close, "high": df.high, "low": df.low, "open": df.open, "volume": df.volume}
    if args:
        kwargs["length"] = args[0]
    out = fn(**{k: v for k, v in kwargs.items()})
    print(out.tail(10).to_string())


if __name__ == "__main__":
    main()
