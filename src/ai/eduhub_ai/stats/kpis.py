"""
Account KPIs. Same formulas as eduhub_shared.fakes.build_kpis; rates come from eduhub_shared.metrics.
"""
import statistics
from datetime import timedelta
from eduhub_shared.metrics import aggregate_rates
from eduhub_shared.models import AccountKPIs, Post

ONE_WEEK_S = timedelta(weeks=1).total_seconds()

def build_kpis(posts: list[Post]) -> AccountKPIs:
    """
    Compute account KPIs over posts: period, posts per week (at least one week), impressions and aggregated rates.
    """
    if not posts:
        return AccountKPIs(
            post_count=0, period_start=None, period_end=None, posts_per_week=0.0,
            avg_impressions=None, median_impressions=None, rates=aggregate_rates([]),
        )
    start = min(p.created_at for p in posts)
    end = max(p.created_at for p in posts)
    weeks = max((end - start).total_seconds() / ONE_WEEK_S, 1.0)
    impressions = [p.metrics.impressions for p in posts if p.metrics.impressions is not None]
    return AccountKPIs(
        post_count=len(posts),
        period_start=start,
        period_end=end,
        posts_per_week=len(posts) / weeks,
        avg_impressions=statistics.fmean(impressions) if impressions else None,
        median_impressions=float(statistics.median(impressions)) if impressions else None,
        rates=aggregate_rates(p.metrics for p in posts),
    )
