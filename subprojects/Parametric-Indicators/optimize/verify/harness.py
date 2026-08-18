"""#118 — the claims ledger and the V1/V2/V3 harness.

WHY THIS EXISTS

The repeated failure in this project is not getting an answer wrong. It is publishing a number,
closing the topic, and discovering weeks later that the number was wrong — then redoing the work.

Ten such defects are listed in #118. **Every one produced plausible output and no error message**, and
the common property is not carelessness:

    a check was run, it passed, and the check was NOT CAPABLE OF FAILING.

  - The TradingView DST check looked at ONE series out of 649 — and picked the one that is clean.
  - The Nasdaq date check tested three dates and never their neighbours.
  - The "1.31-2.92x" H1-A ratio was checked against my notes rather than against the JSON file.

So repeating a check three times is worthless. The three verifications here are required to be able to
fail for DIFFERENT REASONS:

    V1  RE-DERIVATION      compute the same quantity by a different code path
                           -> catches implementation bugs.        BLIND to bad input.
    V2  INDEPENDENT SOURCE does a different dataset/endpoint agree?
                           -> catches bad input.                  BLIND to a shared convention error.
    V3  FALSIFICATION      state something that MUST BE FALSE and check that it is
                           -> catches an instrument that cannot fail. This is the one that was
                              missing every single time.

⭐ THE RULE THAT WOULD HAVE CAUGHT THE MOST DAMAGE:
   a check that passes on a SAMPLE must state the sample and the population. "Verified" with no
   denominator is not a result. Every claim here is therefore REQUIRED to declare `blind_spot`, and the
   runner refuses to pass a claim that does not.

⚠️ A GATE THAT HAS NEVER FAILED IS UNTESTED. `selftest.py` replays real historical defects and asserts
   that this harness FAILS on them. Run it whenever the harness changes.

    python3 optimize/verify/run.py            # run every registered claim
    python3 optimize/verify/run.py --selftest # prove the harness fails on known defects
"""
from __future__ import annotations

import math
import traceback
from dataclasses import dataclass, field
from typing import Callable

V_KINDS = ("V1", "V2", "V3")


@dataclass
class Check:
    """One verification. `fn` returns (ok: bool, detail: str).

    ⚠️ For V3 the convention is deliberately inverted-sounding: `fn` must confirm that a statement which
    WOULD BE TRUE IF THE INSTRUMENT WERE BROKEN is in fact FALSE. Write the falsifier first; if you
    cannot think of one, you do not yet understand what your measurement could get wrong.
    """
    kind: str
    name: str
    fn: Callable[[], tuple[bool, str]]

    def __post_init__(self) -> None:
        if self.kind not in V_KINDS:
            raise ValueError(f"check kind must be one of {V_KINDS}, got {self.kind!r}")


@dataclass
class Claim:
    """A published number, bound to the code that re-derives it.

    ⚠️ `value_fn` must read the COMMITTED ARTEFACT (the JSON/CSV the number came from), not recompute
    the study from scratch and not hardcode anything. The point is to catch a published figure drifting
    away from the file it claims to come from — defect #2, where "1.31-2.92x" appeared in no file at all.
    """
    id: str
    statement: str
    source: str                       # the committed file the number must be traceable to
    value_fn: Callable[[], float | str]
    expect: float | str
    blind_spot: str                   # VP-C4: what this claim CANNOT see. Required.
    tol: float = 0.0
    checks: list[Check] = field(default_factory=list)
    issue: str = ""

    def kinds(self) -> set[str]:
        return {c.kind for c in self.checks}


_REGISTRY: list[Claim] = []


def register(claim: Claim) -> Claim:
    if any(c.id == claim.id for c in _REGISTRY):
        raise ValueError(f"duplicate claim id {claim.id!r}")
    _REGISTRY.append(claim)
    return claim


def registry() -> list[Claim]:
    return list(_REGISTRY)


def _matches(got, expect, tol: float) -> bool:
    if isinstance(expect, str):
        return str(got) == expect
    try:
        return math.isfinite(float(got)) and abs(float(got) - float(expect)) <= tol
    except (TypeError, ValueError):
        return False


@dataclass
class Result:
    claim: Claim
    ok: bool
    lines: list[str]


def run_claim(c: Claim, *, require_v3: bool = True) -> Result:
    lines: list[str] = []
    ok = True

    # -- 0. structural gates (VP-C4) ------------------------------------------------------------
    # These fail BEFORE any measurement. A claim with no declared blind spot is exactly the shape of
    # the DST defect: a true statement about a sample, published as a statement about the population.
    if not c.blind_spot.strip():
        lines.append("STRUCT  no blind_spot declared — see VP-C4")
        ok = False
    if require_v3 and "V3" not in c.kinds():
        lines.append("STRUCT  no V3 falsification check — a check that cannot fail is not a check")
        ok = False
    missing = [k for k in V_KINDS if k not in c.kinds()]
    if missing:
        lines.append(f"NOTE    no {'/'.join(missing)} check registered")

    # -- 1. re-derive the published number from its committed source --------------------------------
    try:
        got = c.value_fn()
    except Exception as e:  # noqa: BLE001 — a producer that errors is a failed claim, not a crash
        lines.append(f"LEDGER  producer raised {type(e).__name__}: {e}")
        lines.extend("        " + ln for ln in traceback.format_exc().splitlines()[-3:])
        return Result(c, False, lines)

    if _matches(got, c.expect, c.tol):
        lines.append(f"LEDGER  ok    {got!r} == {c.expect!r} (tol {c.tol}) from {c.source}")
    else:
        lines.append(f"LEDGER  FAIL  re-derived {got!r}, published {c.expect!r} (tol {c.tol}) "
                     f"from {c.source}")
        ok = False

    # -- 2. the three independent verifications -----------------------------------------------------
    for chk in c.checks:
        try:
            passed, detail = chk.fn()
        except Exception as e:  # noqa: BLE001
            passed, detail = False, f"raised {type(e).__name__}: {e}"
        lines.append(f"{chk.kind:<7} {'ok  ' if passed else 'FAIL'}  {chk.name}: {detail}")
        ok = ok and passed

    return Result(c, ok, lines)


def run_all(claims: list[Claim] | None = None, *, verbose: bool = True) -> tuple[int, int]:
    claims = registry() if claims is None else claims
    passed = 0
    for c in claims:
        r = run_claim(c)
        passed += bool(r.ok)
        if verbose:
            head = "PASS" if r.ok else "FAIL"
            print(f"\n[{head}] {c.id}   {c.issue}")
            print(f"        {c.statement}")
            print(f"        blind spot: {c.blind_spot}")
            for ln in r.lines:
                print(f"        {ln}")
    return passed, len(claims)
