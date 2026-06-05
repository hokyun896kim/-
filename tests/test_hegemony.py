"""헤게모니 스프레드 엔진 테스트."""
import pandas as pd
import pytest

from stocksystem.data import SampleProvider
from stocksystem.data.base import Financials
from stocksystem.analysis import hegemony as hg


def _fin(rev, op, qrev=None, qop=None):
    def s(vals, n):
        idx = pd.date_range("2021-12-31", periods=len(vals), freq="YE") if n == "y" \
            else pd.date_range("2023-03-31", periods=len(vals), freq="QE")
        return pd.Series(vals, index=idx)
    return Financials(
        symbol="X",
        annual_revenue=s(rev, "y"), annual_op_income=s(op, "y"),
        quarterly_revenue=s(qrev, "q") if qrev else None,
        quarterly_op_income=s(qop, "q") if qop else None)


def test_positive_spread_when_op_grows_faster():
    # 매출 +10%, 영업이익 +30% → 스프레드 +20p
    r = hg.compute(_fin([100, 110], [20, 26]))
    assert r.annual_rev_yoy == pytest.approx(10, abs=0.1)
    assert r.annual_op_yoy == pytest.approx(30, abs=0.1)
    assert r.annual_spread == pytest.approx(20, abs=0.1)
    assert "마진" not in r.verdict


def test_negative_spread_margin_pressure():
    # 매출 +20%, 영업이익 +5% → 스프레드 -15p
    r = hg.compute(_fin([100, 120], [20, 21]))
    assert r.annual_spread < 0
    assert r.verdict == "마진 압박"


def test_ttm_and_accel():
    # 8분기 → TTM YoY 계산 가능, 가속 산출
    qrev = [25, 25, 25, 25, 28, 29, 30, 31]
    qop = [5, 5, 5, 5, 7, 7.5, 8, 8.5]
    r = hg.compute(_fin([100, 110], [20, 24], qrev, qop))
    assert r.ttm_spread is not None
    assert r.accel is not None


def test_insufficient_data():
    r = hg.compute(Financials(symbol="X"))
    assert r.annual_spread is None
    assert r.verdict == "데이터 부족"


def test_base_effect_flagged():
    # 전년 영업이익 ≈ 0 → 가속 폭발 → 기저효과 처리
    qrev = [25, 25, 25, 25, 26, 26, 26, 26]
    qop = [0.01, 0.01, 0.01, 0.01, 5, 5, 5, 5]
    r = hg.compute(_fin([100, 105], [0.1, 8], qrev, qop))
    assert r.base_effect is True
    assert r.accel is None       # 신뢰 불가 → None


def test_revenue_decline_note():
    # 매출 역성장인데 영업이익 덜 감소 → 스프레드 +지만 경고
    r = hg.compute(_fin([120, 100], [20, 18]))
    assert r.annual_spread > 0
    assert "역성장" in r.note


def test_sample_provider_integration():
    r = hg.analyze_symbol("AAPL", SampleProvider())
    assert r.annual_spread is not None
    assert r.verdict


def test_rank_sorted_desc():
    res = hg.rank(["AAPL", "NVDA", "JPM", "KO"], SampleProvider())
    spreads = [r.annual_spread for r in res if r.annual_spread is not None]
    assert spreads == sorted(spreads, reverse=True)
