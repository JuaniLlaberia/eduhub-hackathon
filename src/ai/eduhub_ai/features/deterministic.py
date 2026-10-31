"""
Deterministic (P1) post features: length, timing in Argentina time, media, links, questions, emojis, trends.
Semantic fields (topic, tone, sentiment, hook, cta) are left None; the labeler fills them (stage 03).
"""
import re
import unicodedata
from zoneinfo import ZoneInfo
from eduhub_shared.metrics import length_bucket
from eduhub_shared.models import Post, PostFeatures, Trend

AR_TZ = ZoneInfo("America/Argentina/Buenos_Aires")
HOUR_BLOCKS = (("madrugada", 0, 6), ("mañana", 6, 12), ("mediodía", 12, 15), ("tarde", 15, 19), ("noche", 19, 24))
URL_PATTERN = re.compile(r"https?://\S+")
EMOJI_PATTERN = re.compile(
    "["
    "\U0001f1e6-\U0001f1ff"  # regional indicators (flags)
    "\U0001f300-\U0001faff"  # pictographs, emoticons, transport, symbols and pictographs extended
    "☀-➿"  # misc symbols and dingbats (☀ ❤ ✅ ✨)
    "⬀-⯿"  # arrows and stars (⭐ ⬆)
    "⌀-⏿"  # technical (⌚ ⏰)
    "]"
)

def extract_deterministic(post: Post, trends: list[Trend]) -> PostFeatures:
    """
    Extract the deterministic features of a post; matches_trend is None when there are no trends to compare.
    """
    local = post.created_at.astimezone(AR_TZ)
    text = post.text
    return PostFeatures(
        char_count=len(text),
        word_count=len(text.split()),
        length_bucket=length_bucket(len(text)),
        hour_local=local.hour,
        weekday=local.weekday(),
        media_type=post.media[0] if post.media else None,
        has_link=post.has_link,
        hashtag_count=len(post.hashtags),
        mention_count=len(post.mentions),
        is_question=is_question(text),
        has_emoji=bool(EMOJI_PATTERN.search(text)),
        matches_trend=matches_any_trend(text, trends) if trends else None,
    )

def hour_block(hour: int) -> str:
    """
    Return the es-AR block of a local hour: madrugada 0–6, mañana 6–12, mediodía 12–15, tarde 15–19, noche 19–24.
    """
    for name, start, end in HOUR_BLOCKS:
        if start <= hour < end:
            return name
    raise ValueError(f"hour must be between 0 and 23, got {hour}")

def is_question(text: str) -> bool:
    """
    True if the text (ignoring URLs) contains a question mark, opening or closing.
    """
    without_urls = URL_PATTERN.sub(" ", text)
    return "?" in without_urls or "¿" in without_urls

def normalize(text: str) -> str:
    """
    Lowercase, strip accents and turn '#' into spaces, for case- and accent-insensitive matching.
    """
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in decomposed if not unicodedata.combining(c)).replace("#", " ")

def matches_any_trend(text: str, trends: list[Trend]) -> bool:
    """
    True if any trend name (without '#') appears in the text as whole words, ignoring case and accents.
    """
    haystack = normalize(text)
    for trend in trends:
        needle = " ".join(normalize(trend.name).split())
        if needle and re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", haystack):
            return True
    return False
