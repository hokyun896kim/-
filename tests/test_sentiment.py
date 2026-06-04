"""뉴스 감성 분석 테스트 (VADER + 금융 사전 고도화)."""
from datetime import date, timedelta

from stocksystem.analysis import sentiment as se
from stocksystem.data.base import NewsItem


def test_positive_text():
    assert se.score_text("Company beats earnings and shares surge to record") > 0.3


def test_negative_text():
    assert se.score_text("Company misses estimates, shares plunge on weak guidance") < -0.3


def test_finance_terms_scored():
    # 금융 사전 보강으로 'downgrade', 'lawsuit' 가 분명히 부정으로
    assert se.score_text("Analysts downgrade the stock amid lawsuit") < -0.2
    # 'beat', 'upgrade' 는 분명히 긍정으로
    assert se.score_text("Stock upgraded after earnings beat") > 0.2


def test_neutral_text_near_zero():
    assert abs(se.score_text("The company will report results next week")) < 0.1


def test_negation_flips():
    assert se.score_text("results were not strong") < 0


def test_intensifier_increases_magnitude():
    base = se.score_text("shares fell")
    strong = se.score_text("shares fell sharply")
    # 강조어가 있으면 더 부정적(크기 증가)
    assert strong <= base


def test_score_bounds():
    s = se.score_text("beat surge rally gain jump rise win boost profit soar")
    assert -1.0 <= s <= 1.0


def test_score_item_blends_summary():
    item = NewsItem(title="stock surges on strong demand",
                    summary="however guidance was weak and margins fell")
    s = se.score_item(item)
    assert -1.0 <= s <= 1.0
    # 제목만 봤을 때보다 요약(부정)이 섞여 점수가 낮아짐
    assert s < se.score_text(item.title)


def test_aggregate_positive():
    news = [NewsItem(title="stock surges as profit beats estimates"),
            NewsItem(title="analysts upgrade on strong growth")]
    agg = se.aggregate(news)
    assert agg.score > 55
    assert agg.n_articles == 2
    assert agg.items[0].sentiment is not None


def test_aggregate_negative():
    news = [NewsItem(title="shares plunge on weak guidance"),
            NewsItem(title="downgrade amid lawsuit and probe")]
    agg = se.aggregate(news)
    assert agg.score < 45


def test_recency_weighting():
    today = date(2026, 6, 1)
    # 오래된 긍정 1건 + 최신 부정 1건 → 최신(부정) 쪽으로 기움
    news = [
        NewsItem(title="stock soars on record profit",
                 published=(today - timedelta(days=40)).isoformat()),
        NewsItem(title="shares plunge on fraud probe and lawsuit",
                 published=today.isoformat()),
    ]
    agg = se.aggregate(news, today=today)
    assert agg.score < 50   # 최신 악재가 더 무겁게 반영


def test_confidence_levels():
    today = date(2026, 6, 1)
    # 일관된 긍정 다수 → 신뢰도 높음
    news = [NewsItem(title="stock surges on strong earnings beat",
                     published=today.isoformat()) for _ in range(6)]
    assert se.aggregate(news, today=today).confidence == "높음"
    # 1건뿐 → 낮음
    assert se.aggregate(news[:1], today=today).confidence == "낮음"


def test_aggregate_empty():
    agg = se.aggregate([])
    assert agg.score == 50.0
    assert agg.n_articles == 0


def test_labels():
    assert "긍정" in se.label_for(80)
    assert "중립" in se.label_for(50)
    assert "부정" in se.label_for(20)


def test_engine_name():
    # 환경에 따라 VADER 또는 폴백
    assert se.engine_name() in ("VADER+finance", "lexicon")
