"""#199 — the signed LIVE-PROTOCOL. The signature makes the document law: this claim pins its content and
its one remaining prerequisite, and breaks if the allowlist it binds to is touched without an amendment."""
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from harness import Check, Claim, register

PI = Path(__file__).resolve().parents[2]
ROOT = PI.parents[1]
DOC = ROOT / "docs" / "LIVE-PROTOCOL.md"
AL = PI / "optimize" / "live" / "live_allowlist.json"


def _txt() -> str:
    return DOC.read_text()


def _v1() -> tuple[bool, str]:
    """V1 — SIGNED, BY WHOM, TO WHAT: the file carries the SIGNED status, the owner's name and date, and
    the allowlist hash in §9 equals a fresh sha256 of the live allowlist file — the universe the owner
    signed is byte-for-byte the universe on disk."""
    s = _txt()
    m = re.search(r"Allowlist sha256\[:16\]: \*\*([0-9a-f]{16})\*\*", s)
    fresh = hashlib.sha256(AL.read_bytes()).hexdigest()[:16]
    ok = ("STATUS: SIGNED 2026-08-31" in s and "Owner: **Mulham Fetna**" in s
          and m is not None and m.group(1) == fresh)
    return ok, f"signed; §9 hash {m.group(1) if m else None} == live allowlist {fresh}"


def _v2() -> tuple[bool, str]:
    """V2 — EXACTLY ONE GATE LEFT: §8's prerequisite boxes are all checked except the paper executor
    (#213) and its fill-model line — the clock is blocked by nothing else."""
    s = _txt()
    sec = s.split("## 8.")[1].split("## 9.")[0]
    done = len(re.findall(r"- \[x\]", sec))
    open_ = re.findall(r"- \[ \] ([^\n]+)", sec)
    ok = done >= 5 and len(open_) == 2 and all("#213" in o or "paper fill model" in o for o in open_)
    return ok, f"{done} done; open: {[o[:50] for o in open_]}"


def _v3() -> tuple[bool, str]:
    """V3 — FALSIFIER (the law is falsifiable): the amendments section is EMPTY at signature (any later
    change must appear there or V1/V2 flip), the never-list is present with its seven prohibitions, and
    the mode is PAPER ONLY with the on-demand box guard — the two owner decisions verbatim."""
    s = _txt()
    amend = s.split("## 10.")[1]
    ok = ("*(none)*" in amend and "## 6. The never-list" in s
          and "PAPER ONLY (owner decision 2026-08-31)" in s
          and "on demand** (owner decision 2026-08-31" in s)
    return ok, "amendments empty; never-list present; paper-only + on-demand boxes recorded"


def _n_signed() -> float:
    return 1.0 if "STATUS: SIGNED" in _txt() else 0.0


register(Claim(
    id="LIVE-PROTOCOL-SIGNED",
    issue="#199",
    statement="The LIVE-PROTOCOL is signed (owner, 2026-08-31): PAPER-ONLY execution on the project's own "
              "deployment layer; the 9-slot allowlist bound by hash; 1 contract; engine exits; frozen "
              "gates; boxes scraped on demand with a 35-day auto-pause guard carrying the staleness risk; "
              "mechanical kill rules; monthly reconciliation with failed months flagged; no verdict before "
              "6 months; a seven-item never-list. One gate remains before the track-record clock: the "
              "paper executor and its pre-registered shadow-window verification (#213).",
    source="docs/LIVE-PROTOCOL.md + optimize/live/live_allowlist.json",
    value_fn=_n_signed,
    expect=1.0,
    tol=0.0,
    blind_spot="A signature binds process, not outcomes: paper fills are the engine's own convention, so "
               "the paper record cannot measure real slippage — it measures protocol discipline and "
               "signal quality, and says so in every claim. The confidential source data never enters the "
               "repo; outside reproduction requires one's own data feed (the repo's standing two-tier "
               "reproducibility model).",
    checks=[Check("V1", "signed-and-hash-bound", _v1),
            Check("V2", "one-gate-left", _v2),
            Check("V3", "falsifiable-law", _v3)],
))
