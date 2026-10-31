"""
Which posts are scorable (research D7): originals and quotes with impressions, at least 48 h old.
Replies and reposts behave differently, and recent posts are still accumulating views.
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from eduhub_shared.models import Post, PostKind

MIN_SCORABLE_POSTS = 20
DEFAULT_MIN_AGE = timedelta(hours=48)
SCORABLE_KINDS = frozenset({PostKind.ORIGINAL, PostKind.QUOTE})

class ExclusionReason(StrEnum):
    """
    Why a post is left out of scoring.
    """
    REPLY = "reply"
    REPOST = "repost"
    TOO_RECENT = "too_recent"
    NO_IMPRESSIONS = "no_impressions"

@dataclass(frozen=True)
class SelectionResult:
    """
    Scorable posts (input order kept) and the reason each other post was excluded, by post id.
    """
    scorable: list[Post] = field(default_factory=list)
    excluded: dict[str, ExclusionReason] = field(default_factory=dict)

def select_scorable(posts: list[Post], now: datetime, min_age: timedelta = DEFAULT_MIN_AGE) -> SelectionResult:
    """
    Split posts into scorable ones and excluded ones (with a reason). now is injected, never read from the clock.
    """
    result = SelectionResult()
    for post in posts:
        reason = exclusion_reason(post, now - min_age)
        if reason is None:
            result.scorable.append(post)
        else:
            result.excluded[post.id] = reason
    return result

def exclusion_reason(post: Post, cutoff: datetime) -> ExclusionReason | None:
    """
    Return why post is not scorable (kind first, then age, then views), or None if it is.
    """
    if post.kind not in SCORABLE_KINDS:
        return ExclusionReason.REPLY if post.kind == PostKind.REPLY else ExclusionReason.REPOST
    if post.created_at > cutoff:
        return ExclusionReason.TOO_RECENT
    if not post.metrics.impressions:
        return ExclusionReason.NO_IMPRESSIONS
    return None
