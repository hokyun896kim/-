"""뉴스 감성 분석 테스트."""
from stocksystem.analysis import sentiment as se
from stocksystem.data.base import NewsItem


def test_positive_text():
    assert se.score_text("Company beats earnings and shares surge to record") > 0


def test_negative_text():
    assert se.score_text("Company misses estimates, shares plunge on weak guidance") < 0


def test_neutral_text():
    assert se.score_text("The company will report results next week") == 0.0


def test_negation_flips():
    # "not strong" 은 긍정어가 부정으로 뒤집혀야
    assert se.score_text("results were not strong") < 0


def test_score_bounds():
    s = se.score_text("beat surge rally gain jump rise win boost profit")
    assert -1.0 <= s <= 1.0


def test_aggregate_positive():
    news = [NewsItem(title="stock surges as profit beats estimates"),
            NewsItem(title="analysts upgrade on strong growth")]
    agg = se.aggregate(news)
    assert agg.score > 50
    assert agg.n_articles == 2
    assert agg.items[0].sentiment is not None  # 각 기사에 감성 채워짐


def test_aggregate_negative():
    news = [NewsItem(title="shares plunge on weak guidance"),
            NewsItem(title="downgrade amid lawsuit and probe")]
    agg = se.aggregate(news)
    assert agg.score < 50


def test_aggregate_empty():
    agg = se.aggregate([])
    assert agg.score == 50.0
    assert agg.n_articles == 0


def test_labels():
    assert "긍정" in se.label_for(80)
    assert "중립" in se.label_for(50)
    assert "부정" in se.label_for(20)
