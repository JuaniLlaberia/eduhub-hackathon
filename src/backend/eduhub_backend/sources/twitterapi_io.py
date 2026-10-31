"""
PostSource backed by twitterapi.io (https://docs.twitterapi.io). Plain retweets are dropped.
"""
import logging
import math
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any
import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential
from eduhub_shared.errors import AccountNotFoundError, RateLimitedError, SourceUnavailableError
from eduhub_shared.models import AccountProfile, MediaType, Post, PostKind, PostMetrics, Trend
from eduhub_shared.models.common import normalize_handle

logger = logging.getLogger(__name__)

BASE_URL = "https://api.twitterapi.io"
TIMEOUT = httpx.Timeout(15.0)
ATTEMPTS = 3
MAX_BACKOFF = 4.0
PAGE_SIZE = 20
PAGE_CAP_FACTOR = 2
WOEIDS = {"Argentina": 23424747}
TWEET_DATE_FORMAT = "%a %b %d %H:%M:%S %z %Y"
MEDIA_TYPES = {"photo": MediaType.PHOTO, "video": MediaType.VIDEO, "animated_gif": MediaType.GIF}
UNAVAILABLE_MESSAGE = "No pudimos conectarnos con X en este momento. Probá de nuevo en unos minutos."
RATE_LIMITED_MESSAGE = "X está limitando las consultas. Esperá unos minutos y probá de nuevo."

class RetryableError(Exception):
    """
    A response worth retrying (429 or 5xx).
    """
    def __init__(self, status: int) -> None:
        """
        Store the HTTP status that triggered the retry.
        """
        super().__init__(f"HTTP {status}")
        self.status = status

def parse_tweet_date(value: str) -> datetime:
    """
    Parse the classic X date format, e.g. 'Tue Dec 10 07:00:30 +0000 2024'.
    """
    return datetime.strptime(value, TWEET_DATE_FORMAT).astimezone(UTC)

def tweet_kind(tweet: dict[str, Any]) -> PostKind:
    """
    Classify a non-retweet: quotes first, then replies, otherwise original.
    """
    if tweet.get("quoted_tweet"):
        return PostKind.QUOTE
    if tweet.get("isReply"):
        return PostKind.REPLY
    return PostKind.ORIGINAL

def tweet_media(tweet: dict[str, Any]) -> list[MediaType]:
    """
    Return the media types in extendedEntities, skipping unknown ones.
    """
    media = (tweet.get("extendedEntities") or {}).get("media") or []
    return [MEDIA_TYPES[m["type"]] for m in media if m.get("type") in MEDIA_TYPES]

def to_post(tweet: dict[str, Any], handle: str) -> Post:
    """
    Normalize a twitterapi.io tweet into a Post.
    """
    entities = tweet.get("entities") or {}
    author = (tweet.get("author") or {}).get("userName") or handle
    return Post(
        id=str(tweet["id"]),
        author_handle=author,
        text=tweet.get("text") or "",
        created_at=parse_tweet_date(tweet["createdAt"]),
        url=tweet.get("url") or f"https://x.com/{author}/status/{tweet['id']}",
        lang=tweet.get("lang") or None,
        kind=tweet_kind(tweet),
        media=tweet_media(tweet),
        has_link=bool(entities.get("urls")),
        hashtags=[h["text"] for h in entities.get("hashtags") or []],
        mentions=[m["screen_name"].lower() for m in entities.get("user_mentions") or []],
        conversation_id=tweet.get("conversationId") or None,
        metrics=PostMetrics(
            impressions=tweet.get("viewCount"),
            likes=tweet.get("likeCount") or 0,
            reposts=tweet.get("retweetCount") or 0,
            quotes=tweet.get("quoteCount") or 0,
            replies=tweet.get("replyCount") or 0,
            bookmarks=tweet.get("bookmarkCount") or 0,
        ),
    )

def to_profile(data: dict[str, Any]) -> AccountProfile:
    """
    Normalize a twitterapi.io user into an AccountProfile.
    """
    created = data.get("createdAt")
    return AccountProfile(
        handle=data["userName"],
        display_name=data.get("name") or data["userName"],
        bio=data.get("description") or "",
        followers_count=data.get("followers") or 0,
        following_count=data.get("following") or 0,
        posts_count=data.get("statusesCount") or 0,
        verified=bool(data.get("isVerified") or data.get("isBlueVerified") or data.get("verifiedType")),
        avatar_url=data.get("profilePicture") or None,
        created_at=datetime.fromisoformat(created) if created else None,
    )

def to_trends(body: dict[str, Any], location: str) -> list[Trend]:
    """
    Normalize a twitterapi.io trends response.
    """
    timestamp = (body.get("metadata") or {}).get("timestamp")
    observed = datetime.fromtimestamp(timestamp / 1000, tz=UTC) if timestamp else datetime.now(UTC)
    trends = [item.get("trend") or {} for item in body.get("trends") or []]
    return [
        Trend(name=t["name"], rank=t.get("rank"), location=location, observed_at=observed)
        for t in trends
        if t.get("name")
    ]

def not_found(handle: str) -> AccountNotFoundError:
    """
    Return the error for a missing or inaccessible account.
    """
    return AccountNotFoundError(f"No encontramos la cuenta @{handle} o no es pública.")

def check_status(body: dict[str, Any], handle: str | None = None) -> None:
    """
    Raise the matching contract error when twitterapi.io answers status=error.
    """
    if body.get("status") != "error":
        return
    message = str(body.get("msg") or "")
    if handle is not None and "not found" in message.lower():
        raise not_found(handle)
    logger.warning("twitterapi.io error: %s", message)
    raise SourceUnavailableError(UNAVAILABLE_MESSAGE)

def merge_pinned(kept: list[Post], pinned: dict[str, Any] | None, handle: str) -> list[Post]:
    """
    Add the pinned tweet if it is not a retweet and not already present, then sort newest first.
    """
    if pinned and not pinned.get("retweeted_tweet") and str(pinned["id"]) not in {p.id for p in kept}:
        kept = [*kept, to_post(pinned, handle)]
    return sorted(kept, key=lambda p: p.created_at, reverse=True)

class TwitterApiIoSource:
    """
    PostSource that reads public X data through twitterapi.io.
    """
    def __init__(self, api_key: str, client: httpx.AsyncClient | None = None, backoff_base: float = 0.5) -> None:
        """
        Authenticate with api_key; use client if given (tests), otherwise one client per fetch call.
        """
        self._api_key = api_key
        self._client = client
        self._backoff_base = backoff_base

    @asynccontextmanager
    async def _session(self) -> AsyncIterator[httpx.AsyncClient]:
        """
        Yield the injected client, or a short-lived one closed afterwards.
        """
        if self._client is not None:
            yield self._client
            return
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            yield client

    async def _send(self, client: httpx.AsyncClient, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        Send one GET request, raising RetryableError for 429/5xx and SourceUnavailableError for other 4xx.
        """
        response = await client.get(f"{BASE_URL}{path}", params=params, headers={"X-API-Key": self._api_key})
        if response.status_code == 429 or response.status_code >= 500:
            raise RetryableError(response.status_code)
        if response.status_code >= 400:
            logger.warning("twitterapi.io %s answered HTTP %s", path, response.status_code)
            raise SourceUnavailableError(UNAVAILABLE_MESSAGE)
        try:
            return response.json()
        except ValueError as error:
            raise SourceUnavailableError(UNAVAILABLE_MESSAGE) from error

    async def _get(self, client: httpx.AsyncClient, path: str, params: dict[str, Any]) -> dict[str, Any]:
        """
        GET path with retries on timeouts, network errors, 429 and 5xx, mapped to contract errors.
        """
        retrying = AsyncRetrying(
            stop=stop_after_attempt(ATTEMPTS),
            wait=wait_exponential(multiplier=self._backoff_base, max=MAX_BACKOFF),
            retry=retry_if_exception_type((RetryableError, httpx.TransportError)),
            reraise=True,
        )
        try:
            async for attempt in retrying:
                with attempt:
                    return await self._send(client, path, params)
        except RetryableError as error:
            logger.warning("twitterapi.io %s failed after %s attempts: HTTP %s", path, ATTEMPTS, error.status)
            if error.status == 429:
                raise RateLimitedError(RATE_LIMITED_MESSAGE) from error
            raise SourceUnavailableError(UNAVAILABLE_MESSAGE) from error
        except httpx.TransportError as error:
            logger.warning("twitterapi.io %s failed after %s attempts: %r", path, ATTEMPTS, error)
            raise SourceUnavailableError(UNAVAILABLE_MESSAGE) from error
        raise SourceUnavailableError(UNAVAILABLE_MESSAGE)

    async def fetch_profile(self, handle: str) -> AccountProfile:
        """
        Return the profile of handle. Raise AccountNotFoundError if it is missing, protected or unavailable.
        """
        handle = normalize_handle(handle)
        async with self._session() as client:
            body = await self._get(client, "/twitter/user/info", {"userName": handle})
        check_status(body, handle)
        data = body.get("data")
        if not data or data.get("protected") or data.get("unavailable"):
            raise not_found(handle)
        return to_profile(data)

    async def fetch_posts(self, handle: str, limit: int) -> list[Post]:
        """
        Return up to limit of the account's most recent non-retweet posts, newest first.
        """
        handle = normalize_handle(handle)
        max_pages = math.ceil(limit / PAGE_SIZE) * PAGE_CAP_FACTOR
        kept: list[Post] = []
        pinned: dict[str, Any] | None = None
        cursor = ""
        async with self._session() as client:
            for page in range(max_pages):
                params = {"userName": handle, "includeReplies": "true", "cursor": cursor}
                body = await self._get(client, "/twitter/user/last_tweets", params)
                check_status(body, handle)
                data = body.get("data") or {}
                if page == 0:
                    pinned = data.get("pin_tweet")
                kept += [to_post(t, handle) for t in data.get("tweets") or [] if not t.get("retweeted_tweet")]
                cursor = body.get("next_cursor") or ""
                if len(kept) >= limit or not body.get("has_next_page") or not cursor:
                    break
        unique = list({p.id: p for p in kept}.values())
        return merge_pinned(unique, pinned, handle)[:limit]

    async def fetch_trends(self, location: str = "Argentina") -> list[Trend]:
        """
        Return the current trends for location (only Argentina is supported).
        """
        woeid = WOEIDS.get(location)
        if woeid is None:
            raise SourceUnavailableError(f"No tenemos tendencias para {location}.")
        async with self._session() as client:
            body = await self._get(client, "/twitter/trends", {"woeid": woeid})
        check_status(body)
        return to_trends(body, location)
