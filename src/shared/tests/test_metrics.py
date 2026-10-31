import pytest
from eduhub_shared.metrics import aggregate_rates, compute_rates, length_bucket, total_interactions
from eduhub_shared.models import LengthBucket, PostMetrics

def metrics(impressions, likes=0, reposts=0, quotes=0, replies=0, bookmarks=0):
    return PostMetrics(
        impressions=impressions, likes=likes, reposts=reposts, quotes=quotes, replies=replies, bookmarks=bookmarks
    )

def test_total_interactions_sums_every_public_counter():
    assert total_interactions(metrics(1000, likes=10, reposts=2, quotes=1, replies=3, bookmarks=4)) == 20

def test_rates_use_impressions_as_denominator():
    rates = compute_rates(metrics(1000, likes=10, reposts=2, quotes=1, replies=3, bookmarks=4))
    assert rates.engagement_rate == pytest.approx(0.020)
    assert rates.save_rate == pytest.approx(0.004)
    assert rates.share_rate == pytest.approx(0.003)
    assert rates.reply_rate == pytest.approx(0.003)
    assert rates.like_rate == pytest.approx(0.010)
    assert rates.passive_rate == pytest.approx(0.980)

@pytest.mark.parametrize("impressions", [None, 0])
def test_rates_are_none_without_impressions(impressions):
    rates = compute_rates(metrics(impressions, likes=5))
    assert all(value is None for value in rates.model_dump().values())

def test_passive_rate_never_goes_negative():
    assert compute_rates(metrics(10, likes=50)).passive_rate == 0.0

def test_aggregate_rates_weight_by_impressions_and_skip_posts_without_views():
    rates = aggregate_rates([metrics(1000, likes=10), metrics(3000, likes=90), metrics(None, likes=500)])
    assert rates.like_rate == pytest.approx(100 / 4000)

def test_aggregate_rates_of_nothing_are_none():
    assert aggregate_rates([]).engagement_rate is None

@pytest.mark.parametrize(
    ("chars", "bucket"),
    [(0, LengthBucket.SHORT), (100, LengthBucket.SHORT), (101, LengthBucket.MEDIUM), (200, LengthBucket.MEDIUM),
     (201, LengthBucket.LONG)],
)
def test_length_buckets(chars, bucket):
    assert length_bucket(chars) == bucket
