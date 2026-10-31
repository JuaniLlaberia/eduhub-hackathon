import copy
import json
from datetime import UTC, datetime
from pathlib import Path
import httpx
import pytest
from eduhub_backend.sources.twitterapi_io import TwitterApiIoSource
from eduhub_shared.errors import AccountNotFoundError, RateLimitedError, SourceUnavailableError
from eduhub_shared.models import MediaType, PostKind
from eduhub_shared.testing import check_post_source

DATA = Path(__file__).parent / "data" / "twitterapi_io"
HANDLE = "mercadolibre"
KEY = "test-key"
REPLY_ID = "2115535887237108220"
PHOTO_ID = "2115535881016893674"
VIDEO_ID = "2111222226246848884"
LINK_ID = "2098161748624941499"
KEPT_COUNT = 22

def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))

def page1():
    return load("last_tweets_page1.json")

def page2():
    return load("last_tweets_page2.json")

def last_page():
    return {"status": "success", "code": 0, "msg": "success", "data": {"pin_tweet": None, "tweets": []},
            "has_next_page": False, "next_cursor": ""}

def all_tweets():
    return page1()["data"]["tweets"] + page2()["data"]["tweets"]

def kept_tweets():
    return [t for t in all_tweets() if not t.get("retweeted_tweet")]

def retweet_ids():
    return {t["id"] for t in all_tweets() if t.get("retweeted_tweet")}

class FakeApi:
    """
    MockTransport handler serving the recorded responses; tests replace entries to simulate other cases.
    """
    def __init__(self):
        self.requests = []
        self.user_info = load("user_info.json")
        self.trends = load("trends_ar.json")
        first, second = page1(), page2()
        self.pages = {"": first, first["next_cursor"]: second, second["next_cursor"]: last_page()}
        self.failures = []

    def __call__(self, request):
        self.requests.append(request)
        if self.failures:
            failure = self.failures.pop(0)
            if isinstance(failure, Exception):
                raise failure
            return httpx.Response(failure, json={"error": failure, "message": "fail"})
        path = request.url.path
        if path == "/twitter/user/info":
            return httpx.Response(200, json=self.user_info)
        if path == "/twitter/user/last_tweets":
            return httpx.Response(200, json=self.pages[request.url.params.get("cursor", "")])
        if path == "/twitter/trends":
            return httpx.Response(200, json=self.trends)
        return httpx.Response(404, json={"error": 404, "message": "not found"})

    def calls(self, path):
        return [r for r in self.requests if r.url.path == path]

@pytest.fixture
def api():
    return FakeApi()

@pytest.fixture
def source(api):
    client = httpx.AsyncClient(transport=httpx.MockTransport(api))
    return TwitterApiIoSource(KEY, client=client, backoff_base=0)

async def test_honours_the_post_source_contract(source):
    snapshot = await check_post_source(source, HANDLE, limit=20)
    assert snapshot.profile.handle == HANDLE

async def test_requests_use_the_api_key_and_base_url(source, api):
    await source.fetch_profile(HANDLE)
    request = api.requests[0]
    assert request.url.host == "api.twitterapi.io"
    assert request.url.scheme == "https"
    assert request.headers["x-api-key"] == KEY
    assert request.url.params["userName"] == HANDLE

async def test_handle_is_normalized_before_the_request(source, api):
    await source.fetch_profile("@MercadoLibre")
    assert api.requests[0].url.params["userName"] == HANDLE

async def test_profile_mapping(source):
    profile = await source.fetch_profile(HANDLE)
    assert profile.handle == HANDLE
    assert profile.display_name == "Mercado Libre"
    assert profile.bio.startswith("Cuenta oficial de Mercado Libre.")
    assert profile.followers_count == 227835
    assert profile.following_count == 15
    assert profile.posts_count == 18400
    assert profile.avatar_url == "https://pbs.twimg.com/profile_images/1891548807097200640/JXl94xdC_normal.jpg"
    assert profile.created_at == datetime(2008, 6, 17, 2, 46, 20, tzinfo=UTC)

@pytest.mark.parametrize(
    ("fields", "expected"),
    [
        ({"isVerified": False, "isBlueVerified": False, "verifiedType": "Business"}, True),
        ({"isVerified": True, "isBlueVerified": False, "verifiedType": ""}, True),
        ({"isVerified": False, "isBlueVerified": True, "verifiedType": None}, True),
        ({"isVerified": False, "isBlueVerified": False, "verifiedType": ""}, False),
        ({"isVerified": False, "isBlueVerified": False, "verifiedType": None}, False),
    ],
)
async def test_verified_is_any_of_the_three_flags(source, api, fields, expected):
    api.user_info["data"].update(fields)
    assert (await source.fetch_profile(HANDLE)).verified is expected

async def test_unknown_user_is_account_not_found(source, api):
    api.user_info = load("user_info_not_found.json")
    with pytest.raises(AccountNotFoundError) as error:
        await source.fetch_profile("zz_no_such_user")
    assert error.value.message.strip()

@pytest.mark.parametrize("fields", [{"protected": True}, {"unavailable": True, "unavailableReason": "Suspended"}])
async def test_inaccessible_account_is_account_not_found(source, api, fields):
    api.user_info["data"].update(fields)
    with pytest.raises(AccountNotFoundError):
        await source.fetch_profile(HANDLE)

async def test_posts_drop_retweets_and_follow_every_page(source, api):
    posts = await source.fetch_posts(HANDLE, 500)
    assert [p.id for p in posts] == [t["id"] for t in kept_tweets()]
    assert len(posts) == KEPT_COUNT
    assert not {p.id for p in posts} & retweet_ids()
    assert len(api.calls("/twitter/user/last_tweets")) == 3

async def test_posts_request_includes_replies(source, api):
    await source.fetch_posts(HANDLE, 20)
    request = api.calls("/twitter/user/last_tweets")[0]
    assert request.url.params["userName"] == HANDLE
    assert request.url.params["includeReplies"] == "true"

async def test_cursor_from_the_previous_page_is_sent(source, api):
    await source.fetch_posts(HANDLE, 500)
    cursors = [r.url.params.get("cursor", "") for r in api.calls("/twitter/user/last_tweets")]
    assert cursors == ["", page1()["next_cursor"], page2()["next_cursor"]]

async def test_limit_stops_paging_early(source, api):
    posts = await source.fetch_posts(HANDLE, 5)
    assert [p.id for p in posts] == [t["id"] for t in kept_tweets()[:5]]
    assert len(api.calls("/twitter/user/last_tweets")) == 1

async def test_paging_is_capped_at_twice_the_needed_pages(source, api):
    retweets_only = page1()
    retweets_only["data"]["tweets"] = [t for t in retweets_only["data"]["tweets"] if t.get("retweeted_tweet")]
    retweets_only["has_next_page"] = True
    retweets_only["next_cursor"] = "again"
    api.pages = {"": retweets_only, "again": retweets_only}
    posts = await source.fetch_posts(HANDLE, 10)
    assert posts == []
    assert len(api.calls("/twitter/user/last_tweets")) == 2

async def test_paging_stops_when_there_is_no_next_page(source, api):
    first = page1()
    first["has_next_page"] = False
    api.pages = {"": first}
    posts = await source.fetch_posts(HANDLE, 500)
    assert len(posts) == len([t for t in first["data"]["tweets"] if not t.get("retweeted_tweet")])
    assert len(api.calls("/twitter/user/last_tweets")) == 1

async def test_post_mapping(source):
    posts = {p.id: p for p in await source.fetch_posts(HANDLE, 500)}
    post = posts[PHOTO_ID]
    assert post.author_handle == HANDLE
    assert post.text == next(t["text"] for t in kept_tweets() if t["id"] == PHOTO_ID)
    assert post.created_at == datetime(2026, 10, 28, 20, 7, 13, tzinfo=UTC)
    assert post.url == f"https://x.com/MercadoLibre/status/{PHOTO_ID}"
    assert post.lang == "es"
    assert post.kind == PostKind.ORIGINAL
    assert post.media == [MediaType.PHOTO]
    assert post.hashtags == ["EfectoMELI"]
    assert post.mentions == []
    assert post.has_link is False
    assert post.conversation_id == PHOTO_ID
    metrics = post.metrics
    counts = (metrics.impressions, metrics.likes, metrics.reposts, metrics.quotes, metrics.replies, metrics.bookmarks)
    assert counts == (16780, 59, 12, 3, 11, 2)
    assert metrics.detail_expands is None
    assert metrics.profile_clicks is None
    assert metrics.link_clicks is None

async def test_reply_kind_and_conversation(source):
    posts = {p.id: p for p in await source.fetch_posts(HANDLE, 500)}
    reply = posts[REPLY_ID]
    assert reply.kind == PostKind.REPLY
    assert reply.conversation_id == PHOTO_ID
    assert reply.has_link is True

async def test_video_and_lowercased_mentions(source):
    posts = {p.id: p for p in await source.fetch_posts(HANDLE, 500)}
    post = posts[VIDEO_ID]
    assert post.media == [MediaType.VIDEO]
    assert post.mentions == ["ml_argentina", "libertadores"]
    assert posts[LINK_ID].has_link is True

async def test_quote_kind_wins_over_reply(source, api):
    first = page1()
    target = next(t for t in first["data"]["tweets"] if t["id"] == REPLY_ID)
    target["quoted_tweet"] = copy.deepcopy(next(t for t in first["data"]["tweets"] if t["id"] == PHOTO_ID))
    plain = next(t for t in first["data"]["tweets"] if t["id"] == VIDEO_ID)
    plain["quoted_tweet"] = copy.deepcopy(target["quoted_tweet"])
    first["has_next_page"] = False
    api.pages = {"": first}
    posts = {p.id: p for p in await source.fetch_posts(HANDLE, 500)}
    assert posts[REPLY_ID].kind == PostKind.QUOTE
    assert posts[VIDEO_ID].kind == PostKind.QUOTE

async def test_gif_media_and_empty_strings(source, api):
    first = page1()
    target = next(t for t in first["data"]["tweets"] if t["id"] == PHOTO_ID)
    target["extendedEntities"] = {"media": [{"type": "animated_gif"}, {"type": "photo"}]}
    target["lang"] = ""
    target["conversationId"] = ""
    first["has_next_page"] = False
    api.pages = {"": first}
    posts = {p.id: p for p in await source.fetch_posts(HANDLE, 500)}
    assert posts[PHOTO_ID].media == [MediaType.GIF, MediaType.PHOTO]
    assert posts[PHOTO_ID].lang is None
    assert posts[PHOTO_ID].conversation_id is None

async def test_missing_extended_entities_means_no_media(source, api):
    first = page1()
    target = next(t for t in first["data"]["tweets"] if t["id"] == PHOTO_ID)
    del target["extendedEntities"]
    first["has_next_page"] = False
    api.pages = {"": first}
    posts = {p.id: p for p in await source.fetch_posts(HANDLE, 500)}
    assert posts[PHOTO_ID].media == []

async def test_pinned_post_is_added_in_date_order_when_missing(source, api):
    first = page1()
    pinned = copy.deepcopy(next(t for t in page2()["data"]["tweets"] if not t.get("retweeted_tweet")))
    first["data"]["pin_tweet"] = pinned
    first["has_next_page"] = False
    api.pages = {"": first}
    posts = await source.fetch_posts(HANDLE, 500)
    assert posts[-1].id == pinned["id"]
    assert [p.created_at for p in posts] == sorted((p.created_at for p in posts), reverse=True)

async def test_pinned_post_is_not_duplicated(source, api):
    first = page1()
    first["data"]["pin_tweet"] = copy.deepcopy(next(t for t in first["data"]["tweets"] if t["id"] == PHOTO_ID))
    first["has_next_page"] = False
    api.pages = {"": first}
    ids = [p.id for p in await source.fetch_posts(HANDLE, 500)]
    assert ids.count(PHOTO_ID) == 1

async def test_trends_mapping(source, api):
    trends = await source.fetch_trends()
    assert api.calls("/twitter/trends")[0].url.params["woeid"] == "23424747"
    assert len(trends) == 30
    assert trends[0].name == "Central"
    assert trends[0].rank == 1
    assert all(t.location == "Argentina" for t in trends)
    assert trends[0].observed_at == datetime.fromtimestamp(1793429965938 / 1000, tz=UTC)

async def test_trends_error_status_is_source_unavailable(source, api):
    api.trends = {"status": "error", "msg": "something went wrong", "trends": []}
    with pytest.raises(SourceUnavailableError):
        await source.fetch_trends()

async def test_rate_limit_is_retried_then_succeeds(source, api):
    api.failures = [429]
    profile = await source.fetch_profile(HANDLE)
    assert profile.handle == HANDLE
    assert len(api.requests) == 2

async def test_persistent_rate_limit_raises_after_three_attempts(source, api):
    api.failures = [429, 429, 429]
    with pytest.raises(RateLimitedError) as error:
        await source.fetch_profile(HANDLE)
    assert error.value.message.strip()
    assert len(api.requests) == 3

@pytest.mark.parametrize(
    "failure",
    [500, 502, 503, httpx.ReadTimeout("timeout"), httpx.ConnectError("down")],
    ids=["500", "502", "503", "timeout", "connect"],
)
async def test_transient_failures_raise_source_unavailable_after_three_attempts(source, api, failure):
    api.failures = [failure, failure, failure]
    with pytest.raises(SourceUnavailableError) as error:
        await source.fetch_posts(HANDLE, 20)
    assert error.value.message.strip()
    assert len(api.requests) == 3

async def test_transient_failure_is_retried_then_succeeds(source, api):
    api.failures = [httpx.ReadTimeout("timeout"), 503]
    trends = await source.fetch_trends()
    assert len(trends) == 30
    assert len(api.requests) == 3

@pytest.mark.parametrize("status", [400, 401, 403])
async def test_client_errors_are_not_retried(source, api, status):
    api.failures = [status]
    with pytest.raises(SourceUnavailableError):
        await source.fetch_profile(HANDLE)
    assert len(api.requests) == 1

async def test_error_messages_do_not_leak_the_api_key(source, api):
    api.failures = [401]
    with pytest.raises(SourceUnavailableError) as error:
        await source.fetch_profile(HANDLE)
    assert KEY not in error.value.message
