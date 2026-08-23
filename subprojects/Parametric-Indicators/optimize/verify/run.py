"""#118 — run the claims ledger.

    python3 optimize/verify/run.py             # re-derive every published number
    python3 optimize/verify/run.py --selftest  # prove the harness FAILS on known historical defects

⚠️ A GATE THAT HAS NEVER FAILED IS UNTESTED. `--selftest` is not optional decoration: it replays the
real defects from #118 and asserts this harness rejects them. Run it whenever the harness changes.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import claims_news2  # noqa: F401,E402  — importing registers the claims
import claims_news3  # noqa: F401,E402  — WS-NEWS3 (#124): P1 ride-through claims
import claims_news4  # noqa: F401,E402  — WS-NEWS4 (#136): wide-series premium scan claims
import claims_escpi  # noqa: F401,E402  — WS-ESCPI (#139): the ES CPI-alone study claims
import claims_fusion  # noqa: F401,E402  — WS-FUSION (#152): fusion workstream claims
import claims_earn2  # noqa: F401,E402  — WS-EARN return (#169): earnings power-model claims
import claims_xni  # noqa: F401,E402  — XNI phase 3 (#172): collision/composition claims
import claims_fwd  # noqa: F401,E402  — WS-FWD (#176): forward-OOS extension/books/dashboard claims
import claims_fwd2  # noqa: F401,E402  — WS-FWD round 2 (#179): box refresh, real forward window, ES fix
from harness import run_all, registry  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true",
                    help="replay known defects and require the harness to reject them")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        import selftest
        return selftest.main()

    print("=" * 100)
    print("CLAIMS LEDGER — every published number re-derived from the file it came from")
    print("=" * 100)
    ok, total = run_all(verbose=not a.quiet)
    print("\n" + "=" * 100)
    print(f"{ok}/{total} claims pass")
    if ok != total:
        print("\n⚠️ A FAILING CLAIM MEANS A PUBLISHED NUMBER NO LONGER MATCHES ITS SOURCE.")
        print("   Fix the document or the code — do NOT adjust `expect` to match. That is how a")
        print("   ledger becomes a rubber stamp.")
    print("=" * 100)
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
