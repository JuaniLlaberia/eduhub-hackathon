"""
The pattern-model interface: feature rows from PostFeatures, adjusted effects, and the data-sufficiency rule.
Categorical features are compared with their most common level (the baseline); binary ones as "sí" vs "no".
"""
from collections import Counter
from dataclasses import dataclass
from typing import Protocol
from eduhub_ai.features.deterministic import hour_block
from eduhub_shared.models import PostFeatures

type FeatureRow = dict[str, str | bool]
MIN_POSTS = 30
MIN_LEVEL_POSTS = 3
OTHER_LEVEL = "otros"
YES = "sí"
NO = "no"
WEEKEND_DAYS = frozenset({5, 6})

@dataclass(frozen=True)
class Effect:
    """
    Adjusted effect of one feature level vs its baseline: score multiplier with a bootstrap CI, and how many
    posts have that level.
    """
    feature: str
    value: str
    baseline: str
    multiplier: float
    ci_low: float
    ci_high: float
    n: int

    @property
    def significant(self) -> bool:
        """
        True when the CI excludes 1.0 (no effect) and at least MIN_LEVEL_POSTS posts support it.
        """
        return self.n >= MIN_LEVEL_POSTS and (self.ci_low > 1.0 or self.ci_high < 1.0)

class PatternModel(Protocol):
    """
    A per-account model of log(score) from feature rows.
    """
    def fit(self, rows: list[FeatureRow], scores: list[float]) -> None:
        """
        Fit on the scorable posts' rows and scores.
        """
        ...

    def effects(self) -> list[Effect]:
        """
        Adjusted effect of every feature level kept by the fit.
        """
        ...

    def predict(self, row: FeatureRow) -> float:
        """
        Predicted score (1.0 = typical post) for a row; unknown levels count as the baseline.
        """
        ...

def feature_row(features: PostFeatures) -> FeatureRow:
    """
    Categorical and binary model features of a post; unlabeled (None) features are left out.
    """
    row: FeatureRow = {
        "media_type": features.media_type.value if features.media_type else "text",
        "length_bucket": features.length_bucket.value,
        "hour_block": hour_block(features.hour_local),
        "weekend": features.weekday in WEEKEND_DAYS,
        "has_link": features.has_link,
        "is_question": features.is_question,
        "has_emoji": features.has_emoji,
        "hashtags": "0" if features.hashtag_count == 0 else ("1" if features.hashtag_count == 1 else "2+"),
    }
    for name in ("topic", "tone", "hook", "cta"):
        value = getattr(features, name)
        if value is not None:
            row[name] = value
    if features.matches_trend is not None:
        row["matches_trend"] = features.matches_trend
    return row

@dataclass(frozen=True)
class FeaturePlan:
    """
    Which levels each feature keeps after merging rare ones, and its baseline (most common level).
    Binary features keep levels {"sí", "no"} with baseline "no".
    """
    levels: dict[str, frozenset[str]]
    baselines: dict[str, str]
    binary: frozenset[str]

    def encode(self, row: FeatureRow) -> dict[str, float]:
        """
        One-hot (minus baseline) encoding of a row; unknown or dropped levels encode as the baseline.
        """
        encoded: dict[str, float] = {}
        for feature, levels in self.levels.items():
            value = level_of(row.get(feature))
            if value is None:
                continue
            if value not in levels:
                value = OTHER_LEVEL if OTHER_LEVEL in levels else self.baselines[feature]
            if value != self.baselines[feature]:
                encoded[f"{feature}={value}"] = 1.0
        return encoded

def level_of(value: str | bool | None) -> str | None:
    """
    A row value as a level name (booleans become "sí"/"no").
    """
    if isinstance(value, bool):
        return YES if value else NO
    return value

def plan_features(rows: list[FeatureRow], min_level: int = MIN_LEVEL_POSTS) -> FeaturePlan:
    """
    Merge levels with fewer than min_level posts into "otros" (dropped if still rare), and drop features
    left with a single level.
    """
    levels: dict[str, frozenset[str]] = {}
    baselines: dict[str, str] = {}
    binary = {name for row in rows for name, value in row.items() if isinstance(value, bool)}
    names = sorted({name for row in rows for name in row})
    for name in names:
        counts = Counter(level_of(row[name]) for row in rows if name in row)
        rare = sum(c for level, c in counts.items() if c < min_level)
        kept = {level: c for level, c in counts.items() if c >= min_level}
        if name not in binary and rare >= min_level:
            kept[OTHER_LEVEL] = kept.get(OTHER_LEVEL, 0) + rare
        if len(kept) < 2:
            continue
        levels[name] = frozenset(kept)
        baselines[name] = NO if name in binary and NO in kept else max(sorted(kept), key=lambda lv: kept[lv])
    return FeaturePlan(levels=levels, baselines=baselines, binary=frozenset(binary))

def can_fit(rows: list[FeatureRow], scores: list[float]) -> bool:
    """
    Enough data for a pattern model: at least MIN_POSTS scorable posts and at least one usable feature.
    """
    return len(rows) == len(scores) and len(rows) >= MIN_POSTS and bool(plan_features(rows).levels)
