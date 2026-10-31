import json
from eduhub_shared.fakes import build_segments
from eduhub_shared.fixtures import load_report
from eduhub_shared.models import InsightCategory, PostFeatures, SegmentDimension
from eduhub_shared.openapi import OPENAPI_PATH

def features_payload():
    return load_report().posts[0].features.model_dump(mode="json")

def test_post_features_accept_hook_and_cta():
    payload = {**features_payload(), "hook": "pregunta", "cta": "guardar"}
    features = PostFeatures.model_validate(payload)
    assert features.hook == "pregunta"
    assert features.cta == "guardar"

def test_hook_and_cta_default_to_none():
    payload = features_payload()
    payload.pop("hook", None)
    payload.pop("cta", None)
    features = PostFeatures.model_validate(payload)
    assert features.hook is None
    assert features.cta is None

def test_new_segment_dimensions_and_insight_categories():
    assert SegmentDimension("hook") is SegmentDimension.HOOK
    assert SegmentDimension("cta") is SegmentDimension.CTA
    assert InsightCategory("hook") is InsightCategory.HOOK
    assert InsightCategory("cta") is InsightCategory.CTA

def test_segments_include_hook_and_cta_when_labeled():
    posts = load_report().posts
    hooks = ["pregunta", "dato"]
    ctas = ["guardar", "ninguno"]
    labeled = [
        p.model_copy(update={"features": p.features.model_copy(update={"hook": hooks[i % 2], "cta": ctas[i % 2]})})
        for i, p in enumerate(posts)
    ]
    segments = build_segments(labeled)
    hook_values = {s.value for s in segments if s.dimension == SegmentDimension.HOOK}
    cta_values = {s.value for s in segments if s.dimension == SegmentDimension.CTA}
    assert hook_values == set(hooks)
    assert cta_values == set(ctas)
    assert sum(s.post_count for s in segments if s.dimension == SegmentDimension.HOOK) == len(posts)

def test_segments_skip_hook_and_cta_when_unlabeled():
    segments = build_segments(load_report().posts)
    assert not [s for s in segments if s.dimension in (SegmentDimension.HOOK, SegmentDimension.CTA)]

def test_openapi_exposes_the_new_fields_and_values():
    schemas = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))["components"]["schemas"]
    features = next(v for k, v in schemas.items() if k.startswith("PostFeatures"))
    assert {"hook", "cta"} <= set(features["properties"])
    assert {"hook", "cta"} <= set(schemas["SegmentDimension"]["enum"])
    assert {"hook", "cta"} <= set(schemas["InsightCategory"]["enum"])
