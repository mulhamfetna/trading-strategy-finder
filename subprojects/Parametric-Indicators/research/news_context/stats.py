"""Association, the between-bucket DIFFERENCE, the shuffled-label control, and the power floor."""
from __future__ import annotations

from typing import Tuple

import numpy as np
from scipy.stats import norm, pearsonr, spearmanr


def assoc(z: np.ndarray, r: np.ndarray) -> dict:
    """Spearman (primary) and Pearson (reported alongside).

    Spearman leads because these tails are fat: on gold, Pearson was blind (-0.012) to a real -0.193 rank
    relationship. Reporting only Pearson here would repeat that error.
    """
    z = np.asarray(z, dtype=float)
    r = np.asarray(r, dtype=float)
    ok = ~np.isnan(z) & ~np.isnan(r)
    z, r = z[ok], r[ok]
    if len(z) < 3:
        return {"spearman": float("nan"), "pearson": float("nan"), "n": int(len(z))}
    return {"spearman": float(spearmanr(z, r).statistic),
            "pearson": float(pearsonr(z, r)[0]),
            "n": int(len(z))}


def bucket_delta(z: np.ndarray, r: np.ndarray, labels: np.ndarray, a: str, b: str) -> float:
    """rho(bucket a) - rho(bucket b), on Spearman. This is THE quantity the verdict turns on.

    Comparing each bucket's own confidence interval by eye is NOT a test of their difference -- two
    intervals can overlap while the difference is significant, and vice versa (AGENTS.md, added after
    DAILY-BOX-01).
    """
    labels = np.asarray(labels, dtype=object)
    z = np.asarray(z, dtype=float)
    r = np.asarray(r, dtype=float)
    ra = assoc(z[labels == a], r[labels == a])["spearman"]
    rb = assoc(z[labels == b], r[labels == b])["spearman"]
    return float(ra - rb)


def shuffle_control(z: np.ndarray, r: np.ndarray, labels: np.ndarray, a: str, b: str,
                    draws: int, rng: np.random.Generator) -> Tuple[float, float]:
    """THE dumb control: reshuffle the context labels and see how often chance beats the real split.

    Any split of 882 numbers produces SOME spread between the halves. This asks whether the spread the
    REAL context produces is bigger than the spread a MEANINGLESS label produces. Without it, a
    context-dependence "finding" is indistinguishable from arithmetic.

    Returns (p_value, percentile_of_real_within_the_null).
    """
    if draws < 1:
        raise ValueError(f"draws must be >= 1, got {draws}")
    labels = np.asarray(labels, dtype=object)
    z = np.asarray(z, dtype=float)
    r = np.asarray(r, dtype=float)

    keep = (labels == a) | (labels == b)
    zz, rr, ll = z[keep], r[keep], labels[keep]
    real = abs(bucket_delta(zz, rr, ll, a, b))
    if np.isnan(real):
        return (float("nan"), float("nan"))

    hits = 0
    null = np.empty(draws)
    for i in range(draws):
        perm = rng.permutation(ll)
        d = abs(bucket_delta(zz, rr, perm, a, b))
        null[i] = d
        if not np.isnan(d) and d >= real:
            hits += 1
    p = (hits + 1) / (draws + 1)          # +1 so p is never exactly 0
    good = null[~np.isnan(null)]
    pct = float((good < real).mean() * 100.0) if len(good) else float("nan")
    return (float(p), pct)


def min_detectable_rho(n_a: int, n_b: int, power: float = 0.80, alpha: float = 0.05) -> float:
    """Smallest |delta rho| detectable at `power`, via the Fisher-z variance of a correlation difference.

    Reported BEFORE interpreting any null: a null that could not have detected a tradeable effect is not
    evidence of absence. This project already retracted a workstream for reporting a null at 12% power.
    """
    if n_a < 4 or n_b < 4:
        return float("nan")
    se = np.sqrt(1.0 / (n_a - 3) + 1.0 / (n_b - 3))
    need_z = (norm.ppf(1 - alpha / 2) + norm.ppf(power)) * se
    return float(np.tanh(need_z))        # back from Fisher-z into correlation units
