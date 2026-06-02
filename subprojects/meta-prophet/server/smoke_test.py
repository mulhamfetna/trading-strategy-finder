"""Tiny end-to-end smoke test — proves the sync -> train -> log -> results loop on GPU.

Trains a trivial linear model for a few steps on the GPU (forced gfx1031), emits a
progress line per step (becomes the streamed log), and writes structured outputs into
--out so pull.sh can bring them back. Deliberately fast (~seconds); NOT a real model.

Run by train.sh as:  python smoke_test.py --out <run_dir> [--steps N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="run output directory")
    ap.add_argument("--steps", type=int, default=20)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    import torch  # imported here so the log captures any import error

    dev = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[smoke] torch={torch.__version__} hip={getattr(torch.version,'hip',None)} device={dev}", flush=True)
    if dev != "cuda":
        print("[smoke] WARNING: GPU not available — running on CPU", flush=True)
    else:
        print(f"[smoke] gpu={torch.cuda.get_device_name(0)}", flush=True)

    torch.manual_seed(0)
    # trivial regression: learn y = 3x + 2 on the GPU
    x = torch.randn(4096, 1, device=dev)
    y = 3.0 * x + 2.0 + 0.01 * torch.randn_like(x)
    w = torch.zeros(1, 1, device=dev, requires_grad=True)
    b = torch.zeros(1, device=dev, requires_grad=True)
    opt = torch.optim.SGD([w, b], lr=0.1)

    metrics_path = os.path.join(args.out, "metrics.jsonl")
    t0 = time.time()
    with open(metrics_path, "w") as mf:
        for step in range(1, args.steps + 1):
            opt.zero_grad()
            pred = x @ w + b
            loss = torch.mean((pred - y) ** 2)
            loss.backward()
            opt.step()
            rec = {"step": step, "loss": float(loss), "w": float(w), "b": float(b),
                   "elapsed_s": round(time.time() - t0, 3)}
            mf.write(json.dumps(rec) + "\n"); mf.flush()
            print(f"[smoke] step {step:>3}/{args.steps}  loss={rec['loss']:.5f}  w={rec['w']:.3f} b={rec['b']:.3f}", flush=True)
            time.sleep(0.2)  # make the live stream visible

    result = {
        "ok": True, "device": dev,
        "torch": torch.__version__, "hip": getattr(torch.version, "hip", None),
        "gpu": torch.cuda.get_device_name(0) if dev == "cuda" else None,
        "final_w": float(w), "final_b": float(b), "final_loss": float(loss),
        "steps": args.steps, "wall_s": round(time.time() - t0, 3),
    }
    with open(os.path.join(args.out, "result.json"), "w") as f:
        json.dump(result, f, indent=2)
    print(f"[smoke] DONE -> {args.out}/result.json  (final_loss={result['final_loss']:.5f})", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
