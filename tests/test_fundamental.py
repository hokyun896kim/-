"""기본적 분석 채점 테스트."""
from stocksystem.data.base import Fundamentals
from stocksystem.analysis import fundamental as fa


def test_low_pe_scores_higher_than_high_pe():
    assert fa.score_pe(8) > fa.score_pe(40)


def test_negative_pe_is_penalized():
    assert fa.score_pe(-5) <= 30


def test_high_roe_scores_higher():
    assert fa.score_roe(0.35) > fa.score_roe(0.04)


def test_growth_negative_low():
    assert fa.score_growth(-0.2) < fa.score_growth(0.25)


def test_debt_lower_is_better():
    assert fa.score_debt(20) > fa.score_debt(180)


def test_missing_metrics_return_none():
    assert fa.score_pe(None) is None
    assert fa.score_roe(None) is None


def test_strong_company_high_score():
    f = Fundamentals(
        symbol="GOOD", trailing_pe=12, price_to_book=1.5,
        return_on_equity=0.30, profit_margin=0.25,
        revenue_growth=0.20, earnings_growth=0.25,
        debt_to_equity=25, dividend_yield=0.02,
    )
    res = fa.analyze(f)
    assert res.score >= 75


def test_weak_company_low_score():
    f = Fundamentals(
        symbol="BAD", trailing_pe=80, price_to_book=15,
        return_on_equity=0.02, profit_margin=0.01,
        revenue_growth=-0.10, earnings_growth=-0.15,
        debt_to_equity=200, dividend_yield=0.0,
    )
    res = fa.analyze(f)
    assert res.score <= 40


def test_no_data_is_neutral():
    res = fa.analyze(Fundamentals(symbol="NONE"))
    assert res.score == 50.0
    assert "재무 데이터가 부족" in " ".join(res.notes)


def test_score_always_in_range():
    f = Fundamentals(symbol="X", trailing_pe=22, return_on_equity=0.15)
    res = fa.analyze(f)
    assert 0 <= res.score <= 100
