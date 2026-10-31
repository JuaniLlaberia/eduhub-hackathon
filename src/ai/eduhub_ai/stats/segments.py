"""
Segment stats: how posts sharing a value (topic = "ahorro", media = video, ...) perform. Only scorable posts
(score not None) count. SegmentStat.avg_score holds the **median** score of the segment (robust to one viral
post); SegmentDetail adds the uncertainty used as insight evidence.
"""
import statistics
from collections import defaultdict
from collections.abc import Iterable
from eduhub_ai.stats.significance import SegmentDetail, bootstrap_ci, mann_whitney
from eduhub_shared.metrics import aggregate_rates
from eduhub_shared.models import AnalyzedPost, SegmentDimension, SegmentStat

TEXT_ONLY = "text"
__all__ = ["SegmentDetail", "build_segments", "segment_details"]

def scorable(posts: Iterable[AnalyzedPost]) -> list[AnalyzedPost]:
    """
    Keep only posts that have a score.
    """
    return [p for p in posts if p.score is not None]

def segment_value(item: AnalyzedPost, dimension: SegmentDimension) -> str | None:
    """
    Return the value of a post for a dimension (media_type "text" for text-only posts), or None if unlabeled.
    """
    features = item.features
    values = {
        SegmentDimension.TOPIC: features.topic,
        SegmentDimension.MEDIA_TYPE: features.media_type.value if features.media_type else TEXT_ONLY,
        SegmentDimension.LENGTH_BUCKET: features.length_bucket.value,
        SegmentDimension.TONE: features.tone,
        SegmentDimension.POST_KIND: item.post.kind.value,
        SegmentDimension.HOOK: features.hook,
        SegmentDimension.CTA: features.cta,
    }
    return values[dimension]

def group_by(posts: list[AnalyzedPost], dimension: SegmentDimension) -> dict[str, list[AnalyzedPost]]:
    """
    Group scorable posts by their value for dimension, skipping None values.
    """
    groups: dict[str, list[AnalyzedPost]] = defaultdict(list)
    for item in scorable(posts):
        value = segment_value(item, dimension)
        if value is not None:
            groups[value].append(item)
    return dict(groups)

def build_segments(posts: list[AnalyzedPost]) -> list[SegmentStat]:
    """
    SegmentStat for every (dimension, value) present among scorable posts, best median score first per dimension.
    """
    segments: list[SegmentStat] = []
    for dimension in SegmentDimension:
        stats = [
            SegmentStat(
                dimension=dimension,
                value=value,
                post_count=len(group),
                avg_score=statistics.median(p.score for p in group),
                engagement_rate=aggregate_rates(p.post.metrics for p in group).engagement_rate,
            )
            for value, group in group_by(posts, dimension).items()
        ]
        segments.extend(sorted(stats, key=lambda s: (-(s.avg_score or 0), s.value)))
    return segments

def segment_details(posts: list[AnalyzedPost]) -> list[SegmentDetail]:
    """
    SegmentDetail for every (dimension, value) present among scorable posts, best median score first per dimension.
    """
    details: list[SegmentDetail] = []
    for dimension in SegmentDimension:
        groups = {value: [p.score for p in group] for value, group in group_by(posts, dimension).items()}
        details.extend(details_for(dimension.value, groups))
    return details

def details_for(dimension: str, groups: dict[str, list[float]]) -> list[SegmentDetail]:
    """
    Compare each group of scores against all the other groups of the same dimension.
    """
    details = []
    for value, scores in groups.items():
        rest = [s for other, values in groups.items() if other != value for s in values]
        details.append(describe(dimension, value, scores, rest))
    return sorted(details, key=lambda d: (-d.median_score, d.value))

def describe(dimension: str, value: str, scores: list[float], rest: list[float]) -> SegmentDetail:
    """
    Median, bootstrap CI, lift (median / median of rest) and Mann-Whitney p-value of one group of scores.
    """
    median = statistics.median(scores)
    low, high = bootstrap_ci(scores)
    rest_median = statistics.median(rest) if rest else None
    return SegmentDetail(
        dimension=dimension,
        value=value,
        n=len(scores),
        median_score=median,
        ci_low=low,
        ci_high=high,
        lift_vs_rest=median / rest_median if rest_median else None,
        p_value=mann_whitney(scores, rest) if rest else None,
    )
