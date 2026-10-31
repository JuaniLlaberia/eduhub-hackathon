"""
Performance score (research D2, option c): the geometric mean of relative engagement rate and relative reach.

    er_rel    = ER(post) / median(ER)                      ER from eduhub_shared.metrics.compute_rates
    reach_rel = impressions(post) / median(impressions)
    score     = sqrt(er_rel * reach_rel)                   1.0 = the account's typical post

Medians are taken over the posts passed in (the scorable ones, see features.selection) that have impressions.
Medians, not means, so one viral post barely moves everyone else's score. The score is None when a post has
no impressions or a median is 0.
"""
import math
import statistics
from eduhub_shared.metrics import compute_rates
from eduhub_shared.models import Post

def score_posts(posts: list[Post]) -> dict[str, float | None]:
    """
    Score each post against the medians of posts; returns post id → score (None when not computable).
    """
    engagement = {p.id: compute_rates(p.metrics).engagement_rate for p in posts}
    measured = [p for p in posts if engagement[p.id] is not None]
    if not measured:
        return {p.id: None for p in posts}
    median_er = statistics.median(engagement[p.id] for p in measured)
    median_reach = statistics.median(p.metrics.impressions for p in measured)
    if median_er <= 0 or median_reach <= 0:
        return {p.id: None for p in posts}
    return {p.id: _score(engagement[p.id], p.metrics.impressions, median_er, median_reach) for p in posts}

def _score(er: float | None, impressions: int | None, median_er: float, median_reach: float) -> float | None:
    """
    Geometric mean of er / median_er and impressions / median_reach, or None without impressions.
    """
    if er is None or not impressions:
        return None
    return math.sqrt((er / median_er) * (impressions / median_reach))
