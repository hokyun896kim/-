"""종합 점수/추천 엔진 통합 테스트 (오프라인 SampleProvider 사용)."""
from stocksystem.config import load_config
from stocksystem.data import SampleProvider
from stocksystem.analysis import analyze_symbol, analyze_watchlist
from stocksystem.analysis.scoring import _classify


def test_analyze_symbol_offline():
    cfg = load_config()
    res = analyze_symbol("AAPL", SampleProvider(), cfg)
    assert res.symbol == "AAPL"
    assert 0 <= res.total_score <= 100
    assert res.technical is not None
    assert res.fundamental is not None
    assert res.recommendation in {
        "strong_buy", "buy", "hold", "sell", "strong_sell"}


def test_summary_row_keys():
    cfg = load_config()
    res = analyze_symbol("MSFT", SampleProvider(), cfg)
    row = res.summary_row()
    for key in ["종목", "현재가", "종합점수", "기술점수", "펀더멘털점수", "추천"]:
        assert key in row


def test_watchlist_sorted_desc():
    cfg = load_config()
    results = analyze_watchlist(["AAPL", "MSFT", "NVDA"], SampleProvider(), cfg)
    scores = [r.total_score for r in results]
    assert scores == sorted(scores, reverse=True)


def test_classify_thresholds():
    cfg = load_config()
    assert _classify(90, cfg) == "strong_buy"
    assert _classify(62, cfg) == "buy"
    assert _classify(45, cfg) == "hold"
    assert _classify(30, cfg) == "sell"
    assert _classify(10, cfg) == "strong_sell"


def test_deterministic_sample():
    cfg = load_config()
    a = analyze_symbol("NVDA", SampleProvider(), cfg)
    b = analyze_symbol("NVDA", SampleProvider(), cfg)
    assert a.total_score == b.total_score   # 결정론적
