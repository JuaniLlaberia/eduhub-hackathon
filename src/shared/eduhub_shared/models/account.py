from enum import StrEnum
from pydantic import AwareDatetime, Field, NonNegativeInt, PositiveInt
from eduhub_shared.models.common import ContractModel, Handle
from eduhub_shared.models.context import CreatorContext

class Platform(StrEnum):
    """
    Social platform a profile or post belongs to. Only X is implemented for the hackathon.
    """
    X = "x"

class PostKind(StrEnum):
    """
    Kind of post: original, reply, quote or plain repost.
    """
    ORIGINAL = "original"
    REPLY = "reply"
    QUOTE = "quote"
    REPOST = "repost"

class MediaType(StrEnum):
    """
    Type of media attached to a post.
    """
    PHOTO = "photo"
    VIDEO = "video"
    GIF = "gif"

class AccountProfile(ContractModel):
    """
    Public profile of a creator account.
    """
    platform: Platform = Platform.X
    handle: Handle = Field(description="Without '@', lowercase.")
    display_name: str
    bio: str = ""
    followers_count: NonNegativeInt
    following_count: NonNegativeInt
    posts_count: NonNegativeInt
    verified: bool = False
    avatar_url: str | None = None
    created_at: AwareDatetime | None = None

class PostMetrics(ContractModel):
    """
    Raw counters of a post. Private metrics are only available with the official API on own posts.
    """
    impressions: NonNegativeInt | None = Field(description="Views. None when the source does not provide them.")
    likes: NonNegativeInt
    reposts: NonNegativeInt
    quotes: NonNegativeInt
    replies: NonNegativeInt
    bookmarks: NonNegativeInt
    detail_expands: NonNegativeInt | None = Field(default=None, description="Private metric (optional).")
    profile_clicks: NonNegativeInt | None = Field(default=None, description="Private metric (optional).")
    link_clicks: NonNegativeInt | None = Field(default=None, description="Private metric (optional).")

class Post(ContractModel):
    """
    A single post with its metrics, normalized independently of the data source.
    """
    id: str
    platform: Platform = Platform.X
    author_handle: Handle
    text: str
    created_at: AwareDatetime
    url: str
    lang: str | None = None
    kind: PostKind = PostKind.ORIGINAL
    media: list[MediaType] = Field(default_factory=list)
    has_link: bool = False
    hashtags: list[str] = Field(default_factory=list, description="Without '#'.")
    mentions: list[str] = Field(default_factory=list, description="Handles without '@'.")
    conversation_id: str | None = Field(default=None, description="Thread/conversation id, if any.")
    metrics: PostMetrics

class Trend(ContractModel):
    """
    A trending topic observed at a given time and location.
    """
    name: str
    rank: PositiveInt | None = None
    post_count: NonNegativeInt | None = None
    location: str = "Argentina"
    observed_at: AwareDatetime

class AccountSnapshot(ContractModel):
    """
    Everything the AI needs about an account at one point in time. This is the AI input contract.
    """
    profile: AccountProfile
    posts: list[Post] = Field(description="Newest first.")
    trends: list[Trend] = Field(default_factory=list)
    source: str = Field(description="Data source id, e.g. 'twitterapi.io' or 'fixture'. Never branch on it.")
    collected_at: AwareDatetime
    context: CreatorContext | None = Field(default=None, description="Creator brief sent with the analysis request.")
