"""
Semantic label sets and the LLM response schemas. These values fill PostFeatures.tone / hook / cta / topic
(contract v1.1.0 keeps them as plain str, so the label sets live here and can change without a contract bump).

| Field     | Allowed values (es-AR)                                                                       |
|-----------|----------------------------------------------------------------------------------------------|
| tone      | informativo, opinión, humor, personal, conversacional, promoción, inspiracional              |
| hook      | pregunta, dato, afirmación fuerte, historia, lista, ninguno                                  |
| cta       | guardar, responder, compartir, seguir, link, ninguno                                         |
| sentiment | float in -1..1                                                                               |
| topic     | one of the account taxonomy labels (5-8 short labels from the taxonomy pass), or "otros"     |
"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, create_model

TONE_LABELS = ("informativo", "opinión", "humor", "personal", "conversacional", "promoción", "inspiracional")
HOOK_LABELS = ("pregunta", "dato", "afirmación fuerte", "historia", "lista", "ninguno")
CTA_LABELS = ("guardar", "responder", "compartir", "seguir", "link", "ninguno")
OTHER_TOPIC = "otros"
MIN_TOPICS = 3
MAX_TOPICS = 8

Tone = Literal[TONE_LABELS]
Hook = Literal[HOOK_LABELS]
Cta = Literal[CTA_LABELS]

class TaxonomyResponse(BaseModel):
    """
    Taxonomy pass: short es-AR topic labels for this account ("otros" is appended afterwards).
    """
    model_config = ConfigDict(extra="forbid")
    topics: list[str] = Field(min_length=MIN_TOPICS, max_length=MAX_TOPICS)

class PostLabel(BaseModel):
    """
    Labels for one post. topic is validated against the taxonomy by the batch schema (label_batch_schema).
    """
    model_config = ConfigDict(extra="forbid")
    post_id: str
    topic: str
    tone: Tone
    sentiment: float = Field(ge=-1, le=1)
    hook: Hook
    cta: Cta

class LabelBatchResponse(BaseModel):
    """
    Labeling pass: one label per post of the batch.
    """
    model_config = ConfigDict(extra="forbid")
    labels: list[PostLabel]

def label_batch_schema(taxonomy: list[str]) -> type[LabelBatchResponse]:
    """
    Build a LabelBatchResponse subclass whose topic is an enum of the taxonomy, so the JSON schema enforces it.
    """
    topic_type = Literal[tuple(taxonomy)]
    label = create_model("PostLabelForAccount", __base__=PostLabel, topic=(topic_type, ...))
    return create_model("LabelBatchResponse", __base__=LabelBatchResponse, labels=(list[label], ...))
