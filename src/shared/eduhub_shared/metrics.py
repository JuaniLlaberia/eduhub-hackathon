"""
Contract C5: metric formulas. Every team uses these; nobody re-implements them.
"""
from collections.abc import Iterable
from eduhub_shared.models import LengthBucket, PostMetrics, PostRates

SHORT_MAX_CHARS = 100
MEDIUM_MAX_CHARS = 200
EMPTY_RATES = PostRates(
    engagement_rate=None, save_rate=None, share_rate=None, reply_rate=None, like_rate=None, passive_rate=None
)

def total_interactions(metrics: PostMetrics) -> int:
    """
    Return likes + reposts + quotes + replies + bookmarks.
    """
    return metrics.likes + metrics.reposts + metrics.quotes + metrics.replies + metrics.bookmarks

def _rates(likes: int, reposts: int, quotes: int, replies: int, bookmarks: int, impressions: int | None) -> PostRates:
    """
    Compute rates from raw counters; all None when impressions are missing or zero.
    """
    if not impressions:
        return EMPTY_RATES
    engagement = (likes + reposts + quotes + replies + bookmarks) / impressions
    return PostRates(
        engagement_rate=engagement,
        save_rate=bookmarks / impressions,
        share_rate=(reposts + quotes) / impressions,
        reply_rate=replies / impressions,
        like_rate=likes / impressions,
        passive_rate=max(0.0, 1.0 - engagement),
    )

def compute_rates(metrics: PostMetrics) -> PostRates:
    """
    Compute the rates of one post over its impressions.
    """
    return _rates(
        metrics.likes, metrics.reposts, metrics.quotes, metrics.replies, metrics.bookmarks, metrics.impressions
    )

def aggregate_rates(metrics: Iterable[PostMetrics]) -> PostRates:
    """
    Compute account-level rates as sum(counter) / sum(impressions), using only posts with impressions.
    """
    with_views = [m for m in metrics if m.impressions]
    return _rates(
        sum(m.likes for m in with_views),
        sum(m.reposts for m in with_views),
        sum(m.quotes for m in with_views),
        sum(m.replies for m in with_views),
        sum(m.bookmarks for m in with_views),
        sum(m.impressions or 0 for m in with_views),
    )

def length_bucket(char_count: int) -> LengthBucket:
    """
    Bucket a post by character count: short <= 100 < medium <= 200 < long.
    """
    if char_count <= SHORT_MAX_CHARS:
        return LengthBucket.SHORT
    if char_count <= MEDIUM_MAX_CHARS:
        return LengthBucket.MEDIUM
    return LengthBucket.LONG
