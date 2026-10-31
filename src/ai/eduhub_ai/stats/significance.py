"""
Uncertainty and significance for segment stats, so no insight rests on two lucky posts.
Everything is deterministic: the bootstrap uses a fixed seed.
"""
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
import numpy as np
from scipy.stats import mannwhitneyu

DEFAULT_RESAMPLES = 1000
DEFAULT_LEVEL = 0.9
MIN_N = 3
ALPHA = 0.1
TYPICAL_SCORE = 1.0

@dataclass(frozen=True)
class SegmentDetail:
    """
    One segment with its sample size, median score, 90% bootstrap CI, lift vs the other posts and p-value.
    dimension is a SegmentDimension value or a timing dimension ("hour_block", "day_type", ...).
    """
    dimension: str
    value: str
    n: int
    median_score: float
    ci_low: float
    ci_high: float
    lift_vs_rest: float | None
    p_value: float | None

def bootstrap_ci(
    values: Sequence[float],
    stat: Callable[..., float] = np.median,
    n_resamples: int = DEFAULT_RESAMPLES,
    seed: int = 0,
    level: float = DEFAULT_LEVEL,
) -> tuple[float, float]:
    """
    Percentile bootstrap confidence interval of stat(values). Raises ValueError on empty input.
    """
    data = np.asarray(values, dtype=float)
    if data.size == 0:
        raise ValueError("bootstrap_ci needs at least one value")
    if data.size == 1:
        return float(data[0]), float(data[0])
    rng = np.random.default_rng(seed)
    resamples = data[rng.integers(0, data.size, size=(n_resamples, data.size))]
    estimates = stat(resamples, axis=1)
    tail = (1 - level) / 2 * 100
    low, high = np.percentile(estimates, [tail, 100 - tail])
    return float(low), float(high)

def mann_whitney(group: Sequence[float], rest: Sequence[float]) -> float:
    """
    Two-sided Mann-Whitney U p-value of group vs rest; 1.0 when either side is empty or all values tie.
    """
    if not group or not rest:
        return 1.0
    p_value = float(mannwhitneyu(group, rest, alternative="two-sided").pvalue)
    return 1.0 if math.isnan(p_value) else p_value

def is_significant(detail: SegmentDetail, min_n: int = MIN_N, alpha: float = ALPHA) -> bool:
    """
    True when the segment has at least min_n posts and either its CI excludes the typical score (1.0) or the
    Mann-Whitney test against the rest gives p < alpha.
    """
    if detail.n < min_n:
        return False
    excludes_typical = detail.ci_low > TYPICAL_SCORE or detail.ci_high < TYPICAL_SCORE
    return excludes_typical or (detail.p_value is not None and detail.p_value < alpha)
