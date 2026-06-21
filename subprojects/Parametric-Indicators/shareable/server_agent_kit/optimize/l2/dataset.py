"""L2 dataset — the single source of truth for "what L2 is allowed to touch": the box signals L1
dropped (veto + vol-gate), each tagged with the box direction and whether L1 is flat at that bar."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DroppedSignal:
    idx: int
    ts: object        # pd.Timestamp
    box_dir: str      # 'long' | 'short'
    reason: str       # 'veto' | 'vol_gate'
    l1_flat_at_idx: bool


@dataclass
class DroppedSignalSet:
    signals: list      # list[DroppedSignal]
    n_veto: int
    n_vol_gate: int

    def __len__(self) -> int:
        return len(self.signals)

    def flat_candidates(self) -> list:
        """The subset L2 may open on: dropped signals where L1 is flat at the bar."""
        return [s for s in self.signals if s.l1_flat_at_idx]


def build_dataset(l1) -> DroppedSignalSet:
    sigs = []
    n_veto = n_gate = 0
    for d in l1.dropped_signals:
        flat = not bool(l1.state_timeline[d["idx"]])
        sigs.append(DroppedSignal(idx=int(d["idx"]), ts=d["ts"], box_dir=d["box_dir"],
                                  reason=d["reason"], l1_flat_at_idx=flat))
        if d["reason"] == "veto":
            n_veto += 1
        else:
            n_gate += 1
    return DroppedSignalSet(signals=sigs, n_veto=n_veto, n_vol_gate=n_gate)
