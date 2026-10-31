"""
When to post: the weekday × hour heatmap (Argentina time) for the chart, hour-block stats for insights (raw cells
are sparse), and the best slots. Only scorable posts count; TimeSlotStat.avg_score holds the **median** score.
"""
import statistics
from collections import defaultdict
from eduhub_ai.features.deterministic import hour_block
from eduhub_ai.stats.segments import SegmentDetail, details_for, scorable
from eduhub_shared.models import AnalyzedPost, TimeSlotStat

WEEKEND = frozenset({5, 6})
WEEKDAY_LABEL = "semana"
WEEKEND_LABEL = "fin de semana"
MIN_RELIABLE_SLOT_POSTS = 2

def build_heatmap(posts: list[AnalyzedPost]) -> list[TimeSlotStat]:
    """
    One TimeSlotStat per (weekday, hour) with scorable posts, sorted by weekday then hour.
    """
    groups: dict[tuple[int, int], list[float]] = defaultdict(list)
    for item in scorable(posts):
        groups[(item.features.weekday, item.features.hour_local)].append(item.score)
    return [
        TimeSlotStat(weekday=w, hour=h, post_count=len(scores), avg_score=statistics.median(scores))
        for (w, h), scores in sorted(groups.items())
    ]

def day_type(weekday: int) -> str:
    """
    "fin de semana" for Saturday/Sunday, "semana" otherwise.
    """
    return WEEKEND_LABEL if weekday in WEEKEND else WEEKDAY_LABEL

def hour_block_stats(posts: list[AnalyzedPost]) -> list[SegmentDetail]:
    """
    SegmentDetails for dimensions "hour_block", "day_type" and "hour_block_day_type" (e.g. "noche, fin de semana").
    """
    blocks: dict[str, list[float]] = defaultdict(list)
    days: dict[str, list[float]] = defaultdict(list)
    combos: dict[str, list[float]] = defaultdict(list)
    for item in scorable(posts):
        block = hour_block(item.features.hour_local)
        day = day_type(item.features.weekday)
        blocks[block].append(item.score)
        days[day].append(item.score)
        combos[f"{block}, {day}"].append(item.score)
    return [
        *details_for("hour_block", dict(blocks)),
        *details_for("day_type", dict(days)),
        *details_for("hour_block_day_type", dict(combos)),
    ]

def best_time_slots(heatmap: list[TimeSlotStat], limit: int = 3) -> list[TimeSlotStat]:
    """
    Top slots by median score, preferring slots with at least two posts (falls back to single-post slots).
    """
    scored = [s for s in heatmap if s.avg_score is not None]
    reliable = [s for s in scored if s.post_count >= MIN_RELIABLE_SLOT_POSTS] or scored
    return sorted(reliable, key=lambda s: (-(s.avg_score or 0), s.weekday, s.hour))[:limit]
