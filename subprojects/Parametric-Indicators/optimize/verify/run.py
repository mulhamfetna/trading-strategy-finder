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
import claims_orb  # noqa: F401,E402  — WS-ORB (#183): opening-range breakout grid, 225 cells, no positive
from harness import run_all, registry  # noqa: E402


def evidence_tracked(verbose: bool = True) -> list[str]:
    """Positioning audit 2026-08-29 §3.1 — close the CLASS, not the instance.

    A claim whose `source` names a file that is not in git passes where it was written and nowhere else
    (TV-PREVIOUS-IS-POINT-IN-TIME / TV-FORECAST-NOT-COPIED-FROM-ACTUAL read an untracked CSV for 3 weeks;
    the ledger only caught it when run in a second checkout). So: every path-like token in every claim's
    `source` must resolve to at least one git-TRACKED file. Tokens are resolved against the engine dir and
    the repo root; `{A,B}` braces and `{INST}`-style placeholders become wildcards; free text is ignored.
    Returns the list of "CLAIM-ID: token" offenders (empty = clean)."""
    import re as _re
    import subprocess as _sp
    from fnmatch import fnmatch as _fn
    from harness import registry as _registry
    pi = Path(__file__).resolve().parents[2]          # optimize/verify/run.py -> the engine dir
    root = pi.parents[1]                                 # -> the repo root (git ls-files paths are relative to it)
    tracked = set(_sp.run(["git", "ls-files"], capture_output=True, text=True, cwd=str(root)).stdout.split("\n"))
    rel_pi = str(pi.relative_to(root))
    bad: list[str] = []
    for c in _registry():
        last_dir = ""                                                    # "… gate.json + shots/" -> shots/ is relative to the previous token's dir
        for tok in _re.findall(r"[A-Za-z0-9_./*{},-]+/[A-Za-z0-9_./*{},-]*", c.source):
            tok = tok.strip(".,()")
            if not tok:
                continue
            pat = _re.sub(r"\{[^}]*\}", "*", tok)                       # {NQ,RTY} / {INST} -> *
            if pat.endswith("/"):                                        # a directory: any tracked file under it
                cands = [pat, f"{rel_pi}/{pat}"] + ([f"{last_dir}/{pat}", f"{rel_pi}/{last_dir}/{pat}"] if last_dir else [])
                hit = any(f.startswith(cp) for cp in cands for f in tracked if f)
            else:
                last = pat.rsplit("/", 1)[-1]
                if "." not in last and "*" not in last:                  # prose like "p2_power_events/result"
                    continue
                cands = [pat, f"{rel_pi}/{pat}"]
                hit = any(_fn(f, cp) for cp in cands for f in tracked if f)
                last_dir = pat.rsplit("/", 1)[0] if "/" in pat else last_dir
            if not hit:
                bad.append(f"{c.id}: {tok}")
    if verbose:
        print(f"EVIDENCE TRACKED  {'OK — every claim source resolves to a git-tracked file' if not bad else 'FAIL'}")
        for b in bad:
            print(f"        untracked/missing source: {b}")
    return bad


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
    untracked = evidence_tracked(verbose=True)
    print("\n" + "=" * 100)
    print(f"{ok}/{total} claims pass")
    if untracked:
        print(f"\n⚠️ {len(untracked)} CLAIM SOURCE(S) ARE NOT IN GIT — the ledger cannot be re-run elsewhere. Commit the evidence.")
        ok = -1
    if ok != total:
        print("\n⚠️ A FAILING CLAIM MEANS A PUBLISHED NUMBER NO LONGER MATCHES ITS SOURCE.")
        print("   Fix the document or the code — do NOT adjust `expect` to match. That is how a")
        print("   ledger becomes a rubber stamp.")
    print("=" * 100)
    return 0 if ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
