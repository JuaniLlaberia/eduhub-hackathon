"""
The draft generator's LLM response schema. Labels reuse the labeling sets, so a draft can be scored with the
same features as the account's real posts.
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict
from eduhub_ai.labeling.schemas import Cta, Hook, Tone

class DraftItem(BaseModel):
    """
    One draft as written by the LLM, with its own labels (topic is one of the account's topics or "otros") and
    the format it is meant to be posted with (media), so the score reflects a video post as a video post.
    """
    model_config = ConfigDict(extra="forbid")
    text: str
    rationale: str
    topic: str
    tone: Tone
    hook: Hook
    cta: Cta
    media: Literal["text", "photo", "video", "gif"]

class DraftsResponse(BaseModel):
    """
    The generator's whole answer (the count is enforced in code, not in the schema).
    """
    model_config = ConfigDict(extra="forbid")
    drafts: list[DraftItem]
